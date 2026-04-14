"""
Модуль логирования для HHParser
Обеспечивает одновременное логирование в файл и консоль/GUI
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import config


class HHParserFormatter(logging.Formatter):
    """Кастомный форматтер для красивого вывода логов"""
    
    # Цвета для терминала (ANSI escape codes)
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__(config.LOG_FORMAT)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Получаем стандартное форматирование
        formatted = super().format(record)
        
        # Добавляем цвета если нужно
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            return f"{color}{formatted}{self.RESET}"
        
        return formatted


class GUIHandler(logging.Handler):
    """Handler для отправки логов в GUI"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord):
        """Отправляем лог в GUI callback"""
        if self.callback:
            log_entry = self.format(record)
            try:
                self.callback(log_entry)
            except Exception:
                self.handleError(record)


class LoggerManager:
    """Менеджер логирования для HHParser"""
    
    _instance: Optional['LoggerManager'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'LoggerManager':
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def setup_logger(
        self,
        name: str = "HHParser",
        log_level: str = config.LOG_LEVEL,
        gui_callback = None,
    ) -> logging.Logger:
        """
        Настраивает логгер с несколькими handlers
        
        Args:
            name: Имя логгера
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            gui_callback: Callback функция для отправки логов в GUI
            
        Returns:
            Настроенный logger
        """
        if self._logger is not None:
            return self._logger

        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Предотвращаем дублирование handlers
        self._logger.handlers.clear()

        # 1. File Handler (ротация файлов)
        try:
            file_handler = RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=config.LOG_MAX_BYTES,
                backupCount=config.LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(HHParserFormatter(use_colors=False))
            self._logger.addHandler(file_handler)
        except Exception as e:
            print(f"Не удалось создать file handler: {e}", file=sys.stderr)

        # 2. Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(HHParserFormatter(use_colors=True))
        self._logger.addHandler(console_handler)

        # 3. GUI Handler (если есть callback)
        if gui_callback:
            gui_handler = GUIHandler(gui_callback)
            gui_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            self._logger.addHandler(gui_handler)

        return self._logger

    def get_logger(self) -> logging.Logger:
        """Получить текущий логгер"""
        if self._logger is None:
            return self.setup_logger()
        return self._logger

    def update_gui_callback(self, callback):
        """Обновить callback для GUI"""
        if self._logger is None:
            self.setup_logger(gui_callback=callback)
            return

        # Удаляем старые GUI handlers
        for handler in self._logger.handlers[:]:
            if isinstance(handler, GUIHandler):
                self._logger.removeHandler(handler)

        # Добавляем новый
        if callback:
            gui_handler = GUIHandler(callback)
            gui_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
            self._logger.addHandler(gui_handler)


# Convenience функции для быстрого использования
def get_logger(gui_callback=None) -> logging.Logger:
    """
    Получить настроенный логгер
    
    Args:
        gui_callback: Optional callback для GUI логов
        
    Returns:
        logging.Logger
    """
    manager = LoggerManager()
    return manager.setup_logger(gui_callback=gui_callback)


def log_gui_message(gui_callback, message: str, level: str = "INFO"):
    """
    Отправить сообщение в GUI лог
    
    Args:
        gui_callback: Функция callback для обновления GUI
        message: Сообщение для логирования
        level: Уровень лога (INFO, ERROR, WARNING, SUCCESS)
    """
    if gui_callback:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        gui_callback(formatted_message)


# Экспортируем основные компоненты
__all__ = [
    "LoggerManager",
    "get_logger",
    "log_gui_message",
    "GUIHandler",
    "HHParserFormatter",
]
