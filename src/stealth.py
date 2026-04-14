"""
Расширенные stealth настройки для обхода детекции автоматизации
Включает дополнительные скрипты и техники для скрытия Playwright
"""

import random
from typing import Dict, List


class StealthManager:
    """Управление stealth настройками для обхода антибот систем"""

    # Скрипты для скрытия автоматизации
    ANTI_DETECTION_SCRIPTS: List[str] = [
        # Скрываем webdriver
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """,
        
        # Подделываем chrome объект
        """
        window.navigator.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        """,
        
        # Подделываем plugins
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojo5hoos2pe399' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' }
            ],
        });
        """,
        
        # Устанавливаем языки
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ru-RU', 'ru', 'en-US', 'en'],
        });
        """,
        
        # Подделываем permissions
        """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """,
        
        # Скрываем selenium и webdriver в prototype
        """
        delete navigator.__proto__.webdriver;
        """,
        
        # Fix для Chrome headless
        """
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        """,
        
        # Подделываем WebGL vendor
        """
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
        """,
        
        # Подделываем hardware concurrency
        """
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => Math.floor(Math.random() * 4) + 4
        });
        """,
        
        # Подделываем device memory
        """
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => [4, 8, 16][Math.floor(Math.random() * 3)]
        });
        """,
        
        # Подделываем max touch points
        """
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0
        });
        """,
        
        # Скрываем automation-controlled
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        """,
    ]

    @staticmethod
    def get_complete_stealth_script() -> str:
        """
        Возвращает полный stealth скрипт для инициализации
        
        Returns:
            JavaScript код для скрытия автоматизации
        """
        return "\n".join(StealthManager.ANTI_DETECTION_SCRIPTS)

    @staticmethod
    def get_random_screen_resolution() -> Dict[str, int]:
        """
        Генерирует случайное разрешение экрана
        
        Returns:
            Словарь с width и height
        """
        resolutions = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
            {"width": 1600, "height": 900},
        ]
        return random.choice(resolutions)

    @staticmethod
    def get_random_platform() -> str:
        """
        Возвращает случайную платформу
        
        Returns:
            Строка с платформой
        """
        platforms = [
            "Win32",
            "Win64",
        ]
        return random.choice(platforms)

    @staticmethod
    def get_browser_launch_args() -> List[str]:
        """
        Возвращает аргументы для запуска браузера с максимальной скрытностью
        
        Returns:
            Список аргументов
        """
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--media-cache-size=1",
            "--disk-cache-size=1",
        ]

    @staticmethod
    def get_random_timezone() -> str:
        """
        Возвращает случайную временную зону (в пределах РФ)
        
        Returns:
            Строка с timezone
        """
        timezones = [
            "Europe/Moscow",
            "Europe/Samara",
            "Asia/Yekaterinburg",
            "Asia/Omsk",
            "Asia/Novosibirsk",
            "Asia/Krasnoyarsk",
            "Asia/Irkutsk",
            "Asia/Yakutsk",
            "Asia/Vladivostok",
        ]
        return random.choice(timezones)

    @staticmethod
    def get_random_locale() -> str:
        """
        Возвращает случайную локаль (русская)
        
        Returns:
            Строка с локалью
        """
        locales = [
            "ru-RU",
            "ru",
        ]
        return random.choice(locales)
