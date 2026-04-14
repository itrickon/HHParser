"""
Оптимизированный сборщик вакансий по URL поиска HH.ru
Собирает вакансии со страниц поиска без авторизации
"""

import os
import re
import random
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, Page as AsyncPage

import config
from logger import get_logger
from src.base_parser import BaseHHParser
from src.vacancy_extractor import VacancyExtractor
from src.browser_manager import BrowserManager
from src.validator import HHValidator


class HHVacancyCollector(BaseHHParser):
    """
    Сборщик вакансий со страниц поиска HH.ru
    
    Особенности:
    - Работает без авторизации
    - Переходит по URL поиска и собирает вакансии
    - Поддерживает пагинацию (переход по страницам)
    - Сохраняет результаты автоматически
    """
    
    def __init__(
        self,
        search_url: str,
        max_vacancies: int = config.MAX_VACANCIES,
        gui_works: bool = False,
        proxy_config: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация сборщика вакансий
        
        Args:
            search_url: URL страницы поиска HH.ru
            max_vacancies: Максимальное количество вакансий для сбора
            gui_works: Флаг работы с GUI
            proxy_config: Конфигурация прокси
        """
        super().__init__(max_vacancies=max_vacancies, gui_works=gui_works, proxy_config=proxy_config)
        
        # Валидируем URL поиска
        self.validator = HHValidator()
        if not self.validator.validate_search_url(search_url):
            raise ValueError(f"Некорректный URL поиска: {search_url}")
        
        self.search_url = search_url
        self.output_file = config.URL_SEARCH_OUTPUT
        
        # Компоненты
        self.logger = get_logger()
        self.vacancy_extractor = VacancyExtractor()
        self.browser_manager = BrowserManager()
        
        # Данные
        self.vacancies: List[Dict[str, Any]] = []
        self.count_page: int = 0

    async def parse_main(self, update_callback=None):
        """
        Основная функция сбора вакансий
        
        Args:
            update_callback: Callback для обновления GUI
        """
        self.logger.info(f"Запуск сбора вакансий: {self.search_url}")
        self.logger.info(f"Максимальное количество: {self.max_vacancies}")
        
        try:
            # Создаем браузер
            browser, context, page = await self.browser_manager.create_browser(headless=False)
            
            self.browser = browser
            self.context = context
            self.page = page
            
            # Переходим на страницу поиска
            await page.goto(
                self.search_url,
                wait_until="domcontentloaded",
                timeout=self.nav_timeout,
            )
            
            await self.browser_manager.human_scroll_jitter(page)
            
            if update_callback:
                update_callback(f"Начало сбора вакансий: {self.search_url[:80]}...")
            
            page_num = 1
            processed_count = 0
            
            while len(self.vacancies) < self.max_vacancies:
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Страница: {page_num}")
                self.logger.info(f"Собрано: {len(self.vacancies)}/{self.max_vacancies}")
                self.logger.info(f"{'='*50}")
                
                if update_callback:
                    update_callback(f"Страница {page_num}: {len(self.vacancies)}/{self.max_vacancies}")
                
                # Получаем все карточки вакансий на странице
                vacancy_cards = await self._get_vacancy_cards(page)
                
                if not vacancy_cards:
                    self.logger.info("Не найдено карточек вакансий на странице")
                    break
                
                self.logger.info(f"Найдено карточек: {len(vacancy_cards)}")
                
                # Обрабатываем каждую карточку
                for card in vacancy_cards:
                    if len(self.vacancies) >= self.max_vacancies:
                        break
                    
                    processed_count += 1
                    self.logger.info(f"\n[#{processed_count}] Парсим карточку...")
                    
                    if update_callback:
                        update_callback(f"Парсинг вакансии #{processed_count}")
                    
                    # Получаем базовые данные из карточки
                    basic_data = await self.vacancy_extractor.parse_vacancy_card(card)
                    
                    if not basic_data["vacancy"]:
                        self.logger.info("Пропускаем - нет названия вакансии")
                        continue
                    
                    # Получаем ссылку на вакансию
                    vacancy_url = await self._get_vacancy_url_from_card(card)
                    
                    if vacancy_url:
                        self.logger.info(f"Переходим за телефоном: {vacancy_url[:80]}...")
                        
                        # Переходим на страницу вакансии для получения телефона
                        full_data = await self.vacancy_extractor.parse_vacancy_page(
                            page=page,
                            context=context,
                            vacancy_url=vacancy_url,
                            nav_timeout=self.nav_timeout,
                        )
                        
                        # Объединяем данные (предпочитаем данные со страницы)
                        if full_data["vacancy"]:
                            basic_data["vacancy"] = full_data["vacancy"]
                        if full_data["company"]:
                            basic_data["company"] = full_data["company"]
                        if full_data["city"] and full_data["city"] != "Не указан":
                            basic_data["city"] = full_data["city"]
                        if full_data["phone"] and full_data["phone"] != "Требуется переход":
                            basic_data["phone"] = full_data["phone"]
                        
                        # Добавляем URL
                        basic_data["url"] = vacancy_url
                    
                    # Добавляем в список
                    self.vacancies.append(basic_data)
                    
                    self.logger.info(f"Добавлено: {basic_data['vacancy'][:50]}...")
                    self.logger.info(f"  Компания: {basic_data['company'][:30]}...")
                    self.logger.info(f"  Город: {basic_data['city']}")
                    self.logger.info(f"  Телефон: {basic_data['phone']}")
                    
                    # Пауза между вакансиями
                    await self.browser_manager.human_sleep(0.4, 0.8)
                
                # Сохраняем результаты
                await self._save_results()
                
                # Проверяем лимит
                if len(self.vacancies) >= self.max_vacancies:
                    self.logger.info(f"Достигнут лимит в {self.max_vacancies} вакансий")
                    break
                
                # Переход на следующую страницу
                self.logger.info("\nПроверяем наличие следующей страницы...")
                if await self._go_to_next_page(page):
                    page_num += 1
                    await self.browser_manager.human_sleep(0.4, 0.7)
                else:
                    self.logger.info("Больше нет страниц для парсинга")
                    break
                
                # Задержка между страницами
                await self.browser_manager.human_sleep(*config.PAGE_DELAY_BETWEEN_BATCHES)
            
            # Финальное сохранение
            final_count = len(self.vacancies)
            await self._save_results()
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"СБОР ЗАВЕРШЕН!")
            self.logger.info(f"Всего собрано вакансий: {final_count}")
            self.logger.info(f"Файл сохранен: {self.output_file}")
            self.logger.info(f"{'='*50}")
            
            if update_callback:
                update_callback(f"Сбор завершен! Найдено {final_count} вакансий")
            
        except Exception as e:
            error_msg = f"Произошла ошибка: {e}"
            self.logger.error(error_msg)
            if update_callback:
                update_callback(error_msg)
            raise
        
        finally:
            # Закрываем браузер
            await self.browser_manager.close_browser()

    async def _get_vacancy_cards(self, page: AsyncPage) -> List:
        """Получает все карточки вакансий на странице"""
        try:
            vacancy_cards = await page.query_selector_all(config.VACANCY_CARD_SELECTOR)
            return vacancy_cards[:self.max_vacancies - len(self.vacancies)]
        except Exception as e:
            self.logger.error(f"Ошибка при поиске карточек: {e}")
            return []

    async def _get_vacancy_url_from_card(self, vacancy_card) -> Optional[str]:
        """Получает ссылку на вакансию из карточки"""
        try:
            link_el = await vacancy_card.query_selector(config.VACANCY_TITLE_SELECTOR)
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    # Убираем параметры отслеживания
                    clean_href = self.validator.clean_vacancy_url(href)
                    
                    # Преобразуем относительные ссылки в абсолютные
                    if not clean_href.startswith("http"):
                        clean_href = f"https://hh.ru{clean_href}"
                    
                    return clean_href
        except Exception as e:
            self.logger.error(f"Ошибка при получении ссылки: {e}")
        
        return None

    async def _go_to_next_page(self, page: AsyncPage) -> bool:
        """Переходит на следующую страницу результатов"""
        try:
            # Ищем кнопку "Далее"
            next_button = await page.query_selector(config.PAGER_NEXT_SELECTOR)
            
            if not next_button:
                self.logger.info("Кнопка 'Далее' не найдена")
                return False
            
            # Проверяем активность
            href = await next_button.get_attribute("href")
            if not href:
                self.logger.info("Кнопка 'Далее' неактивна")
                return False
            
            await self.browser_manager.human_hover(page, next_button)
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            self.logger.info("Переходим на следующую страницу...")
            await next_button.click()
            await asyncio.sleep(random.uniform(0.2, 0.7))
            
            # Ждем загрузки
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Скроллим
            await self.browser_manager.human_scroll_jitter(page)
            
            self.count_page += 1
            self.logger.info(f"Успешно перешли на страницу {self.count_page + 1}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при переходе на следующую страницу: {e}")
            return False

    async def _save_results(self):
        """Сохраняет текущие результаты в Excel"""
        if not self.vacancies:
            return
        
        try:
            # Создаем DataFrame
            df = pd.DataFrame(self.vacancies)
            
            # Переупорядочиваем колонки
            if all(col in df.columns for col in config.EXCEL_COLUMNS):
                df = df[config.EXCEL_COLUMNS]
            
            # Создаем директорию если её нет
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем
            df.to_excel(self.output_file, index=False, sheet_name=config.EXCEL_SHEET_NAME)
            
            self.logger.info(f"Сохранено {len(self.vacancies)} записей в {self.output_file}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении результатов: {e}")


async def main():
    """Точка входа для автономного запуска"""
    # Пример использования
    search_url = "https://hh.ru/search/vacancy?area=1&text=python"  # Замените на свой URL
    
    collector = HHVacancyCollector(
        search_url=search_url,
        max_vacancies=50,
        gui_works=False,
    )
    
    await collector.parse_main()


if __name__ == "__main__":
    asyncio.run(main())
