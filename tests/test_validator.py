"""
Тесты для модуля валидации HHValidator
"""

import pytest
import tempfile
import os
from pathlib import Path

import pandas as pd

from src.validator import HHValidator


class TestHHValidator:
    """Тесты для HHValidator"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.validator = HHValidator()

    # ===== Тесты валидации URL вакансий =====

    def test_validate_vacancy_url_valid(self):
        """Тест корректных URL вакансий"""
        valid_urls = [
            "https://hh.ru/vacancy/12345678",
            "http://hh.ru/vacancy/87654321",
            "https://moscow.hh.ru/vacancy/11111111",
        ]
        
        for url in valid_urls:
            assert self.validator.validate_vacancy_url(url) is True, f"URL должен быть валидным: {url}"

    def test_validate_vacancy_url_invalid(self):
        """Тест некорректных URL вакансий"""
        invalid_urls = [
            "https://google.com",
            "https://hh.ru/search/vacancy",
            "not_a_url",
            "https://hh.ru/job/12345",
            "",
        ]
        
        for url in invalid_urls:
            assert self.validator.validate_vacancy_url(url) is False, f"URL должен быть невалидным: {url}"

    # ===== Тесты валидации URL поиска =====

    def test_validate_search_url_valid(self):
        """Тест корректных URL поиска"""
        valid_urls = [
            "https://hh.ru/search/vacancy?area=1",
            "https://moscow.hh.ru/search/vacancy?text=python",
            "http://hh.ru/search/vacancy",
        ]
        
        for url in valid_urls:
            assert self.validator.validate_search_url(url) is True, f"URL поиска должен быть валидным: {url}"

    def test_validate_search_url_invalid(self):
        """Тест некорректных URL поиска"""
        invalid_urls = [
            "https://hh.ru/vacancy/12345",
            "https://google.com/search",
            "not_a_url",
        ]
        
        for url in invalid_urls:
            assert self.validator.validate_search_url(url) is False, f"URL поиска должен быть невалидным: {url}"

    # ===== Тесты валидации Excel файлов =====

    def test_validate_excel_file_valid(self):
        """Тест корректных Excel файлов"""
        # Создаем временный Excel файл
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({"col1": [1, 2, 3]})
            df.to_excel(tmp.name, index=False)
            tmp_path = tmp.name
        
        try:
            assert self.validator.validate_excel_file(tmp_path) is True
        finally:
            os.unlink(tmp_path)

    def test_validate_excel_file_nonexistent(self):
        """Тест несуществующего файла"""
        assert self.validator.validate_excel_file("/nonexistent/file.xlsx") is False

    def test_validate_excel_file_wrong_extension(self):
        """Тест файла с неправильным расширением"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name
        
        try:
            assert self.validator.validate_excel_file(tmp_path) is False
        finally:
            os.unlink(tmp_path)

    def test_validate_excel_file_empty(self):
        """Тест пустого файла"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            assert self.validator.validate_excel_file(tmp_path) is False
        finally:
            os.unlink(tmp_path)

    # ===== Тесты валидации номеров телефонов =====

    def test_validate_phone_number_valid(self):
        """Тест корректных номеров телефонов"""
        valid_phones = [
            "+7 (999) 123-45-67",
            "89991234567",
            "79991234567",
            "9991234567",
            "+79991234567",
        ]
        
        for phone in valid_phones:
            assert self.validator.validate_phone_number(phone) is True, f"Номер должен быть валидным: {phone}"

    def test_validate_phone_number_invalid(self):
        """Тест некорректных номеров телефонов"""
        invalid_phones = [
            "",
            "123",
            "abc",
            "999123",
        ]
        
        for phone in invalid_phones:
            assert self.validator.validate_phone_number(phone) is False, f"Номер должен быть невалидным: {phone}"

    # ===== Тесты фильтрации рекламы =====

    def test_filter_ads_urls(self):
        """Тест фильтрации рекламных ссылок"""
        urls = [
            "https://hh.ru/vacancy/12345",
            "https://adsrv.hh.ru/vacancy/99999",
            "https://hh.ru/vacancy/67890",
            "https://ads.hh.ru/job/11111",
        ]
        
        filtered = self.validator.filter_ads_urls(urls)
        
        assert len(filtered) == 2
        assert "https://adsrv.hh.ru/vacancy/99999" not in filtered
        assert "https://ads.hh.ru/job/11111" not in filtered

    # ===== Тесты очистки URL =====

    def test_clean_vacancy_url(self):
        """Тест очистки URL от параметров"""
        url_with_params = "https://hh.ru/vacancy/12345?utm_source=google&utm_medium=cpc"
        cleaned = self.validator.clean_vacancy_url(url_with_params)
        
        assert cleaned == "https://hh.ru/vacancy/12345"

    def test_clean_vacancy_url_no_params(self):
        """Тест очистки URL без параметров"""
        url = "https://hh.ru/vacancy/12345"
        cleaned = self.validator.clean_vacancy_url(url)
        
        assert cleaned == url

    # ===== Тесты валидации директорий =====

    def test_validate_output_directory_valid(self):
        """Тест корректной директории"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.xlsx")
            assert self.validator.validate_output_directory(output_path) is True

    # ===== Тесты статистики URL =====

    def test_validate_urls_list(self):
        """Тест статистики списка URL"""
        urls = [
            "https://hh.ru/vacancy/12345",
            "https://hh.ru/vacancy/67890",
            "https://google.com",
            "https://adsrv.hh.ru/vacancy/99999",
        ]
        
        stats = self.validator.validate_urls_list(urls)
        
        assert stats["total"] == 4
        assert stats["valid"] == 2
        assert stats["invalid"] == 2
        assert stats["ads_filtered"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
