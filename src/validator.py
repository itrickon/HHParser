"""
Модуль валидации для HHParser
Проверка URL, файлов, данных и т.д.
"""

import re
import os
from pathlib import Path
from typing import List, Optional

import config
from logger import get_logger


class HHValidator:
    """Класс для валидации данных в HHParser"""
    
    def __init__(self):
        self.logger = get_logger()

    @staticmethod
    def validate_vacancy_url(url: str) -> bool:
        """
        Проверяет что URL является ссылкой на вакансию HH.ru
        
        Args:
            url: URL для проверки
            
        Returns:
            True если URL корректен
        """
        pattern = re.compile(config.HH_VACANCY_URL_PATTERN)
        return bool(pattern.match(url))

    @staticmethod
    def validate_search_url(url: str) -> bool:
        """
        Проверяет что URL является ссылкой на поиск HH.ru
        
        Args:
            url: URL для проверки
            
        Returns:
            True если URL корректен
        """
        pattern = re.compile(config.HH_SEARCH_URL_PATTERN)
        return bool(pattern.search(url))

    @staticmethod
    def validate_excel_file(file_path: str) -> bool:
        """
        Проверяет что файл существует и имеет правильный формат
        
        Args:
            file_path: Путь к Excel файлу
            
        Returns:
            True если файл корректен
        """
        path = Path(file_path)
        
        # Проверяем существование
        if not path.exists():
            return False
        
        # Проверяем расширение
        valid_extensions = {'.xlsx', '.xls'}
        if path.suffix.lower() not in valid_extensions:
            return False
        
        # Проверяем что файл не пустой
        if path.stat().st_size == 0:
            return False
        
        return True

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        Проверяет корректность номера телефона
        
        Args:
            phone: Номер телефона
            
        Returns:
            True если номер корректен
        """
        if not phone:
            return False
        
        # Очищаем от символов
        digits = re.sub(r'\D', '', phone)
        
        # Российские номера: 11 цифр начиная с 7 или 8, или 10 цифр
        if len(digits) == 11 and digits[0] in ('7', '8'):
            return True
        elif len(digits) == 10:
            return True
        
        return False

    @staticmethod
    def filter_ads_urls(urls: List[str]) -> List[str]:
        """
        Фильтрует рекламные ссылки
        
        Args:
            urls: Список URL
            
        Returns:
            Отфильтрованный список URL
        """
        filtered = []
        
        for url in urls:
            # Проверяем что URL не содержит рекламные домены
            is_ad = any(ads_domain in url for ads_domain in config.ADS_DOMAINS)
            if not is_ad:
                filtered.append(url)
        
        return filtered

    @staticmethod
    def clean_vacancy_url(url: str) -> str:
        """
        Очищает URL вакансии от параметров отслеживания
        
        Args:
            url: Исходный URL
            
        Returns:
            Очищенный URL
        """
        if "?" in url:
            return url.split("?")[0]
        return url

    @staticmethod
    def validate_output_directory(output_path: str) -> bool:
        """
        Проверяет что директория для вывода доступна
        
        Args:
            output_path: Путь к директории или файлу
            
        Returns:
            True если директория доступна
        """
        path = Path(output_path)
        
        # Если это файл, проверяем директорию
        if path.suffix:
            path = path.parent
        
        # Создаем директорию если её нет
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def validate_urls_list(self, urls: List[str]) -> dict:
        """
        Валидирует список URL и возвращает статистику
        
        Args:
            urls: Список URL для валидации
            
        Returns:
            Словарь со статистикой {total, valid, invalid, ads_filtered}
        """
        total = len(urls)
        valid = 0
        invalid = 0
        
        for url in urls:
            if self.validate_vacancy_url(url):
                valid += 1
            else:
                invalid += 1
                self.logger.warning(f"Некорректный URL: {url}")
        
        # Фильтруем рекламу
        filtered_urls = self.filter_ads_urls(urls)
        ads_filtered = total - len(filtered_urls)
        
        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "ads_filtered": ads_filtered,
        }
