"""
Модуль для управления браузером Playwright
Создание, настройка и закрытие браузера с антидетектом
"""

import random
import asyncio
import logging
from typing import Optional, Dict, Tuple

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page as AsyncPage,
    Playwright,
)

import config
from logger import get_logger
from src.stealth import StealthManager


class BrowserManager:
    """Менеджер браузера с поддержкой антидетекта"""
    
    def __init__(
        self,
        headless: bool = False,
        proxy_config: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация менеджера браузера
        
        Args:
            headless: Запуск в headless режиме
            proxy_config: Конфигурация прокси {server, username, password}
        """
        self.logger = get_logger()
        self.headless = headless
        self.proxy_config = proxy_config
        
        # Компоненты браузера
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[AsyncPage] = None

    @staticmethod
    def get_random_user_agent() -> str:
        """Возвращает случайный User-Agent"""
        return random.choice(config.USER_AGENTS)

    @staticmethod
    def get_random_viewport() -> Dict[str, int]:
        """Генерирует случайный размер viewport"""
        return {
            "width": random.randint(config.VIEWPORT_WIDTH_MIN, config.VIEWPORT_WIDTH_MAX),
            "height": random.randint(config.VIEWPORT_HEIGHT_MIN, config.VIEWPORT_HEIGHT_MAX),
        }

    async def create_browser(self) -> Tuple[Browser, BrowserContext, AsyncPage]:
        """
        Создает браузер с настройками антидетекта
        
        Returns:
            Кортеж (browser, context, page)
        """
        self.logger.info("Создание браузера...")
        
        # Запускаем Playwright
        self.playwright = await async_playwright().start()
        
        # Создаем браузер
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=StealthManager.get_browser_launch_args(),
        )
        
        # Настройки viewport
        viewport = self.get_random_viewport()
        self.logger.debug(f"Viewport: {viewport}")
        
        # Конфигурация прокси
        proxy = None
        if config.PROXY_ENABLED and self.proxy_config:
            proxy = {"server": self.proxy_config.get("server", "")}
            if self.proxy_config.get("username"):
                proxy["username"] = self.proxy_config["username"]
            if self.proxy_config.get("password"):
                proxy["password"] = self.proxy_config["password"]
            self.logger.info(f"Прокси включен: {proxy['server']}")
        
        # Создаем контекст
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
        
        # Inject anti-detection scripts
        await self.context.add_init_script(StealthManager.get_complete_stealth_script())
        
        # Создаем страницу
        self.page = await self.context.new_page()
        
        self.logger.info(f"Браузер созданлен (viewport={viewport['width']}x{viewport['height']})")
        
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

    async def human_sleep(self, a: float, b: float):
        """Асинхронная пауза для имитации человека"""
        await asyncio.sleep(random.uniform(a, b))

    async def human_scroll_jitter(self, page: AsyncPage):
        """Имитация человеческого скроллинга"""
        try:
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            if random.random() < 0.3:
                await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
                await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            self.logger.debug(f"Ошибка при скроллинге: {e}")

    async def human_hover(self, page: AsyncPage, element):
        """Имитация человеческого наведения"""
        try:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await element.hover()
            await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception as e:
            self.logger.debug(f"Ошибка при hover: {e}")
