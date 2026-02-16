import os
import re
import random
import asyncio
import pandas as pd
from pathlib import Path
from playwright.async_api import (
    async_playwright,
    Page as AsyncPage,
    TimeoutError as PWTimeoutError,
)


class HHParse:
    def __init__(self, input_file: str, max_num_firm: int, gui_works: bool):

        self.gui_works = gui_works
        self.enter_event = asyncio.Event() if gui_works else None
        self.use_gui_input = gui_works

        self.input_file = Path(input_file)
        self.max_num_firm = max_num_firm
        self.data_saving = "hh_parse_results/data.xlsx"
        self.warning_message()
        # Получаем данные фирмы для каждого URL в партии
        self.batch_results = []
        # БАЗОВЫЕ ТАЙМАУТЫ
        self.CONCURRENCY = 3  #                            Количество одновременно открытых вкладок браузера (2–3 оптимально)
        self.BATCH_CONCURRENCY_JITTER = True #             Иногда работаем 2 вкладками вместо 3 для естественности
        self.NAV_STAGGER_BETWEEN_TABS = (0.5, 0.9)  #     Пауза перед открытием КАЖДОЙ вкладки (чтобы не стартовали все разом)
        self.POST_NAV_IDLE = (0.35, 0.5)  #                Небольшая «заминка» после загрузки страницы перед действиями
        self.PAGE_DELAY_BETWEEN_BATCHES = (0.2, 0.4,)  #   Пауза между партиями ссылок (раньше была (2.0, 4.0))
        self.CLOSE_STAGGER_BETWEEN_TABS = (0.15, 0.25,)  # Вкладки закрываем с небольшой случайной паузой

        if os.path.exists(self.data_saving):
            os.remove(self.data_saving)

        # ВХОДНОЙ ФАЙЛ С ССЫЛКАМИ
        self.INPUT_SHEET = None  # Имя листа в Excel; None = использовать все листы
        self.URL_COLUMN = None  #  Имя колонки со ссылками; None = искать ссылки во всех колонках

        # ЧЕЛОВЕЧНОСТЬ / АНТИБАН-ПОВЕДЕНИЕ
        self.HUMAN = {
            "pre_page_warmup_scrolls": (1, 3),  #    Сколько раз «прогрелись» скроллом после открытия страницы
            "scroll_step_px": (250, 900),  #         Диапазон шага скролла в пикселях
            "scroll_pause_s": (0.18, 0.75),  #       Пауза между скроллами
            "hover_pause_s": (0.14, 0.42),  #        Пауза при наведении на элементы
            "pre_click_pause_s": (0.10, 0.28),  #    Короткая пауза перед кликом
            "post_click_pause_s": (0.12, 0.32),  #   Пауза сразу после клика
            "between_actions_pause": (0.10,0.30),  # Пауза между действиями (скролл, клик, наведение)
            "click_delay_jitter": (0.2, 0.4),  # Случайная задержка после клика по телефону (min и max)
        }

    async def human_sleep(self, a: float, b: float):
        """
        Приостанавливает выполнение на случайное количество секунд в диапазоне [a, b].
        Используется для имитации человеческих пауз и предотвращения блокировок!
        """
        await asyncio.sleep(random.uniform(a, b))

    async def press_and_rel(self):
        """Ожидает нажатия Enter из GUI или консоли"""
        if self.gui_works:
            # Ждем, пока GUI пошлет событие
            print("Ожидаю нажатия Enter из GUI...")
            await self.wait_for_gui_enter()
        else:
            # Старый способ - ждем из консоли
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input, "Готов? Нажми Enter в консоли: ")

    async def wait_for_gui_enter(self):
        """Асинхронно ждет события от GUI"""
        while not self.enter_event.is_set():
            await asyncio.sleep(0.3)
        self.enter_event.clear()  # Сбрасываем для следующего использования

    def trigger_enter_from_gui(self):
        """Вызывается из GUI для имитации нажатия Enter"""
        if self.gui_works and hasattr(self, "enter_event"):
            self.enter_event.set()

    def read_urls_from_excel_or_csv(self, sheet=None, url_column=None) -> list[str]:
        """
        Читает URL вакансий с hh.ru из Excel или CSV файла.
        Args:
            sheet: Имя листа Excel (None для всех листов)
            url_column: Имя колонки с URL (None для поиска во всех колонках)
        Return: Список URL вакансий hh.ru
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Файл не найден: {self.input_file}")

        # Регулярное выражение для поиска URL hh.ru
        url_re = re.compile(r"https?://(?:[a-z]+\.)?hh\.ru/vacancy/\d+")
        urls: list[str] = []

        if self.input_file.suffix.lower() in {".xlsx", ".xls"}:
            xls = pd.ExcelFile(self.input_file)
            sheets = [sheet] if sheet is not None else xls.sheet_names
            for sh in sheets:
                df = xls.parse(sh, dtype=str)
                if url_column and url_column in df.columns:
                    col = df[url_column].dropna().astype(str)
                    urls.extend(col.tolist())
                else:
                    for col in df.columns:
                        s = df[col].dropna().astype(str)
                        for val in s:
                            urls.extend(url_re.findall(val))
        elif self.input_file.suffix.lower() in {".csv", ".txt"}:
            df = pd.read_csv(self.input_file, dtype=str, sep=None, engine="python")
            if url_column and url_column in df.columns:
                col = df[url_column].dropna().astype(str)
                urls.extend(col.tolist())
            else:
                for col in df.columns:
                    s = df[col].dropna().astype(str)
                    for val in s:
                        urls.extend(url_re.findall(val))
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {self.input_file.suffix}")

        print(f"Прочитано {len(urls)} URL из файла: {self.input_file.name}")
        return urls

    async def data_output_to_xlsx(self, get_firm_data):
        """Быстрое сохранение в Excel"""
        if not get_firm_data:
            return
        
        try:
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.data_saving), exist_ok=True)
            
            new_df = pd.DataFrame(
                get_firm_data,
                columns=["URL", "Название вакансии", "Название компании", "Телефон", "ФИО"],
            )
            
            # Если файл не существует - создаем
            if not os.path.exists(self.data_saving):
                new_df.to_excel(self.data_saving, index=False)
                print(f"Создан файл: {len(get_firm_data)} записей")
                return
            
            # Если файл существует - добавляем строки
            try:
                # Читаем существующий файл
                existing_df = pd.read_excel(self.data_saving)
                
                # Объединяем и сохраняем (быстро)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.to_excel(self.data_saving, index=False)
                
            except Exception as e:
                print(f"Ошибка сохранения: {e}")
                
        except Exception as e:
            print(f"Ошибка: {e}")

    def get_random_user_agent(self):
        """Скрываем автоматизацию с помощью захода с разных систем"""
        user_agents = [
            # Windows Chrome - разные версии
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_7_10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)

    async def process_urls_with_pool(self, context, urls: list[str], update_callback=None):
        """
        Обрабатывает список URL с использованием пула страниц.
        Args:
            context: Контекст браузера Playwright
            urls: Список URL для обработки
        """
        if not urls:
            return

        # Пул создаём максимального размера; часть вкладок можем не использовать
        pages = [await context.new_page() for _ in range(self.CONCURRENCY)]
        try:
            it = iter(urls)  # Итератор по URL
            while True:
                # Иногда делаем партию меньше максимума, чтобы поведение было менее ровным
                batch_size = (
                    random.randint(max(1, self.CONCURRENCY - 1), self.CONCURRENCY)
                    if self.BATCH_CONCURRENCY_JITTER
                    else self.CONCURRENCY
                )
                batch_pages = pages[:batch_size]

                batch = []  # Инициализация списка для текущей партии
                for p in batch_pages:  # Цикл по страницам партии
                    try:
                        url = next(it)
                    except StopIteration:
                        return
                    batch.append((url, p))

                    # Не открываем все вкладки синхронно — ставим паузу перед каждым goto
                    await self.human_sleep(*self.NAV_STAGGER_BETWEEN_TABS)
                    try:
                        await p.goto(url, wait_until="domcontentloaded")
                    except PWTimeoutError:
                        print(f"Таймаут: {url}")
                        continue
                    
                for url, p in batch:
                    await self.human_sleep(*self.HUMAN["between_actions_pause"])

                    try:
                        # Извлекаем данные фирмы
                        firm_data = await self.__get_firm_data_from_page(p, url)
                        # Сохраняем результат только если есть телефон
                        if firm_data and firm_data[3] != "Телефон не найден":  # Индекс 4 = телефон
                            self.batch_results.append(firm_data)
                            print(f"Данные фирмы: {url} -> {firm_data}")
                            if update_callback:
                                update_callback(f"Успешно: {url}")
                        else:
                            print(f"Пропуск: телефон не найден для {url}")
                            if update_callback:
                                update_callback(f"Пропущено (нет телефона): {url}")

                    except Exception as e:
                        print(f"Ошибка при обработке {url}: {e}")
                        if update_callback:
                            update_callback(f"Ошибка: {url}")

                # Сохраняем все найденные данные партией (для оптимизации)
                if len(self.batch_results) >= 5:  # Сохраняем пачками по 20
                    await self.data_output_to_xlsx(self.batch_results)
                    self.batch_results = []  # Очищаем после сохранения
        finally:
            for p in pages:
                try:
                    await p.close()  # Закрытие страницы
                except Exception:
                    pass

    async def __get_firm_data_from_page(self, page, url: str):
        """Извлекает данные фирмы с открытой страницы"""
        if url.find("?") != -1:
            url = url[url.find("hh") : url.find("?") + 1]  # Берем ссылке, начиная с hh
        else:
            url = url[url.find("hh") :]

        firm_data = {
            "url": url,
            "firm_vacancy": "Не найдено",
            "company_name": "Не найдено",
            "true_phone": "Телефон не найден",
            "fio": "Не указано",
        }

        try:
            # Извлечение названия вакансии
            vacancy_element = await page.query_selector('[data-qa="vacancy-title"]')
            if vacancy_element:
                vacancy_text = await vacancy_element.text_content()
                if vacancy_text:
                    firm_data["firm_vacancy"] = vacancy_text.strip()
            # Извлечение названия компании
            company_element = await page.query_selector('[data-qa="vacancy-company-name"] span')
            if company_element:
                company_text = await company_element.text_content()
                if company_text:
                    firm_data["company_name"] = " ".join(company_text.strip().split("\xa0"))
            
            try:
                contact_btn = await page.query_selector('button[data-qa="show-employer-contacts show-employer-contacts_top-button"]')
                if contact_btn:  # Проверка на None
                    await contact_btn.click()
                    await self.human_sleep(0.5, 0.8)
                                
                # Номер телефона и ФИО - ищем через кнопку "Связаться"
                
                fio_element = await page.query_selector('div[data-qa="vacancy-contacts__fio"]')
                if fio_element:
                    fio_text = await fio_element.text_content()
                    if fio_text and fio_text.strip():
                        firm_data["fio"] = fio_text.strip()
                
                # Ищем телефон
                # Сначала ищем span с номером телефона
                phone_span = await page.query_selector('span[data-qa="vacancy-contacts__phone-number"]')
                
                if phone_span:
                    phone_text = await phone_span.text_content()
                    if phone_text and phone_text.strip():
                        # Очищаем телефон от лишних символов, оставляем только цифры и +
                        phone_clean = re.sub(r'[^\d+]', '', phone_text.strip())
                        firm_data["true_phone"] = phone_clean.lstrip('+')
                else:
                    # Если телефон не найден, возможно нужно кликнуть по блоку телефона
                    phone_block = await page.query_selector('div[data-qa="vacancy-contacts__phone"]')
                    if phone_block:
                        await phone_block.click()
                        # Ищем телефон после клика
                        await asyncio.sleep(0.5)
                        phone_span = await page.query_selector('span[data-qa="vacancy-contacts__phone-number"]')
                        if phone_span:
                            phone_text = await phone_span.text_content()
                            if phone_text and phone_text.strip():
                                phone_clean = re.sub(r'[^\d+]', '', phone_text.strip())
                                firm_data["true_phone"] = phone_clean.lstrip('+')
                                print(f"Телефон найден после клика: {firm_data['true_phone']}")
                            else:
                                firm_data["true_phone"] = "Телефон не найден"
                        else:
                            firm_data["true_phone"] = "Телефон не найден"
                    else:
                        firm_data["true_phone"] = "Телефон не найден"
                
            except Exception as e:
                print(f"Ошибка при поиске контактов: {e}")

                    
        except Exception as e:
            print(f"Ошибка при поиске контактов: {e}")
            firm_data["true_phone"] = f"Ошибка"


        except Exception as e:
            print(f"Ошибка при получении данных фирмы: {e}")

        # Возвращаем в формате списка
        return [
            firm_data["url"],
            firm_data["firm_vacancy"],
            firm_data["company_name"],
            firm_data["true_phone"],
            firm_data["fio"],
        ]

    def warning_message(self):
        print("\n" + "=" * 50)
        print("EDUCATIONAL USE ONLY - NO WARRANTY PROVIDED")
        print("This parser may violate Terms of Service.")
        print("Use only for learning web scraping techniques.")
        print("Author not responsible for any legal consequences.")
        print("=" * 50 + "\n")

    async def parse_main(self, update_callback=None):
        """Парсинг сайта"""
        urls = self.read_urls_from_excel_or_csv(self.INPUT_SHEET, self.URL_COLUMN)
        urls = urls[: self.max_num_firm]

        print(f"Новых ссылок к обработке: {len(urls)};")
        try:
            if update_callback and len(urls) == 0:
                update_callback(f"Внимание! Новых ссылок к обработке: {len(urls)};")
            else:
                update_callback(f"Новых ссылок к обработке: {len(urls)};")
        except:
            pass

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-web-security",
                    "--disable-site-isolation-trials",
                ],
            )  # headless=True - без графического итерфейса
            try:
                vp_w = random.randint(1200, 1400)
                vp_h = random.randint(760, 900)
                context = await browser.new_context(
                    viewport={"width": vp_w, "height": vp_h},
                    user_agent=self.get_random_user_agent(),
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                    extra_http_headers={"Cache-Control": "no-cache"},
                )

                # Ручной логин на первой ссылке (если есть что открывать)
                seed_url = urls[0] if urls else None
                if seed_url:

                    page = await context.new_page()  # Создание новой страницы

                    await asyncio.sleep(random.uniform(0.4, 0.8))
                    try:
                        await asyncio.sleep(random.uniform(0.5, 0.8))

                        # Потом на объявление
                        await page.goto(
                            seed_url,
                            wait_until="domcontentloaded",
                        )
                    except PWTimeoutError:
                        try:
                            await page.goto(seed_url, wait_until="domcontentloaded")
                        except PWTimeoutError:
                            print(f"Таймаут при загрузке {seed_url}")

                    await self.human_sleep(0.3, 0.7)

                    print("\nТвои действия:")  # Инструкция пользователю
                    print(" • если есть капча — реши;")
                    print(" • залогинься в Авито;")
                    print(" • оставь открытую страницу объявления.")

                    # Здесь ждем подтверждения входа
                    if self.gui_works:
                        if update_callback:
                            update_callback("Ожидание подтверждения входа... Нажмите 'Вход выполнен'")
                        await self.press_and_rel()  # Ждем нажатия кнопки в GUI
                    else:
                        # Старый способ для консоли
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, input, "Готов? Нажми Enter в консоли: ")

                    try:
                        await page.close()
                    except Exception:
                        pass
                        # Основной список из Excel
                try:
                    await self.process_urls_with_pool(context, urls, update_callback)
                    if self.batch_results != 0:
                        await self.data_output_to_xlsx(self.batch_results)
                except Exception as e:
                    print(f"Ошибка {e}")

            finally:
                await browser.close()


async def main():
    parser = HHParse(
        input_file="abc.xlsx",
        max_num_firm=5,  # Сколько вакансий собрать
        gui_works=False,
    )
    await parser.parse_main()


if __name__ == "__main__":
    asyncio.run(main())
