"""
Тесты для stealth модуля
"""

import pytest
from src.stealth import StealthManager


class TestStealthManager:
    """Тесты для StealthManager"""

    # ===== Тесты получения stealth скрипта =====

    def test_get_complete_stealth_script(self):
        """Тест получения полного stealth скрипта"""
        script = StealthManager.get_complete_stealth_script()
        
        assert isinstance(script, str)
        assert len(script) > 0
        assert "webdriver" in script
        assert "chrome" in script.lower()

    # ===== Тесты рандомизации =====

    def test_get_random_screen_resolution(self):
        """Тест получения случайного разрешения экрана"""
        resolution = StealthManager.get_random_screen_resolution()
        
        assert "width" in resolution
        assert "height" in resolution
        assert isinstance(resolution["width"], int)
        assert isinstance(resolution["height"], int)
        assert resolution["width"] > 0
        assert resolution["height"] > 0

    def test_get_random_platform(self):
        """Тест получения случайной платформы"""
        platform = StealthManager.get_random_platform()
        
        assert isinstance(platform, str)
        assert platform in ["Win32", "Win64"]

    def test_get_random_timezone(self):
        """Тест получения случайной временной зоны"""
        timezone = StealthManager.get_random_timezone()
        
        assert isinstance(timezone, str)
        assert "Europe" in timezone or "Asia" in timezone

    def test_get_random_locale(self):
        """Тест получения случайной локали"""
        locale = StealthManager.get_random_locale()
        
        assert isinstance(locale, str)
        assert locale in ["ru-RU", "ru"]

    # ===== Тесты аргументов запуска =====

    def test_get_browser_launch_args(self):
        """Тест получения аргументов для запуска браузера"""
        args = StealthManager.get_browser_launch_args()
        
        assert isinstance(args, list)
        assert len(args) > 0
        assert "--no-sandbox" in args
        assert "--disable-blink-features=AutomationControlled" in args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
