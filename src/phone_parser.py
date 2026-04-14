"""
Оптимизированный парсер телефонов HH.ru
Использует модульную архитектуру с разделением ответственности
"""

import os
import re
import random
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
import openpyxl
from playwright.async_api import async_playwright, Page as AsyncPage

import config
from logger import get_logger
from src.base_parser import BaseHHParser
from src.vacancy_extractor import VacancyExtractor
from src.browser_manager import BrowserManager
from src.validator import HHValidator
from src.excel_manager import ExcelManager


class HHPhoneParser(BaseHHParser):
    """
    Парсер телефонов из вакансий HH.ru
    
    Особенности:
    - Работает с Excel файлом содержащим URL вакансий
    - Переходит на каждую вакансию и извлекает контактные данные
    - Поддерживает GUI режим с подтверждением входа
    - Сохраняет результаты в Excel
    """
    
    def __init__(
        self,
        input_file: str,
        max_num_firm: int = config.MAX_VACANCIES,
        gui_works: bool = False,
        proxy_config: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация парсера телефонов
        
        Args:
            input_file: Путь к Excel файлу с URL вакансий
            max_num_firm: Максимальное количество вакансий для парсинга
            gui_works: Флаг работы с GUI
            proxy_config: Конфигурация прокси
        """
        super().__init__(max_vacancies=max_num_firm, gui_works=gui_works, proxy_config=proxy_config)
        
        self.input_file = Path(input_file)
        self.output_file = config.OUTPUT_FILE
        
        # Компоненты
        self.logger = get_logger()
        self.validator = HHValidator()
        self.excel_manager = ExcelManager()
        self.vacancy_extractor = VacancyExtractor()
        self.browser_manager = BrowserManager()
        
        # Данные
        self.list_of_companies: List[List[str]] = []
        self.link: str = ""  # URL для парсинга (устанавливается в parse_main)
        self.count_page: int = 0
        
        # Проверяем входной файл
        if not self.validator.validate_excel_file(str(self.input_file)):
            raise ValueError(f"Некорректный Excel файл: {self.input_file}")
        
        # Удаляем старый результат если существует
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            self.logger.info(f"Удален старый файл результатов: {self.output_file}")

    async def parse_main(self, update_callback=None):
        """
        Основная функция парсинга телефонов
        
        Args:
            update_callback: Callback для обновления GUI
        """
        self.logger.info("Запуск парсинга телефонов...")
        
        try:
            # Создаем браузер
            browser, context, page = await self.browser_manager.create_browser(headless=False)
            
            self.browser = browser
            self.context = context
            self.page = page
            
            # Загружаем URL из файла
            urls = self.excel_manager.read_urls_from_excel(
                str(self.input_file),
                sheet_name=config.INPUT_SHEET,
                url_column=config.URL_COLUMN,
            )
            
            if not urls:
                self.logger.error("Не найдено URL в файле")
                if update_callback:
                    update_callback("Ошибка: Не найдено URL в файле")
                return
            
            # Фильтруем и валидируем URL
            urls = self.validator.filter_ads_urls(urls)
            url_stats = self.validator.validate_urls_list(urls)
            
            self.logger.info(f"Загружено URL: {url_stats['total']} "
                           f"(валидных: {url_stats['valid']}, "
                           f"рекламы отфильтровано: {url_stats['ads_filtered']})")
            
            if update_callback:
                update_callback(f"Найдено {url_stats['valid']} вакансий для парсинга")
            
            # Переходим на HH.ru для авторизации если нужно
            await page.goto(
                "https://hh.ru",
                wait_until="domcontentloaded",
                timeout=self.nav_timeout,
            )
            
            await self.browser_manager.human_scroll_jitter(page)
            
            # Ждем подтверждения входа если работаем с GUI
            if self.gui_works:
                if update_callback:
                    update_callback("Требуется авторизация. Войдите и нажмите 'Вход выполнен'")
                await self.wait_for_gui_enter()
            
            # Обрабатываем вакансии
            processed_count = 0
            
            for url in urls:
                if len(self.list_of_companies) >= self.max_vacancies:
                    self.logger.info(f"Достигнут лимит в {self.max_vacancies} вакансий")
                    break
                
                # Очищаем URL
                url = self.validator.clean_vacancy_url(url)
                
                if not self.validator.validate_vacancy_url(url):
                    self.logger.warning(f"Пропускаем некорректный URL: {url}")
                    continue
                
                processed_count += 1
                self.logger.info(f"\n[#{processed_count}] Парсим вакансию: {url[:80]}...")
                
                if update_callback:
                    update_callback(f"Парсинг вакансии #{processed_count}")
                
                # Парсим вакансию
                vacancy_data = await self.vacancy_extractor.parse_vacancy_page(
                    page=page,
                    context=context,
                    vacancy_url=url,
                    nav_timeout=self.nav_timeout,
                )
                
                if vacancy_data["vacancy"]:
                    # Формируем запись
                    firm_data = [
                        vacancy_data["vacancy"],
                        vacancy_data["company"],
                        vacancy_data["city"],
                        vacancy_data["phone"],
                        url,
                    ]
                    
                    self.list_of_companies.append(firm_data)
                    
                    self.logger.info(f"Добавлено: {vacancy_data['vacancy'][:50]}...")
                    self.logger.info(f"  Компания: {vacancy_data['company'][:30]}...")
                    self.logger.info(f"  Город: {vacancy_data['city']}")
                    self.logger.info(f"  Телефон: {vacancy_data['phone']}")
                    
                    # Сохраняем каждые 3 записи
                    if len(self.list_of_companies) % 3 == 0:
                        await self._save_results()
                        self.list_of_companies = []
                
                # Пауза между вакансиями
                await self.browser_manager.human_sleep(0.4, 0.8)
            
            # Сохраняем остатки
            if self.list_of_companies:
                await self._save_results()
                self.list_of_companies = []
            
            # Загружаем финальный файл для подсчета
            total_records = self._count_results()
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"ПАРСИНГ ЗАВЕРШЕН!")
            self.logger.info(f"Всего собрано вакансий: {total_records}")
            self.logger.info(f"Файл сохранен: {self.output_file}")
            self.logger.info(f"{'='*50}")
            
            if update_callback:
                update_callback(f"Парсинг завершен! Собрано {total_records} вакансий")
            
        except Exception as e:
            error_msg = f"Произошла ошибка: {e}"
            self.logger.error(error_msg)
            if update_callback:
                update_callback(error_msg)
            raise
        
        finally:
            # Закрываем браузер
            await self.browser_manager.close_browser()

    async def _save_results(self):
        """Сохраняет текущие результаты в Excel"""
        if not self.list_of_companies:
            return
        
        try:
            # Создаем DataFrame
            df = pd.DataFrame(
                self.list_of_companies,
                columns=config.EXCEL_COLUMNS
            )
            
            # Сохраняем
            if os.path.exists(self.output_file):
                # Добавляем в существующий файл
                existing_df = pd.read_excel(self.output_file)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_excel(self.output_file, index=False)
            else:
                # Создаем новый файл
                df.to_excel(self.output_file, index=False)
            
            self.logger.info(f"Сохранено {len(self.list_of_companies)} записей")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении результатов: {e}")

    def _count_results(self) -> int:
        """Подсчитывает общее количество результатов"""
        try:
            if os.path.exists(self.output_file):
                df = pd.read_excel(self.output_file)
                return len(df)
        except Exception:
            pass
        
        return 0


async def main():
    """Точка входа для автономного запуска"""
    # Пример использования
    input_file = "path/to/your/vacancies.xlsx"  # Замените на свой файл
    
    if not os.path.exists(input_file):
        print(f"Файл не найден: {input_file}")
        print("Создайте Excel файл с URL вакансий в первой колонке")
        return
    
    parser = HHPhoneParser(
        input_file=input_file,
        max_num_firm=20,
        gui_works=False,
    )
    
    await parser.parse_main()


if __name__ == "__main__":
    asyncio.run(main())
