# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Обзор проекта

Неофициальный Python SDK для Яндекс Тег Менеджера. Работает с внутренним GraphQL API Яндекса по адресу `metrika.yandex.ru/api/metrika`, предоставляя программный интерфейс для управления тегами, триггерами, переменными и контейнерами. Документация и комментарии в коде — на русском языке.

## Команды

```bash
# Установка зависимостей
pip install requests

# Быстрый тест API (нужен config.py с учётными данными)
python test_api.py

# Запуск примеров
python examples/basic_usage.py
```

Формальных тестов, линтера и системы сборки нет — единственная зависимость `requests` указана в `requirements.txt`.

## Архитектура

Четыре модуля с чётким разделением ответственности:

- **`ytm_api/client.py`** — класс `YandexTagManagerAPI`: все методы API (CRUD для тегов, триггеров, переменных; кастомные шаблоны; persistent DL-переменные; публикация; экспорт/импорт). Управляет HTTP-сессией, заголовками авторизации (`x-csrf-token`, `x-uid`, cookie `Session_id`). Все публичные методы принимают `container_id` первым параметром.

- **`ytm_api/models.py`** — dataclass-модели (`Tag`, `Trigger`, `Variable`, `Template`, `ActivationCondition` и др.) с сериализацией через `from_dict()`/`to_dict()`. Также содержит классы-константы: `TriggerTemplates`, `TagTemplates`, `VariableTemplates`, `ConditionOperators`, `BuiltInVariables`.

- **`ytm_api/queries.py`** — строки GraphQL-запросов и мутаций, составленные из переиспользуемых фрагментов. Включает мутации для шаблонов: `MUTATION_CREATE_TEMPLATE`, `MUTATION_PUBLISH_TEMPLATE`, `MUTATION_EDIT_TEMPLATE`.

- **`ytm_api/__init__.py`** — публичная поверхность пакета; реэкспортирует клиент, модели и константы.

## Ключевые паттерны

- **Добавление нового метода API**: определить GraphQL-запрос в `queries.py` → добавить метод в `YandexTagManagerAPI` в `client.py`, вызывающий `self._request(query, variables)` → распарсить ответ в модель из `models.py`
- **Фабрика моделей**: все модели используют `@dataclass` с `from_dict(data: dict)` classmethod, а не прямую инициализацию из сырых данных API
- **Константы шаблонов**: ID шаблонов тегов/триггеров/переменных хранятся как статические атрибуты классов (не enum) в `models.py`
- **Авторизация**: сессионные учётные данные из DevTools браузера; конфигурируются в `config.py` (в git-ignore, шаблон — `config.example.py`)

## Особенности API ЯТМ

- **Кастомные шаблоны**: lifecycle — `createYtmTemplate` (draft) → `publishYtmTemplate` → использование. `parameterId` параметров **меняется при каждой публикации**, финальные ID только в ответе `publishYtmTemplate`.
- **`templateVersion` в input** — передавать строкой, не int (иначе 500 Internal Server Error).
- **`enablingConditions: []`** — обязательное поле для параметров шаблона, даже если пустое.
- **Шаблон `custom_js` не существует** — ЯТМ не поддерживает Custom JavaScript переменные (в отличие от GTM).
- **dataLayer не накапливает состояние** — eventless-пуши (`dataLayer.push({key: val})` без `event`) полностью игнорируются. Persistent DL-переменные решают это через пару: обычная DL-переменная + кастомный шаблон с `templateStorage`.

### Шаблоны тегов (проверено в превью dpmn.ru 30.09.2026)

- **Колбэки** — `data.ytmOnSuccess()` / `data.ytmOnFailure()`, без них публикация падает на линтере. Скрипт грузится через `require('loadScript')`, `injectScript` нет. Полная карта доступных API — в комментарии раздела «ШАБЛОНЫ ТЕГОВ ДЛЯ ГАЛЕРЕИ» в `client.py`.
- **Ошибки линтера** приходят в `publishYtmTemplate` как JSON с `lint_errors` / `permission_errors`, а текст ошибок GraphQL подсказывает имена полей и значений enum.
- **`canLoadScriptUrls`: маски в хосте в рантайме не работают.** `https://*.dinamikapro.ru/…`, `**.ru`, `*.*.ru` линтер пропускает, но в браузере — `Permission denied for loadScript`. Работает только точный хост, в пути `*` допустим. Без зоны (`https://*/…`) не пропускает уже линтер.
- **`canAccessGlobals` в тегах работает** (`callInWindow('ym', …)`, `callInWindow('webVitals.onLCP', cb)`). Но результат вызова копируется в sandbox: если функция возвращает цикличный объект (например, `posthog.init` возвращает экземпляр), будет `Maximum call stack size exceeded`. Такие функции не вызывать; `copyFromWindow` — только для примитивов.
- **Заглушка по образцу сниппета** — через `createQueue('x')` + `createQueue('x._i')`. Если передать `setInWindow` объект с вложенным массивом, библиотека не распознаёт его как массив.
- **Тип параметра `Table`** в enum есть, но колонки через API задать не удалось. Рабочие типы — `TextInput`, `DropDownMenu`.
- **E2E**: первый прогон сразу после `preview()` часто видит старую версию, повторять. posthog-js в headless считает браузер ботом и не отправляет события — проверять вызовы, а не доставку. Custom HTML ЯТМ выполняет синхронно из `tag.js`, поэтому в стеке он выглядит как код Метрики; различать по верхнему кадру.
