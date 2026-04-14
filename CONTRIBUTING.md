# Руководство по контрибьюции

Спасибо за интерес к улучшению HHParser! Вот как вы можете внести свой вклад:

## 🚀 Начало работы

### 1. Форкните репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/HHParser.git
cd HHParser
```

### 2. Установите зависимости для разработки

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

### 3. Создайте ветку для вашей функции

```bash
git checkout -b feature/my-amazing-feature
```

## 📝 Стандарты кода

### Стиль кода

Мы используем **Black** для форматирования и **flake8** для линтинга:

```bash
# Форматирование
black src/ tests/

# Линтинг
flake8 src/ tests/
```

### Type Hints

Все функции должны иметь type hints:

```python
def parse_vacancy(url: str, timeout: int = 30) -> dict[str, str]:
    """Parse vacancy page and extract data.
    
    Args:
        url: URL of the vacancy page
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with vacancy data
    """
    pass
```

### Документация

- Используйте docstrings для всех публичных функций и классов
- Следуйте формату Google Style Guide

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Конкретный тест
pytest tests/test_validator.py -v
```

### Написание тестов

- Каждый новый модуль должен иметь тесты
- Используйте pytest fixtures
- Тестируйте как успешные случаи, так и ошибки

Пример:

```python
def test_validate_vacancy_url_valid():
    """Test valid vacancy URLs"""
    validator = HHValidator()
    assert validator.validate_vacancy_url("https://hh.ru/vacancy/12345") is True
```

## 🔄 Процесс Pull Request

### 1. Перед отправкой

- [ ] Запустите все тесты: `pytest`
- [ ] Проверьте стиль: `black . && flake8`
- [ ] Обновите документацию если нужно
- [ ] Добавьте запись в CHANGELOG.md

### 2. Создайте PR

Опишите что было сделано:

```markdown
## Описание
Краткое описание изменений

## Тип изменений
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Тесты
- [ ] Добавлены unit-тесты
- [ ] Все тесты проходят

## Чеклист
- [ ] Код следует стандартам проекта
- [ ] Добавлены docstrings
- [ ] Обновлена документация
```

### 3. Code Review

- Минимум 1 аппрув от мейнтейнера
- Ответьте на комментарии ревьюеров
- Внесите исправления если нужно

## 🐛 Баг репорты

Если нашли баг, создайте Issue с:

1. **Описанием проблемы**
2. **Шагами воспроизведения**
3. **Ожидаемым поведением**
4. **Скриншотами** (если применимо)
5. **Окружением** (ОС, Python версия, и т.д.)

## 💡 Предложения функций

Для новых функций создайте Issue с меткой `enhancement`:

1. **Название функции**
2. **Описание** - что должна делать
3. **Обоснование** - почему это полезно
4. **Альтернативы** - какие есть варианты

## 📊 Архитектурные решения

Для крупных изменений:

1. Обсудите в Issue перед реализацией
2. Предложите архитектуру
3. Дождесь фидбека от мейнтейнеров
4. Реализуйте после аппрува

## 🎯 Области для улучшений

### Приоритетные:

- [ ] Улучшение антидетект защиты
- [ ] Поддержка других сайтов (не только HH)
- [ ] Веб-интерфейс вместо GUI
- [ ] API для интеграций
- [ ] Docker контейнеризация

### Nice to have:

- [ ] Кэширование результатов
- [ ] Параллельный парсинг
- [ ] Экспорт в разные форматы (CSV, JSON)
- [ ] Интеграция с базами данных

## 🙏 Спасибо!

Каждый вклад важен и помогает сделать проект лучше! 🎉
