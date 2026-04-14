"""
Базовый класс для всех парсеров HH.ru
Содержит общую логику: работа с браузером, антидетект, валидация и т.д.
"""

import os
import re
import random
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import pandas as pd
import openpyxl
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page as AsyncPage,
    Playwright,
    TimeoutError as PWTimeoutError,
)

import config
from logger import get_logger


class BaseHHParser:
    """
    Базовый класс для парсеров HH.ru
    
    Содержит:
    - Управление браузером Playwright
    - Антидетект (User-Agent, viewport, fingerprint)
    - Валидация URL
    - Работа с Excel файлами
    - Human-like поведение (случайные задержки, скроллинг)
    """
    
    def __init__(
        self,
        max_vacancies: int = config.MAX_VACANCIES,
        gui_works: bool = False,
        proxy_config: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация базового парсера
        
        Args:
            max_vacancies: Максимальное количество вакансий для парсинга
            gui_works: Флаг работы с GUI
            proxy_config: Конфигурация прокси {server, username, password}
        """
        self.logger = get_logger()
        self.max_vacancies = max_vacancies
        self.gui_works = gui_works
        self.proxy_config = proxy_config
        
        # asyncio Event для GUI
        self.enter_event: Optional[asyncio.Event] = asyncio.Event() if gui_works else None
        
        # Данные для сохранения
        self.results: List[Dict[str, Any]] = []
        self.output_file: str = config.OUTPUT_FILE
        
        # Browser компоненты (инициализируются в parse_main)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[AsyncPage] = None
        
        # Таймауты
        self.nav_timeout: int = config.NAV_TIMEOUT
        
        self.logger.info(f"BaseHHParser инициализирован (max_vacancies={max_vacancies})")

    # ===== Антидетект и рандомизация =====

    @staticmethod
    def get_random_user_agent() -> str:
        """Возвращает случайный User-Agent из списка"""
        return random.choice(config.USER_AGENTS)

    @staticmethod
    def get_random_viewport() -> Dict[str, int]:
        """Генерирует случайный размер viewport"""
        return {
            "width": random.randint(config.VIEWPORT_WIDTH_MIN, config.VIEWPORT_WIDTH_MAX),
            "height": random.randint(config.VIEWPORT_HEIGHT_MIN, config.VIEWPORT_HEIGHT_MAX),
        }

    @staticmethod
    async def human_sleep(a: float, b: float):
        """
        Асинхронная пауза для имитации человеческого поведения
        
        Args:
            a: Минимальное время паузы
            b: Максимальное время паузы
        """
        await asyncio.sleep(random.uniform(a, b))

    @staticmethod
    async def human_scroll_jitter(page: AsyncPage):
        """
        Имитация человеческого скроллинга с случайными движениями
        
        Args:
            page: Объект страницы Playwright
        """
        try:
            # Небольшой скролл вниз
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Иногда скролл обратно вверх
            if random.random() < 0.3:
                await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
                await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            logging.debug(f"Ошибка при скроллинге: {e}")

    @staticmethod
    async def human_hover(page: AsyncPage, element):
        """
        Имитация человеческого наведения на элемент
        
        Args:
            page: Объект страницы Playwright
            element: CSS селектор или элемент
        """
        try:
            if isinstance(element, str):
                element = await page.query_selector(element)
            
            if element:
                # Двигаемся к элементу с небольшой случайной задержкой
                await asyncio.sleep(random.uniform(0.05, 0.15))
                await element.hover()
                await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            logging.debug(f"Ошибка при hover: {e}")

    # ===== Валидация =====

    @staticmethod
    def validate_hh_vacancy_url(url: str) -> bool:
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
    def validate_hh_search_url(url: str) -> bool:
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

    # ===== Работа с Excel =====

    @staticmethod
    def read_urls_from_excel(
        file_path: str,
        sheet_name: Optional[str] = None,
        url_column: Optional[str] = None,
    ) -> List[str]:
        """
        Читает URL вакансий из Excel файла
        
        Args:
            file_path: Путь к Excel файлу
            sheet_name: Имя листа (None = все листы)
            url_column: Имя колонки с URL (None = поиск во всех колонках)
            
        Returns:
            Список URL вакансий hh.ru
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        url_pattern = re.compile(config.HH_VACANCY_URL_PATTERN)
        urls: List[str] = []
        
        try:
            xls = pd.ExcelFile(file_path)
            sheets = [sheet_name] if sheet_name else xls.sheet_names
            
            for sheet in sheets:
                df = xls.parse(sheet, dtype=str)
                
                if url_column and url_column in df.columns:
                    # Ищем в конкретной колонке
                    col_data = df[url_column].dropna().astype(str)
                    for val in col_data:
                        found_urls = url_pattern.findall(val)
                        urls.extend(found_urls)
                else:
                    # Ищем во всех колонках
                    for col in df.columns:
                        col_data = df[col].dropna().astype(str)
                        for val in col_data:
                            found_urls = url_pattern.findall(val)
                            urls.extend(found_urls)
            
            # Убираем дубликаты
            unique_urls = list(dict.fromkeys(urls))
            logging.info(f"Найдено {len(unique_urls)} уникальных URL из {len(urls)}")
            
            return unique_urls
            
        except Exception as e:
            logging.error(f"Ошибка при чтении Excel файла: {e}")
            raise

    def save_to_excel(self, data: List[List[str]], output_file: Optional[str] = None):
        """
        Сохраняет данные в Excel файл
        
        Args:
            data: Список списков с данными [[vacancy, company, city, phone], ...]
            output_file: Путь к файлу (по умолчанию config.OUTPUT_FILE)
        """
        if not data:
            self.logger.warning("Нет данных для сохранения")
            return
        
        output_file = output_file or self.output_file
        
        try:
            # Создаем DataFrame
            df = pd.DataFrame(data, columns=config.EXCEL_COLUMNS)
            
            # Сохраняем в Excel
            df.to_excel(output_file, index=False, sheet_name=config.EXCEL_SHEET_NAME)
            
            self.logger.info(f"Данные сохранены в {output_file} ({len(data)} записей)")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении в Excel: {e}")
            raise

    def append_to_excel(self, data: List[List[str]], output_file: Optional[str] = None):
        """
        Добавляет данные в существующий Excel файл
        
        Args:
            data: Список списков с данными
            output_file: Путь к файлу
        """
        if not data:
            return
        
        output_file = output_file or self.output_file
        output_path = Path(output_file)
        
        try:
            if output_path.exists():
                # Читаем существующий файл
                existing_df = pd.read_excel(output_file, sheet_name=config.EXCEL_SHEET_NAME)
                new_df = pd.DataFrame(data, columns=config.EXCEL_COLUMNS)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.to_excel(output_file, index=False, sheet_name=config.EXCEL_SHEET_NAME)
            else:
                # Создаем новый файл
                self.save_to_excel(data, output_file)
                
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении в Excel: {e}")
            raise

    # ===== Управление браузером =====

    async def create_browser(
        self,
        headless: bool = False,
    ) -> Tuple[Browser, BrowserContext, AsyncPage]:
        """
        Создает браузер с настройками антидетекта
        
        Args:
            headless: Запуск в headless режиме (по умолчанию False)
            
        Returns:
            Кортеж (browser, context, page)
        """
        self.playwright = await async_playwright().start()
        
        # Запуск браузера
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        
        # Настройки viewport
        viewport = self.get_random_viewport()
        
        # Конфигурация прокси если включена
        proxy = None
        if config.PROXY_ENABLED and self.proxy_config:
            proxy = {
                "server": self.proxy_config.get("server", ""),
            }
            if self.proxy_config.get("username"):
                proxy["username"] = self.proxy_config["username"]
            if self.proxy_config.get("password"):
                proxy["password"] = self.proxy_config["password"]
        
        # Создание контекста
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=self.get_random_user_agent(),
            locale=config.LOCALE,
            timezone_id=config.TIMEZONE_ID,
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
            },
            proxy=proxy,
        )
        
        # Скрытие автоматизации
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.navigator.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en'],
            });
        """)
        
        # Создание страницы
        self.page = await self.context.new_page()
        
        self.logger.info(f"Браузер созданлен (viewport={viewport})")
        
        return self.browser, self.context, self.page

    async def close_browser(self):
        """Закрывает браузер и освобождает ресурсы"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.logger.info("Браузер закрыт")
            
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии браузера: {e}")

    # ===== GUI взаимодействие =====

    async def wait_for_gui_enter(self):
        """Ждет нажатия Enter из GUI"""
        if not self.gui_works or not self.enter_event:
            return
        
        self.logger.info("Ожидание подтверждения от GUI...")
        while not self.enter_event.is_set():
            await asyncio.sleep(0.3)
        
        self.enter_event.clear()
        self.logger.info("Подтверждение получено от GUI")

    def trigger_enter_from_gui(self):
        """Вызывается из GUI для имитации нажатия Enter"""
        if self.gui_works and self.enter_event:
            self.enter_event.set()

    # ===== Абстрактные методы (должны быть реализованы в наследниках) =====

    async def parse_main(self, update_callback=None):
        """
        Основной метод парсинга (должен быть реализован в наследниках)
        
        Args:
            update_callback: Callback для обновления GUI
        """
        raise NotImplementedError("Метод parse_main должен быть реализован в наследнике")

    # ===== Контекстный менеджер =====

    async def __aenter__(self):
        """Вход в контекстный менеджер"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        await self.close_browser()
