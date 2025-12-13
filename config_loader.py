"""
Модуль для загрузки конфигурации из YAML файла
"""

import yaml
import os
from typing import Dict, Any


def _apply_env_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Применяет переменные окружения к конфигурации

    Переменные окружения имеют приоритет над значениями в config.yaml

    Args:
        config: Конфигурация из YAML файла

    Returns:
        Конфигурация с примененными переменными окружения
    """
    # Маппинг переменных окружения на пути в конфигурации
    env_mappings = {
        'SERVER_HOST': ('server', 'host'),
        'SERVER_PORT': ('server', 'port'),
        'SERVER_DEBUG': ('server', 'debug'),
        'TRIBUTE_API_KEY': ('tribute', 'api_key'),
        'RCON_HOST': ('minecraft_rcon', 'host'),
        'RCON_PORT': ('minecraft_rcon', 'port'),
        'RCON_PASSWORD': ('minecraft_rcon', 'password'),
        'RCON_COMMAND': ('minecraft_rcon', 'command'),
    }

    for env_var, config_path in env_mappings.items():
        env_value = os.getenv(env_var)

        if env_value is not None:
            # Применяем значение из переменной окружения
            current = config
            for key in config_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            last_key = config_path[-1]

            # Конвертируем типы данных
            if last_key == 'port':
                # Порты должны быть int
                current[last_key] = int(env_value)
            elif last_key == 'debug':
                # Debug должен быть bool
                current[last_key] = env_value.lower() in ('true', '1', 'yes', 'on')
            else:
                # Остальное - строки
                current[last_key] = env_value

    return config


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML файла с поддержкой переменных окружения

    Поддерживаемые переменные окружения:
    - SERVER_HOST: server.host
    - SERVER_PORT: server.port
    - SERVER_DEBUG: server.debug
    - TRIBUTE_API_KEY: tribute.api_key
    - RCON_HOST: minecraft_rcon.host
    - RCON_PORT: minecraft_rcon.port
    - RCON_PASSWORD: minecraft_rcon.password
    - RCON_COMMAND: minecraft_rcon.command

    Args:
        config_path: Путь к файлу конфигурации

    Returns:
        Словарь с конфигурацией
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Применяем переменные окружения (они имеют приоритет над config.yaml)
    config = _apply_env_variables(config)
    
    # Проверяем обязательные поля
    required_fields = [
        'server',
        'tribute',
        'currency_rates',
        'tribute_database',
        'minecraft_rcon'
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Отсутствует обязательное поле в конфигурации: {field}")

    # Проверяем API ключ (если не задан через env)
    api_key = config['tribute']['api_key']
    if api_key in ('YOUR_API_KEY_HERE', '', None):
        if not os.getenv('TRIBUTE_API_KEY'):
            raise ValueError("Необходимо указать API ключ от Tribute в config.yaml или TRIBUTE_API_KEY!")

    # Проверяем настройки RCON
    rcon_config = config['minecraft_rcon']
    required_rcon_fields = ['host', 'port', 'password', 'command']

    for field in required_rcon_fields:
        if field not in rcon_config:
            raise ValueError(f"Отсутствует обязательное поле в minecraft_rcon: {field}")

    # Проверяем что команда содержит плейсхолдеры
    command = rcon_config['command']
    if '%player_name%' not in command or '%amount%' not in command:
        raise ValueError("Команда RCON должна содержать плейсхолдеры %player_name% и %amount%")

    # Проверяем что пароль не дефолтный (если не задан через env)
    rcon_password = rcon_config['password']
    if rcon_password in ('your_rcon_password', 'YOUR_RCON_PASSWORD', '', None):
        if not os.getenv('RCON_PASSWORD'):
            raise ValueError("Необходимо указать реальный RCON пароль в config.yaml или RCON_PASSWORD!")

    return config
