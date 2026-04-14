"""
HHParser - Парсер вакансий с HH.ru
Модульная архитектура с разделением ответственности
"""

__version__ = "2.0.0"
__author__ = "itrickon (optimized by direct02)"

# Экспортируем основные классы
from src.base_parser import BaseHHParser
from src.phone_parser import HHPhoneParser
from src.url_collector import HHVacancyCollector
from src.vacancy_extractor import VacancyExtractor
from src.browser_manager import BrowserManager
from src.validator import HHValidator
from src.excel_manager import ExcelManager

__all__ = [
    "BaseHHParser",
    "HHPhoneParser",
    "HHVacancyCollector",
    "VacancyExtractor",
    "BrowserManager",
    "HHValidator",
    "ExcelManager",
]
