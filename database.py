"""
Модуль для работы с базами данных Tribute и Minecraft
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional
import pymysql
from pymongo import MongoClient


class DatabaseManager:
    """Менеджер для работы с базами данных"""
    
    def __init__(self, config: Dict[str, Any], logger):
        """
        Инициализация менеджера баз данных
        
        Args:
            config: Конфигурация
            logger: Объект логгера
        """
        self.config = config
        self.logger = logger
        
        # Инициализируем подключения к БД
        self._init_tribute_db()
        self._init_minecraft_db()
    
    def _init_tribute_db(self):
        """Инициализирует базу данных Tribute"""
        self.logger.debug("🔧 Инициализация БД Tribute")
        
        db_type = self.config['tribute_database']['type']
        
        if db_type == 'sqlite':
            self._init_tribute_sqlite()
        elif db_type == 'mysql':
            self._init_tribute_mysql()
        elif db_type == 'mongodb':
            self._init_tribute_mongodb()
        else:
            raise ValueError(f"Неподдерживаемый тип БД Tribute: {db_type}")
        
        self.logger.info(f"✅ БД Tribute ({db_type}) инициализирована")
    
    def _init_tribute_sqlite(self):
        """Инициализирует SQLite для Tribute"""
        import os
        db_path = self.config['tribute_database']['sqlite']['path']
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для webhook'ов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                player_name TEXT,
                game_currency INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.tribute_db_type = 'sqlite'
        self.tribute_db_path = db_path
    
    def _init_tribute_mysql(self):
        """Инициализирует MySQL для Tribute"""
        mysql_config = self.config['tribute_database']['mysql']
        
        conn = pymysql.connect(
            host=mysql_config['host'],
            port=mysql_config['port'],
            user=mysql_config['user'],
            password=mysql_config['password'],
            database=mysql_config['database'],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # Создаем таблицу для webhook'ов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhooks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                webhook_type VARCHAR(100) NOT NULL,
                payload TEXT NOT NULL,
                status VARCHAR(50) NOT NULL,
                player_name VARCHAR(100),
                game_currency INT DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        conn.commit()
        conn.close()
        
        self.tribute_db_type = 'mysql'
        self.tribute_mysql_config = mysql_config
    
    def _init_tribute_mongodb(self):
        """Инициализирует MongoDB для Tribute"""
        mongo_config = self.config['tribute_database']['mongodb']
        
        # Формируем строку подключения
        if 'user' in mongo_config and mongo_config.get('user'):
            connection_string = f"mongodb://{mongo_config['user']}:{mongo_config['password']}@{mongo_config['host']}:{mongo_config['port']}/{mongo_config['database']}"
        else:
            connection_string = f"mongodb://{mongo_config['host']}:{mongo_config['port']}"
        
        self.mongo_client = MongoClient(connection_string)
        self.mongo_db = self.mongo_client[mongo_config['database']]
        self.tribute_db_type = 'mongodb'
    
    def _init_minecraft_db(self):
        """Инициализирует базу данных Minecraft"""
        self.logger.debug("🔧 Инициализация БД Minecraft")
        
        db_type = self.config['minecraft_database']['type']
        
        if db_type == 'sqlite':
            self._init_minecraft_sqlite()
        elif db_type == 'mysql':
            self._init_minecraft_mysql()
        else:
            raise ValueError(f"Неподдерживаемый тип БД Minecraft: {db_type}")
        
        self.logger.info(f"✅ БД Minecraft ({db_type}) инициализирована")
    
    def _init_minecraft_sqlite(self):
        """Инициализирует SQLite для Minecraft"""
        import os
        db_path = self.config['minecraft_database']['sqlite']['path']
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.minecraft_db_type = 'sqlite'
        self.minecraft_db_path = db_path
    
    def _init_minecraft_mysql(self):
        """Инициализирует MySQL для Minecraft"""
        mysql_config = self.config['minecraft_database']['mysql']
        
        self.minecraft_db_type = 'mysql'
        self.minecraft_mysql_config = mysql_config
    
    def save_tribute_webhook(
        self,
        webhook_type: str,
        payload: Dict[str, Any],
        status: str,
        player_name: Optional[str] = None,
        game_currency: int = 0,
        error_message: Optional[str] = None
    ):
        """
        Сохраняет webhook в БД Tribute
        
        Args:
            webhook_type: Тип webhook'а
            payload: Данные webhook'а
            status: Статус обработки
            player_name: Имя игрока (если применимо)
            game_currency: Начисленная валюта (если применимо)
            error_message: Сообщение об ошибке (если есть)
        """
        self.logger.debug(f"💾 Сохранение webhook в БД Tribute: {webhook_type}")
        
        payload_json = json.dumps(payload, ensure_ascii=False)
        
        if self.tribute_db_type == 'sqlite':
            self._save_tribute_sqlite(webhook_type, payload_json, status, player_name, game_currency, error_message)
        elif self.tribute_db_type == 'mysql':
            self._save_tribute_mysql(webhook_type, payload_json, status, player_name, game_currency, error_message)
        elif self.tribute_db_type == 'mongodb':
            self._save_tribute_mongodb(webhook_type, payload, status, player_name, game_currency, error_message)
    
    def _save_tribute_sqlite(self, webhook_type, payload_json, status, player_name, game_currency, error_message):
        """Сохраняет в SQLite"""
        conn = sqlite3.connect(self.tribute_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO webhooks (webhook_type, payload, status, player_name, game_currency, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (webhook_type, payload_json, status, player_name, game_currency, error_message))
        
        conn.commit()
        conn.close()
    
    def _save_tribute_mysql(self, webhook_type, payload_json, status, player_name, game_currency, error_message):
        """Сохраняет в MySQL"""
        conn = pymysql.connect(**self.tribute_mysql_config, charset='utf8mb4')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO webhooks (webhook_type, payload, status, player_name, game_currency, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (webhook_type, payload_json, status, player_name, game_currency, error_message))
        
        conn.commit()
        conn.close()
    
    def _save_tribute_mongodb(self, webhook_type, payload, status, player_name, game_currency, error_message):
        """Сохраняет в MongoDB"""
        document = {
            'webhook_type': webhook_type,
            'payload': payload,
            'status': status,
            'player_name': player_name,
            'game_currency': game_currency,
            'error_message': error_message,
            'created_at': datetime.now()
        }
        
        self.mongo_db.webhooks.insert_one(document)
    
    def add_currency_to_player(self, player_name: str, amount: int) -> bool:
        """
        Начисляет валюту игроку в БД Minecraft
        
        Args:
            player_name: Имя игрока
            amount: Количество валюты для начисления
        
        Returns:
            True если успешно, False если ошибка
        """
        self.logger.debug(f"💰 Начисление {amount} валюты игроку {player_name}")
        
        try:
            if self.minecraft_db_type == 'sqlite':
                return self._add_currency_sqlite(player_name, amount)
            elif self.minecraft_db_type == 'mysql':
                return self._add_currency_mysql(player_name, amount)
            else:
                self.logger.error(f"Неподдерживаемый тип БД: {self.minecraft_db_type}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка начисления валюты: {e}")
            return False
    
    def _add_currency_sqlite(self, player_name: str, amount: int) -> bool:
        """Начисляет валюту в SQLite"""
        table_config = self.config['minecraft_database']['table']
        table_name = table_config['name']
        player_col = table_config['player_column']
        currency_col = table_config['currency_column']
        
        self.logger.debug(f"🔍 SQLite: Таблица={table_name}, Игрок={player_col}, Валюта={currency_col}")
        
        conn = sqlite3.connect(self.minecraft_db_path)
        cursor = conn.cursor()
        
        # Проверяем есть ли игрок
        cursor.execute(f'SELECT {currency_col} FROM {table_name} WHERE {player_col} = ?', (player_name,))
        result = cursor.fetchone()
        
        if result:
            # Обновляем баланс
            new_balance = result[0] + amount
            cursor.execute(f'UPDATE {table_name} SET {currency_col} = ? WHERE {player_col} = ?', 
                         (new_balance, player_name))
            self.logger.debug(f"✅ Обновлен баланс: {result[0]} -> {new_balance}")
        else:
            # Создаем новую запись
            cursor.execute(f'INSERT INTO {table_name} ({player_col}, {currency_col}) VALUES (?, ?)', 
                         (player_name, amount))
            self.logger.debug(f"✅ Создана новая запись с балансом {amount}")
        
        conn.commit()
        conn.close()
        return True
    
    def _add_currency_mysql(self, player_name: str, amount: int) -> bool:
        """Начисляет валюту в MySQL"""
        table_config = self.config['minecraft_database']['table']
        table_name = table_config['name']
        player_col = table_config['player_column']
        currency_col = table_config['currency_column']
        
        self.logger.debug(f"🔍 MySQL: Таблица={table_name}, Игрок={player_col}, Валюта={currency_col}")
        
        conn = pymysql.connect(**self.minecraft_mysql_config, charset='utf8mb4')
        cursor = conn.cursor()
        
        # Используем INSERT ... ON DUPLICATE KEY UPDATE для MySQL
        # Это работает если у тебя есть UNIQUE ключ на player_column
        query = f'''
            INSERT INTO {table_name} ({player_col}, {currency_col})
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE {currency_col} = {currency_col} + %s
        '''
        
        cursor.execute(query, (player_name, amount, amount))
        
        self.logger.debug(f"✅ Баланс обновлен (добавлено {amount})")
        
        conn.commit()
        conn.close()
        return True
