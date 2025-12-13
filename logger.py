"""
Модуль логирования с поддержкой debug режима
"""

import os
from datetime import datetime
from typing import Any


class Logger:
    """Простой логгер с поддержкой debug режима"""
    
    def __init__(self, debug_mode: bool = False):
        """
        Инициализация логгера
        
        Args:
            debug_mode: Включить ли debug режим
        """
        self.debug_mode = debug_mode
        self.log_dir = "./logs"
        
        # Создаем директорию для логов
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Файлы логов
        self.info_log = os.path.join(self.log_dir, "info.log")
        self.error_log = os.path.join(self.log_dir, "error.log")
        self.debug_log = os.path.join(self.log_dir, "debug.log")
    
    def _write_to_file(self, filepath: str, message: str):
        """Записывает сообщение в файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _format_message(self, level: str, message: str) -> str:
        """Форматирует сообщение для вывода"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"
    
    def debug(self, message: str):
        """Логирует debug сообщение (только если debug_mode=True)"""
        if self.debug_mode:
            formatted = self._format_message("DEBUG", message)
            print(formatted)
            self._write_to_file(self.debug_log, message)
    
    def info(self, message: str):
        """Логирует информационное сообщение"""
        formatted = self._format_message("INFO", message)
        print(formatted)
        self._write_to_file(self.info_log, message)
    
    def error(self, message: str):
        """Логирует сообщение об ошибке"""
        formatted = self._format_message("ERROR", message)
        print(formatted)
        self._write_to_file(self.error_log, message)
        
        # Дублируем в info лог
        self._write_to_file(self.info_log, f"ERROR: {message}")
    
    def warning(self, message: str):
        """Логирует предупреждение"""
        formatted = self._format_message("WARNING", message)
        print(formatted)
        self._write_to_file(self.info_log, f"WARNING: {message}")
