"""
Тесты для модуля работы с Excel
"""

import pytest
import tempfile
import os
from pathlib import Path

import pandas as pd

from src.excel_manager import ExcelManager


class TestExcelManager:
    """Тесты для ExcelManager"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.excel_manager = ExcelManager()

    # ===== Тесты чтения URL из Excel =====

    def test_read_urls_from_excel_valid(self):
        """Тест чтения URL из корректного Excel файла"""
        # Создаем временный Excel файл с URL
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({
                "A": [
                    "https://hh.ru/vacancy/12345",
                    "https://hh.ru/vacancy/67890",
                    "some text",
                ]
            })
            df.to_excel(tmp.name, index=False)
            tmp_path = tmp.name
        
        try:
            urls = self.excel_manager.read_urls_from_excel(tmp_path)
            
            assert len(urls) == 2
            assert "https://hh.ru/vacancy/12345" in urls
            assert "https://hh.ru/vacancy/67890" in urls
        finally:
            os.unlink(tmp_path)

    def test_read_urls_from_excel_nonexistent(self):
        """Тест чтения из несуществующего файла"""
        with pytest.raises(FileNotFoundError):
            self.excel_manager.read_urls_from_excel("/nonexistent/file.xlsx")

    # ===== Тесты сохранения в Excel =====

    def test_save_to_excel_valid(self):
        """Тест сохранения данных в Excel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_output.xlsx")
            
            data = [
                {"vacancy": "Developer", "company": "Google", "city": "Moscow", "phone": "+7 999 123-45-67"},
                {"vacancy": "Manager", "company": "Yandex", "city": "St. Petersburg", "phone": "+7 888 765-43-21"},
            ]
            
            result = self.excel_manager.save_to_excel(data, output_file)
            
            assert result == output_file
            assert os.path.exists(output_file)
            
            # Проверя что файл можно прочитать
            df = pd.read_excel(output_file)
            assert len(df) == 2

    def test_save_to_excel_empty(self):
        """Тест сохранения пустых данных"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_output.xlsx")
            
            result = self.excel_manager.save_to_excel([], output_file)
            
            assert result == ""

    # ===== Тесты добавления в Excel =====

    def test_append_to_excel_new_file(self):
        """Тест добавления данных когда файл не существует"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_output.xlsx")
            
            data = [
                {"vacancy": "Developer", "company": "Google"},
            ]
            
            result = self.excel_manager.append_to_excel(data, output_file)
            
            assert result == output_file
            assert os.path.exists(output_file)

    def test_append_to_excel_existing_file(self):
        """Тест добавления данных в существующий файл"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_output.xlsx")
            
            # Создаем файл
            data1 = [{"vacancy": "Developer", "company": "Google"}]
            self.excel_manager.save_to_excel(data1, output_file)
            
            # Добавляем данные
            data2 = [{"vacancy": "Manager", "company": "Yandex"}]
            self.excel_manager.append_to_excel(data2, output_file)
            
            # Проверяем
            df = pd.read_excel(output_file)
            assert len(df) == 2

    # ===== Тесты получения информации о файле =====

    def test_get_excel_info_valid(self):
        """Тест получения информации о файле"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
            df.to_excel(tmp.name, index=False)
            tmp_path = tmp.name
        
        try:
            info = self.excel_manager.get_excel_info(tmp_path)
            
            assert "sheets" in info
            assert "total_rows" in info
            assert "columns" in info
            assert info["total_rows"] == 3
            assert len(info["columns"]) == 2
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
