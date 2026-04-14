"""
Модуль для работы с вакансиями HH.ru
Извлечение данных из карточек и страниц вакансий
"""

import re
import random
import asyncio
import logging
from typing import Optional, Dict, Any, List

from playwright.async_api import Page as AsyncPage

import config
from logger import get_logger


class VacancyExtractor:
    """Класс для извлечения данных из вакансий HH.ru"""
    
    def __init__(self):
        self.logger = get_logger()

    async def extract_phone_from_popup(self, page: AsyncPage) -> str:
        """
        Извлекает номер телефона из попапа контактов
        
        Args:
            page: Страница с открытым попапом контактов
            
        Returns:
            Форматированный номер телефона или сообщение об ошибке
        """
        try:
            # Ждем появления номера
            await page.wait_for_selector(
                '[data-qa="vacancy-contacts__phone"]',
                timeout=5000,
            )
            
            # Пробуем несколько селекторов
            for selector in config.PHONE_SELECTORS:
                try:
                    phone_element = await page.query_selector(selector)
                    if phone_element and await phone_element.is_visible():
                        phone_text = (await phone_element.text_content()).strip()
                        if phone_text:
                            return self._format_phone_number(phone_text)
                except:
                    continue
            
            return "Номер не найден"
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении телефона: {e}")
            return "Ошибка"

    def _format_phone_number(self, phone_text: str) -> str:
        """
        Форматирует номер телефона к стандартному виду
        
        Args:
            phone_text: Исходный текст номера
            
        Returns:
            Форматированный номер
        """
        # Очищаем от лишних символов
        phone_digits = re.sub(r"\D", "", phone_text)
        
        if len(phone_digits) >= 10:
            # Форматируем номер
            if phone_digits.startswith("7") and len(phone_digits) == 11:
                return f"+{phone_digits[0]} {phone_digits[1:4]} {phone_digits[4:7]}-{phone_digits[7:9]}-{phone_digits[9:]}"
            elif phone_digits.startswith("8") and len(phone_digits) == 11:
                return f"+7 {phone_digits[1:4]} {phone_digits[4:7]}-{phone_digits[7:9]}-{phone_digits[9:]}"
            elif len(phone_digits) == 10:
                return f"+7 {phone_digits[0:3]} {phone_digits[3:6]}-{phone_digits[6:8]}-{phone_digits[8:]}"
        
        return phone_text

    async def click_contact_button(self, page: AsyncPage) -> bool:
        """
        Кликает по кнопке 'Связаться' для показа контактов
        
        Args:
            page: Страница с вакансией
            
        Returns:
            True если кнопка успешно нажата
        """
        try:
            for selector in config.CONTACT_BUTTON_SELECTORS:
                try:
                    contact_button = await page.query_selector(selector)
                    if contact_button and await contact_button.is_visible():
                        # Имитируем человеческое поведение
                        await self._human_hover(page, contact_button)
                        await asyncio.sleep(random.uniform(0.2, 0.4))
                        
                        await contact_button.click()
                        await asyncio.sleep(random.uniform(0.5, 0.8))
                        
                        # Ждем появления попапа
                        await page.wait_for_selector(
                            'div[class*="magritte-drop-container"], '
                            '[data-qa="vacancy-contacts__phone"]',
                            timeout=5000,
                        )
                        return True
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при клике на кнопку связи: {e}")
            return False

    async def close_contact_popup(self, page: AsyncPage):
        """Закрывает всплывающее окно контактов"""
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(random.uniform(0.3, 0.5))
        except:
            pass

    @staticmethod
    async def _human_hover(page: AsyncPage, element):
        """Имитация человеческого наведения"""
        try:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await element.hover()
            await asyncio.sleep(random.uniform(0.1, 0.2))
        except:
            pass

    async def extract_city_from_location(self, location_text: str) -> str:
        """
        Извлекает город из текста локации
        
        Args:
            location_text: Текст локации (например "Москва, ул. Ленина")
            
        Returns:
            Название города
        """
        if not location_text:
            return "Не указан"
        
        location_text = location_text.strip()
        
        # Убираем лишние слова
        remove_words = [
            "район", "область", "край", "республика",
            "г.", "м.", "ул.", "пр.", "д.",
        ]
        for word in remove_words:
            location_text = location_text.replace(word, "").replace(word.title(), "")
        
        # Разделяем по разделителям
        parts = re.split(r"[,;.\-()]", location_text)
        if parts:
            return parts[0].strip()
        
        return location_text

    async def parse_vacancy_card(self, vacancy_card) -> Dict[str, str]:
        """
        Парсит данные из карточки вакансии на странице поиска
        
        Args:
            vacancy_card: Элемент карточки вакансии
            
        Returns:
            Словарь с данными {vacancy, company, city, phone}
        """
        page_data = {"vacancy": "", "company": "", "city": "", "phone": ""}
        
        try:
            # Название вакансии
            try:
                title_el = await vacancy_card.query_selector(config.VACANCY_TITLE_SELECTOR)
                if title_el:
                    page_data["vacancy"] = (await title_el.text_content()).strip()
            except Exception as e:
                self.logger.debug(f"Ошибка при извлечении названия: {e}")
            
            # Компания
            try:
                company_el = await vacancy_card.query_selector(config.VACANCY_EMPLOYER_SELECTOR)
                if company_el:
                    company_text = await company_el.text_content()
                    page_data["company"] = " ".join(company_text.split()).strip()
            except Exception as e:
                self.logger.debug(f"Ошибка при извлечении компании: {e}")
            
            # Город
            try:
                city_el = await vacancy_card.query_selector(config.VACANCY_ADDRESS_SELECTOR)
                if city_el:
                    city_text = await city_el.text_content()
                    page_data["city"] = await self.extract_city_from_location(city_text)
                else:
                    page_data["city"] = "Не указан"
            except Exception as e:
                self.logger.debug(f"Ошибка при извлечении города: {e}")
                page_data["city"] = "Ошибка"
            
            # Телефон будем получать при переходе на страницу вакансии
            page_data["phone"] = "Требуется переход"
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге карточки: {e}")
            return page_data

    async def parse_vacancy_page(
        self,
        page: AsyncPage,
        context,
        vacancy_url: str,
        nav_timeout: int = 30000,
    ) -> Dict[str, str]:
        """
        Парсит полную страницу вакансии для получения всех данных включая телефон
        
        Args:
            page: Текущая страница
            context: Контекст браузера для создания новой страницы
            vacancy_url: URL страницы вакансии
            nav_timeout: Таймаут навигации
            
        Returns:
            Словарь с данными {vacancy, company, city, phone}
        """
        page_data = {"vacancy": "", "company": "", "city": "", "phone": ""}
        vacancy_page = None
        
        try:
            # Создаем новую страницу
            vacancy_page = await context.new_page()
            await asyncio.sleep(random.uniform(0.5, 0.9))
            
            # Переходим на страницу вакансии
            await vacancy_page.goto(
                vacancy_url,
                wait_until="domcontentloaded",
                timeout=nav_timeout,
            )
            await asyncio.sleep(random.uniform(0.35, 0.5))
            
            # Скроллим для имитации человека
            await self._human_scroll_jitter(vacancy_page)
            
            # Название вакансии
            try:
                title_el = await vacancy_page.query_selector(config.VACANCY_PAGE_TITLE_SELECTOR)
                if title_el:
                    page_data["vacancy"] = (await title_el.text_content()).strip()
            except:
                pass
            
            # Компания
            try:
                company_el = await vacancy_page.query_selector(config.VACANCY_PAGE_COMPANY_SELECTOR)
                if company_el:
                    company_text = await company_el.text_content()
                    page_data["company"] = " ".join(company_text.split()).strip()
            except:
                pass
            
            # Город
            try:
                city_el = await vacancy_page.query_selector(config.VACANCY_PAGE_LOCATION_SELECTOR)
                if city_el:
                    city_text = await city_el.text_content()
                    page_data["city"] = await self.extract_city_from_location(city_text)
                else:
                    page_data["city"] = "Не указан"
            except:
                page_data["city"] = "Ошибка"
            
            # Телефон через кнопку "Связаться"
            try:
                if await self.click_contact_button(vacancy_page):
                    page_data["phone"] = await self.extract_phone_from_popup(vacancy_page)
                    await self.close_contact_popup(vacancy_page)
                else:
                    page_data["phone"] = "Нет кнопки связи"
            except Exception as e:
                self.logger.error(f"Ошибка при получении телефона: {e}")
                page_data["phone"] = "Ошибка"
            
            await asyncio.sleep(random.uniform(0.15, 0.25))
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге страницы вакансии {vacancy_url}: {e}")
        
        finally:
            # Закрываем страницу
            if vacancy_page:
                await vacancy_page.close()
        
        return page_data

    @staticmethod
    async def _human_scroll_jitter(page: AsyncPage):
        """Имитация человеческого скроллинга"""
        try:
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            if random.random() < 0.3:
                await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
                await asyncio.sleep(random.uniform(0.1, 0.2))
        except:
            pass
