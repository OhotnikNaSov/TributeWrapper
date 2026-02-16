"""
Модуль Discord бота с slash-командой /adduser
Отправляет RCON команды на Minecraft сервер
"""

import discord
from discord import app_commands
from typing import Dict, Any, Optional
from mcrcon import MCRcon
import re


class TributeDiscordBot(discord.Client):
    """Discord бот для управления сервером через RCON"""

    def __init__(self, config: Dict[str, Any], logger):
        """
        Инициализация бота

        Args:
            config: Полная конфигурация приложения
            logger: Объект логгера
        """
        self.logger = logger
        self.config = config
        self.bot_config = config['discord_bot']
        self.rcon_config = config['minecraft_rcon']

        self.guild_id = int(self.bot_config['guild_id'])
        self.channel_id = int(self.bot_config['channel_id'])
        self.allowed_role_ids = [int(r) for r in self.bot_config.get('allowed_role_ids', []) if r and r != 0]
        self.adduser_command_template = self.bot_config['adduser_command']

        # Настройки discord.py
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

        # Регистрируем команды
        self._register_commands()

    def _register_commands(self):
        """Регистрирует slash-команды бота"""
        guild_obj = discord.Object(id=self.guild_id)

        @self.tree.command(
            name="adduser",
            description="Добавить пользователя на сервер через RCON",
            guild=guild_obj
        )
        @app_commands.describe(
            nick="Ник игрока на сервере",
            rp_name="РП имя (используйте _ вместо пробела)",
            gender="Пол персонажа",
            quest_link="Ссылка на квенту в Discord"
        )
        @app_commands.choices(gender=[
            app_commands.Choice(name="Мужской", value="male"),
            app_commands.Choice(name="Женский", value="female"),
        ])
        async def adduser_command(
            interaction: discord.Interaction,
            nick: str,
            rp_name: str,
            gender: app_commands.Choice[str],
            quest_link: str
        ):
            await self._handle_adduser(interaction, nick, rp_name, gender.value, quest_link)

    def _check_access(self, interaction: discord.Interaction) -> Optional[str]:
        """
        Проверяет доступ пользователя к команде

        Returns:
            None если доступ разрешён, строка с причиной отказа если запрещён
        """
        # Проверка гильдии
        if not interaction.guild or interaction.guild.id != self.guild_id:
            return "Команда доступна только на определённом сервере Discord"

        # Проверка канала
        if interaction.channel_id != self.channel_id:
            return f"Команда доступна только в канале <#{self.channel_id}>"

        # Проверка ролей
        if self.allowed_role_ids:
            member = interaction.user
            user_role_ids = {role.id for role in member.roles}
            if not user_role_ids.intersection(self.allowed_role_ids):
                return "У вас нет роли для использования этой команды"

        return None

    def _execute_rcon(self, command: str) -> str:
        """
        Выполняет RCON команду на сервере

        Args:
            command: Полная RCON команда

        Returns:
            Ответ сервера
        """
        host = self.rcon_config['host']
        port = self.rcon_config['port']
        password = self.rcon_config['password']

        with MCRcon(host, password, port) as mcr:
            response = mcr.command(command)

        # Очищаем Minecraft цветовые коды
        response = re.sub(r'§x(?:§[0-9a-f]){6}', '', response, flags=re.IGNORECASE)
        response = re.sub(r'§[0-9a-fk-or]', '', response, flags=re.IGNORECASE)

        return response

    async def _handle_adduser(
        self,
        interaction: discord.Interaction,
        nick: str,
        rp_name: str,
        gender: str,
        quest_link: str
    ):
        """Обработчик команды /adduser"""
        self.logger.debug(f"[Discord Bot] /adduser от {interaction.user} (ID: {interaction.user.id})")
        self.logger.debug(f"[Discord Bot] Параметры: nick={nick}, rp_name={rp_name}, gender={gender}, quest_link={quest_link}")

        # Проверяем доступ
        deny_reason = self._check_access(interaction)
        if deny_reason:
            self.logger.debug(f"[Discord Bot] Доступ запрещён: {deny_reason}")
            await interaction.response.send_message(
                f"**Доступ запрещён:** {deny_reason}",
                ephemeral=True
            )
            return

        # Формируем RCON команду
        command = self.adduser_command_template
        command = command.replace('%nick%', nick)
        command = command.replace('%rp_name%', rp_name)
        command = command.replace('%gender%', gender)
        command = command.replace('%quest_link%', quest_link)

        self.logger.info(f"[Discord Bot] Выполнение RCON: {command}")

        # Отправляем "думаю..." чтобы не было таймаута
        await interaction.response.defer(ephemeral=True)

        try:
            response = self._execute_rcon(command)
            self.logger.info(f"[Discord Bot] Ответ RCON: {response}")

            if response.strip():
                result_text = f"**Команда выполнена**\n```\n{command}\n```\n**Ответ сервера:**\n```\n{response}\n```"
            else:
                result_text = f"**Команда выполнена**\n```\n{command}\n```\n*Сервер не вернул ответа (пусто)*"

            await interaction.followup.send(result_text, ephemeral=True)

        except ConnectionRefusedError:
            error_msg = f"Не удалось подключиться к RCON ({self.rcon_config['host']}:{self.rcon_config['port']})"
            self.logger.error(f"[Discord Bot] {error_msg}")
            await interaction.followup.send(
                f"**Ошибка подключения к RCON**\n```\n{error_msg}\n```",
                ephemeral=True
            )

        except Exception as e:
            error_msg = f"Ошибка выполнения RCON: {str(e)}"
            self.logger.error(f"[Discord Bot] {error_msg}")
            await interaction.followup.send(
                f"**Ошибка**\n```\n{error_msg}\n```",
                ephemeral=True
            )

    async def on_ready(self):
        """Вызывается когда бот подключился к Discord"""
        self.logger.info(f"[Discord Bot] Бот запущен как {self.user} (ID: {self.user.id})")
        self.logger.info(f"[Discord Bot] Гильдия: {self.guild_id}, Канал: {self.channel_id}")
        self.logger.info(f"[Discord Bot] Разрешённые роли: {self.allowed_role_ids}")

        # Синхронизируем slash-команды с гильдией
        guild_obj = discord.Object(id=self.guild_id)
        try:
            synced = await self.tree.sync(guild=guild_obj)
            self.logger.info(f"[Discord Bot] Синхронизировано {len(synced)} команд с гильдией")
        except Exception as e:
            self.logger.error(f"[Discord Bot] Ошибка синхронизации команд: {e}")

    async def on_error(self, event_method, *args, **kwargs):
        """Логирование ошибок бота"""
        self.logger.error(f"[Discord Bot] Ошибка в событии {event_method}")
