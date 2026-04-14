"""
Конфигурация проекта HHParser
Все настройки и константы вынесены сюда для удобства изменения
"""

from pathlib import Path
from typing import Tuple, Optional

# ===== Директории проекта =====
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = DATA_DIR / "results"

# Создаем директории если их нет
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ===== Файлы данных =====
INPUT_FILE: Optional[str] = None  # Путь к входному Excel файлу
OUTPUT_FILE: str = str(OUTPUT_DIR / "hh_parser_results.xlsx")
URL_SEARCH_OUTPUT: str = str(OUTPUT_DIR / "hh_url_search_results.xlsx")

# ===== Настройки парсера =====
MAX_VACANCIES: int = 20  # Количество вакансий для парсинга по умолчанию
CONCURRENCY: int = 3  # Количество одновременно открытых вкладок (2-3 оптимально)
BATCH_CONCURRENCY_JITTER: bool = True  # Иногда работаем 2 вкладками вместо 3
NAV_TIMEOUT: int = 30000  # Таймаут навигации в мс (30 секунд)

# ===== Тайминги и задержки =====
NAV_STAGGER_BETWEEN_TABS: Tuple[float, float] = (0.5, 0.9)  # Пауза перед открытием каждой вкладки
POST_NAV_IDLE: Tuple[float, float] = (0.35, 0.5)  # Заминка после загрузки страницы
PAGE_DELAY_BETWEEN_BATCHES: Tuple[float, float] = (0.2, 0.4)  # Пауза между партиями ссылок
CLOSE_STAGGER_BETWEEN_TABS: Tuple[float, float] = (0.15, 0.25)  # Пауза при закрытии вкладок
BETWEEN_ACTIONS_PAUSE: Tuple[float, float] = (0.10, 0.30)  # Пауза между действиями

# ===== Настройки браузера =====
VIEWPORT_WIDTH_MIN: int = 1200
VIEWPORT_WIDTH_MAX: int = 1400
VIEWPORT_HEIGHT_MIN: int = 760
VIEWPORT_HEIGHT_MAX: int = 900

# User-Agent списки для рандомизации
USER_AGENTS: list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

LOCALE: str = "ru-RU"
TIMEZONE_ID: str = "Europe/Moscow"

# ===== Настройки GUI =====
APP_TITLE: str = "HHParser - Парсер вакансий HH.ru"
APP_VERSION: str = "2.0.0"
APP_WINDOW_SIZE: str = "920x850"
APP_MIN_SIZE: Tuple[int, int] = (800, 700)

# Цвета для логирования
LOG_COLORS = {
    "INFO": "black",
    "ERROR": "red",
    "WARNING": "#cf7c00",
    "SUCCESS": "#00a800",
}

LOG_COLORS_DARK = {
    "INFO": "white",
    "ERROR": "#ff6666",
    "WARNING": "#ffc766",
    "SUCCESS": "#00e600",
}

# ===== Регулярные выражения =====
HH_VACANCY_URL_PATTERN = r"https?://(?:[a-z]+\.)?hh\.ru/vacancy/\d+"
HH_SEARCH_URL_PATTERN = r"hh\.ru/search/vacancy"
PHONE_NUMBER_PATTERN = r"\+?7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"

# ===== Селекторы для парсинга =====
# Карточки вакансий
VACANCY_CARD_SELECTOR = '[data-qa="vacancy-serp__vacancy"]'
VACANCY_TITLE_SELECTOR = '[data-qa="serp-item__title"]'
VACANCY_EMPLOYER_SELECTOR = '[data-qa="vacancy-serp__vacancy-employer"]'
VACANCY_ADDRESS_SELECTOR = '[data-qa="vacancy-serp__vacancy-address"]'

# Страница вакансии
VACANCY_PAGE_TITLE_SELECTOR = '[data-qa="vacancy-title"]'
VACANCY_PAGE_COMPANY_SELECTOR = '[data-qa="vacancy-company-name"]'
VACANCY_PAGE_LOCATION_SELECTOR = '[data-qa="vacancy-view-location"]'

# Кнопки контактов
CONTACT_BUTTON_SELECTORS = [
    'button[data-qa="vacancy-serp__vacancy_contacts"]',
    'a[data-qa="vacancy-contacts-button"]',
    'button:has-text("Связаться")',
    'a:has-text("Связаться")',
]

PHONE_SELECTORS = [
    '[data-qa="vacancy-contacts__phone"]',
    'span[class*="phone"]',
    'a[href^="tel:"]',
]

# Пагинация
PAGER_NEXT_SELECTOR = 'a[data-qa="pager-next"]'

# ===== Фильтры =====
ADS_DOMAINS: list = [
    "adsrv.hh.ru",
    "ads.hh.ru",
]

# ===== Настройки прокси (опционально) =====
PROXY_ENABLED: bool = False
PROXY_SERVER: Optional[str] = None  # Формат: "http://user:pass@proxy:port"
PROXY_USERNAME: Optional[str] = None
PROXY_PASSWORD: Optional[str] = None

# ===== Логирование =====
LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE: str = str(LOG_DIR / "hh_parser.log")
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: int = 5

# ===== Excel настройки =====
EXCEL_COLUMNS: list = ["vacancy", "company", "city", "phone", "url"]
EXCEL_SHEET_NAME: str = "Results"

# ===== Входной файл настройки =====
INPUT_SHEET: Optional[str] = None  # Имя листа в Excel; None = использовать все листы
URL_COLUMN: Optional[str] = None  # Имя колонки с URL; None = искать ссылки во всех колонках
