"""
Модуль для работы с Minecraft RCON
"""

import re
from typing import Dict, Any, Optional, Tuple
from mcrcon import MCRcon


class RconManager:
    """Менеджер для выполнения команд через Minecraft RCON"""

    def __init__(self, config: Dict[str, Any], logger):
        """
        Инициализация RCON менеджера

        Args:
            config: Конфигурация
            logger: Объект логгера
        """
        self.config = config
        self.logger = logger
        self.rcon_config = config['minecraft_rcon']

        self.host = self.rcon_config['host']
        self.port = self.rcon_config['port']
        self.password = self.rcon_config['password']
        self.command_template = self.rcon_config['command']
        self.success_patterns = self.rcon_config.get('success_patterns', [])
        self.error_patterns = self.rcon_config.get('error_patterns', [])

        self.logger.info(f"✅ RCON менеджер инициализирован ({self.host}:{self.port})")

    @staticmethod
    def _strip_minecraft_colors(text: str) -> str:
        """
        Удаляет все Minecraft цветовые коды из текста

        Поддерживаемые форматы:
        - §x§r§g§b§r§g§b - hex цвета
        - §a, §l, §n и т.д. - стандартные коды

        Args:
            text: Текст с Minecraft цветовыми кодами

        Returns:
            Очищенный текст
        """
        # Удаляем hex цвета (§x§r§g§b§r§g§b)
        text = re.sub(r'§x(?:§[0-9a-f]){6}', '', text, flags=re.IGNORECASE)

        # Удаляем обычные цветовые коды (§a, §l, §n и т.д.)
        text = re.sub(r'§[0-9a-fk-or]', '', text, flags=re.IGNORECASE)

        return text

    def execute_command(self, player_name: str, amount: int) -> Tuple[bool, str]:
        """
        Выполняет команду начисления валюты через RCON

        Args:
            player_name: Имя игрока
            amount: Количество валюты для начисления

        Returns:
            Tuple[bool, str]: (успех, ответ сервера)
        """
        # Подставляем плейсхолдеры в команду
        command = self.command_template.replace('%player_name%', player_name)
        command = command.replace('%amount%', str(amount))

        self.logger.debug(f"🎮 Выполнение RCON команды: {command}")

        try:
            # Подключаемся к RCON и выполняем команду
            with MCRcon(self.host, self.password, self.port) as mcr:
                response = mcr.command(command)

            self.logger.debug(f"📨 Ответ RCON: {response}")

            # Проверяем ответ на успех или ошибку
            is_success = self._check_response(response, player_name, amount)

            return is_success, response

        except ConnectionRefusedError:
            error_msg = f"Не удалось подключиться к RCON ({self.host}:{self.port})"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Ошибка выполнения RCON команды: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg

    def _check_response(self, response: str, player_name: str, amount: int) -> bool:
        """
        Проверяет ответ сервера на успех или ошибку

        Args:
            response: Ответ от RCON сервера
            player_name: Имя игрока (для подстановки в плейсхолдеры)
            amount: Количество валюты (для подстановки в плейсхолдеры)

        Returns:
            True если команда успешна, False если ошибка
        """
        # Очищаем Minecraft цветовые коды из ответа
        cleaned_response = self._strip_minecraft_colors(response)
        response_lower = cleaned_response.lower()

        self.logger.debug(f"🧹 Очищенный ответ: {cleaned_response}")

        # Проверяем на паттерны ошибок
        for error_pattern in self.error_patterns:
            # Заменяем плейсхолдеры в паттерне
            pattern = self._replace_placeholders(error_pattern, player_name, amount)
            if pattern.lower() in response_lower:
                self.logger.debug(f"⚠️ Найден паттерн ошибки: '{error_pattern}'")
                return False

        # Проверяем на паттерны успеха
        for success_pattern in self.success_patterns:
            # Заменяем плейсхолдеры в паттерне
            pattern = self._replace_placeholders(success_pattern, player_name, amount)
            if pattern.lower() in response_lower:
                self.logger.debug(f"✅ Найден паттерн успеха: '{success_pattern}' (проверено как '{pattern}')")
                return True

        # Если нет паттернов успеха, но и нет ошибок - считаем успехом
        if not self.success_patterns:
            self.logger.debug("✅ Паттерны успеха не настроены, считаем успехом")
            return True

        # Если есть паттерны успеха, но ни один не найден - ошибка
        self.logger.debug("⚠️ Ни один паттерн успеха не найден в ответе")
        return False

    @staticmethod
    def _replace_placeholders(pattern: str, player_name: str, amount: int) -> str:
        """
        Заменяет плейсхолдеры в паттерне

        Поддерживаемые плейсхолдеры:
        - {player} - имя игрока
        - {amount} - количество валюты

        Args:
            pattern: Паттерн с плейсхолдерами
            player_name: Имя игрока
            amount: Количество валюты

        Returns:
            Паттерн с замененными плейсхолдерами
        """
        result = pattern.replace('{player}', player_name)
        result = result.replace('{amount}', str(amount))
        return result

    def add_currency_to_player(self, player_name: str, amount: int) -> bool:
        """
        Начисляет валюту игроку через RCON

        Args:
            player_name: Имя игрока
            amount: Количество валюты для начисления

        Returns:
            True если успешно, False если ошибка
        """
        self.logger.debug(f"💰 Начисление {amount} валюты игроку {player_name} через RCON")

        success, response = self.execute_command(player_name, amount)

        if success:
            self.logger.info(f"✅ RCON: Успешно начислено {amount} валюты игроку {player_name}")
            self.logger.debug(f"📋 Ответ сервера: {response}")
        else:
            self.logger.error(f"❌ RCON: Ошибка начисления валюты игроку {player_name}")
            self.logger.error(f"📋 Ответ сервера: {response}")

        return success
