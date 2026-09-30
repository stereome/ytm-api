# Yandex Tag Manager API SDK

## Обзор

Неофициальный Python SDK для программного управления Яндекс Тег Менеджером. Работает через внутренний GraphQL API `metrika.yandex.ru/api/metrika`.

Автор: Сергей Захарченко, Dopamine Analytics

### Что умеет SDK

| Функция | Метод | Описание |
|---------|-------|----------|
| **Теги** | `get_tags()` | Получить список тегов контейнера |
| | `create_tag()` | Создать тег (Custom HTML или по шаблону) |
| | `update_tag()` | Обновить существующий тег |
| | `delete_tag()` | Удалить тег |
| **Триггеры** | `get_triggers()` | Получить список триггеров |
| | `create_trigger()` | Создать триггер с условиями |
| | `delete_trigger()` | Удалить триггер |
| **Переменные** | `get_variables()` | Встроенные переменные (для подстановки) |
| | `get_custom_variables()` | Кастомные переменные контейнера |
| | `create_variable()` | Создать кастомную переменную (общий метод) |
| | `create_js_variable()` | JavaScript Variable (window.xxx) |
| | `create_data_layer_variable()` | Data Layer Variable |
| | `create_cookie_variable()` | Cookie Variable |
| | `create_constant_variable()` | Константа |
| | `create_dom_element_variable()` | DOM Element Variable |
| | `create_url_variable()` | URL Variable (компоненты URL) |
| | `create_referrer_variable()` | Referrer Variable |
| | `create_lookup_table_variable()` | Таблица поиска (маппинг) |
| | `create_random_number_variable()` | Случайное число |
| | `delete_variable()` | Удалить переменную |
| **Шаблоны** | `get_templates()` | Список доступных шаблонов |
| | `create_custom_template()` | Создать кастомный шаблон |
| | `publish_template()` | Опубликовать кастомный шаблон |
| | `create_variable_from_template()` | Создать переменную из кастомного шаблона |
| **Готовые шаблоны** | `create_url_query_param_template()` | URL Query Parameter (UTM-метки) |
| | `create_local_storage_template()` | localStorage Variable |
| | `create_cookie_value_template()` | Cookie Value |
| | `create_referrer_domain_template()` | Referrer Domain |
| | `create_session_page_views_template()` | Просмотры за сессию |
| | `create_visit_number_template()` | Номер визита |
| | `create_traffic_source_template()` | Источник трафика (JSON) |
| | `create_attribution_source_template()` | Атрибуция (UTM/реферер) |
| | `create_utm_last_touch_template()` | UTM Last Touch |
| | `create_ym_client_id_template()` | Metrica Client ID |
| | `create_is_returning_visitor_template()` | Новый/вернувшийся |
| | `create_timestamp_template()` | Timestamp (ms/s/ISO) |
| **Persistent DL** | `create_persistent_dl_template()` | Шаблон persistent DataLayer |
| | `create_persistent_dl_variable()` | Persistent DL переменная (пара) |
| | `create_persistent_dl_variables()` | Массовое создание persistent DL |
| **DL Interceptor** | `setup_dl_interceptor()` | Перехватчик eventless DL-пушей |
| | `create_intercepted_dl_variable()` | Переменная из перехваченного DL |
| | `create_intercepted_dl_variables()` | Массовое создание |
| **Публикация** | `get_changelog()` | Changelog между версиями |
| | `publish()` | Опубликовать контейнер |
| | `preview()` | Активировать preview-режим |
| **Экспорт/Импорт** | `export_container()` | Экспорт контейнера в JSON |
| | `import_container()` | Импорт из экспорта |
| **Утилиты** | `create_html_tag_with_trigger()` | Быстро создать тег + триггер |

---

## Установка и настройка

### Требования

- Python 3.10+
- `requests` (`pip install requests`)

### Авторизация

SDK использует сессионную авторизацию браузера. Три параметра нужно получить из DevTools:

1. Открыть https://metrika.yandex.ru, перейти в раздел Тег Менеджер
2. DevTools (F12) -> Network -> любой запрос к `api/metrika`
3. Из Request Headers скопировать:
   - `x-csrf-token` -> параметр `csrf_token`
   - `x-uid` -> параметр `uid`
4. Из Cookie скопировать:
   - `Session_id` -> параметр `session_id`

```python
from ytm_api import YandexTagManagerAPI

api = YandexTagManagerAPI(
    session_id="3:1769918318.5.2...",   # Cookie Session_id
    csrf_token="8980da54d11975764...",   # Header x-csrf-token
    uid="1153393446",                    # Header x-uid
)
```

### Container ID

**Важно:** Container ID -- это НЕ ID счётчика Яндекс Метрики!

Container ID виден в теле (Payload) запросов к `api/metrika` как поле `containerId`. Пример:

- ID счётчика Метрики: `106472777` (виден в URL)
- Container ID: `1080803` (виден в Payload запроса)

---

## Архитектура

```
ytm_api/
  __init__.py     # Публичная поверхность пакета
  client.py       # Класс YandexTagManagerAPI — все методы API
  models.py       # Dataclass-модели и константы шаблонов
  queries.py      # GraphQL запросы и мутации
```

### client.py — Клиент API

Основной класс `YandexTagManagerAPI`. Управляет HTTP-сессией, авторизацией, отправкой GraphQL-запросов и обработкой ошибок.

Внутренние методы:
- `_request(query, variables)` — отправляет GraphQL-запрос через `requests.Session.post()`
- `_check_error(result, operation_name)` — проверяет ответ на ошибки, бросает `YTMError`

Эндпоинт: `https://metrika.yandex.ru/api/metrika` (POST, JSON)

Формат запроса:
```json
{
  "query": "mutation createYtmTag($containerId: String!, $tag: YtmTagInput!) { ... }",
  "variables": { "containerId": "70978", "tag": { ... } }
}
```

Авторизация передаётся через заголовки:
- `x-csrf-token` — CSRF-токен
- `x-uid` — ID пользователя Яндекса
- `Cookie: Session_id=...` — сессионная cookie

### models.py — Модели данных

Dataclass-модели с фабричным методом `from_dict()` и сериализацией `to_dict()`:

| Модель | Описание |
|--------|----------|
| `Tag` | Тег контейнера (tag_id, name, type, status, trigger_ids, parameters) |
| `Trigger` | Триггер (trigger_id, name, type, activation_conditions, parameters) |
| `Template` | Шаблон тега/триггера/переменной |
| `Variable` | Встроенная переменная (variable_id, name, category) |
| `TemplateParameter` | Параметр шаблона (type, parameter_id, value) |
| `ActivationCondition` | Условие активации триггера (operator, variable_id, target_value) |
| `DateTime` | Обёртка над датой из API |
| `ContainerExport` | Экспорт контейнера (теги, триггеры, переменные) |
| `ExportedTag` / `ExportedTrigger` / `ExportedVariable` | Сущности для экспорта |

Классы-константы:

| Класс | Описание | Пример значения |
|-------|----------|-----------------|
| `TriggerTemplates` | ID шаблонов триггеров | `PAGE_VIEW = "page_view"`, `CUSTOM_EVENT = "custom_event"` |
| `TagTemplates` | ID шаблонов тегов | `CUSTOM_HTML = "chtml"`, `YANDEX_METRIKA = "149"` |
| `VariableTemplates` | ID шаблонов переменных | `JS_VARIABLE = "js_variable"`, `DATA_LAYER = "datalayer"` |
| `ConditionOperators` | Операторы для условий | `EQUALS = "equals"`, `CONTAINS = "contains"` |
| `BuiltInVariables` | Встроенные переменные | `CLICK_URL = "click_url"`, `PAGE_URL = "page_url"` |

### queries.py — GraphQL-запросы

Запросы построены из переиспользуемых фрагментов:
- `FRAGMENT_API_ERROR` — обработка ошибок
- `FRAGMENT_DATE_TIME` — дата и время
- `FRAGMENT_TEMPLATE_PARAMETER` — параметры шаблонов (включая таблицы)
- `FRAGMENT_TRIGGER_CONDITION` — условия активации

Основные запросы:

| Запрос | Тип | GraphQL операция |
|--------|-----|------------------|
| `QUERY_TAGS_LIST` | query | `ytmTags2` |
| `MUTATION_CREATE_TAG` | mutation | `createYtmTag` |
| `MUTATION_EDIT_TAG` | mutation | `editYtmTag` |
| `MUTATION_DELETE_TAG` | mutation | `deleteYtmTag` |
| `QUERY_TRIGGERS_LIST` | query | `ytmTriggers2` |
| `MUTATION_CREATE_TRIGGER` | mutation | `createYtmTrigger` |
| `MUTATION_DELETE_TRIGGER` | mutation | `deleteYtmTrigger` |
| `QUERY_AVAILABLE_TEMPLATES` | query | `ytmAvailableTemplates` |
| `MUTATION_CREATE_TEMPLATE` | mutation | `createYtmTemplate` |
| `MUTATION_PUBLISH_TEMPLATE` | mutation | `publishYtmTemplate` |
| `MUTATION_EDIT_TEMPLATE` | mutation | `editYtmTemplate` |
| `QUERY_VARIABLES_SUGGEST` | query | `ytmVariablesSuggest` |
| `QUERY_CUSTOM_VARIABLES_LIST` | query | `ytmVariables2` |
| `MUTATION_CREATE_VARIABLE` | mutation | `createYtmVariable` |
| `MUTATION_DELETE_VARIABLE` | mutation | `deleteYtmVariable` |
| `QUERY_VERSION_CHANGELOG` | query | `ytmContainerVersionChangelog` |
| `MUTATION_PUBLISH_VERSION` | mutation | `publishYtmVersion` |
| `QUERY_LATEST_VERSION` | query | `ytmLatestContainerVersion` |

---

## Примеры использования

### Базовое использование

```python
from ytm_api import YandexTagManagerAPI
from ytm_api.models import TriggerTemplates, TagTemplates, ActivationCondition

api = YandexTagManagerAPI(
    session_id="...",
    csrf_token="...",
    uid="...",
)

CONTAINER_ID = "70978"

# Получить теги и триггеры
tags = api.get_tags(CONTAINER_ID)
triggers = api.get_triggers(CONTAINER_ID)

# Создать триггер
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="All Pages",
    template_id=TriggerTemplates.PAGE_VIEW,
)

# Создать Custom HTML тег
tag = api.create_tag(
    container_id=CONTAINER_ID,
    name="My Tag",
    template_id=TagTemplates.CUSTOM_HTML,
    html_code="<script>console.log('hello');</script>",
    trigger_ids=[trigger.trigger_id],
)

# Опубликовать
api.publish(CONTAINER_ID, name="v1.0")
```

### Создание триггера с условиями

```python
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="Download Click",
    template_id=TriggerTemplates.CLICK_LINKS,
    activation_conditions=[
        ActivationCondition(
            operator="contains",
            is_not=False,
            variable_id="click_url",
            target_value="download",
        ),
    ],
)
```

### Кастомные переменные (встроенные шаблоны)

```python
# JavaScript Variable — читает window.userEmail
api.create_js_variable(CONTAINER_ID, "User Email", "userEmail")

# DataLayer Variable — читает dataLayer[i].ecommerce.purchase.revenue
api.create_data_layer_variable(CONTAINER_ID, "Revenue", "ecommerce.purchase.revenue")

# Cookie Variable
api.create_cookie_variable(CONTAINER_ID, "GA Client ID", "_ga")

# Константа
api.create_constant_variable(CONTAINER_ID, "API Key", "pk_live_xxx")

# DOM Element по CSS-селектору
api.create_dom_element_variable(CONTAINER_ID, "Page Title", "h1.title")

# URL Variable — только path
api.create_url_variable(CONTAINER_ID, "Page Path", "path")

# Lookup Table
api.create_lookup_table_variable(
    CONTAINER_ID,
    "Scroll Category",
    "{{ Scroll Depth Threshold }}",
    lookup_table=[("25", "shallow"), ("50", "medium"), ("75", "deep"), ("100", "complete")],
    default_value="unknown",
)
```

### Кастомные шаблоны переменных

Для галереи ЯТМ. Шаблон создаётся и публикуется один раз, затем на его основе создаются экземпляры переменных.

```python
# URL Query Parameter — извлекает отдельный GET-параметр
template = api.create_url_query_param_template(CONTAINER_ID)

# Создаём UTM-переменные
for param in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]:
    api.create_variable_from_template(
        CONTAINER_ID, template,
        name=f"UTM {param.replace('utm_', '').title()}",
        param_values={"paramName": param},
    )

# localStorage Variable — читает из localStorage
ls_template = api.create_local_storage_template(
    CONTAINER_ID,
    keys=["quiz_result", "cart_id"],
)
api.create_variable_from_template(
    CONTAINER_ID, ls_template,
    name="Quiz Result",
    param_values={"keyName": "quiz_result"},
)
```

### Persistent DataLayer переменные

ЯТМ (в отличие от GTM) не накапливает состояние dataLayer. Eventless пуши (`dataLayer.push({key: val})` без `event`) полностью игнорируются.

Два решения:

**Решение 1 — Persistent DL через templateStorage:**

```python
# Создать шаблон (один раз на контейнер)
template = api.create_persistent_dl_template(CONTAINER_ID)

# Создать переменные (каждая создаёт ПАРУ: обычная DL + persistent)
api.create_persistent_dl_variable(
    CONTAINER_ID, template,
    name="DL - userId (persistent)",
    key_name="userId",
)

# Массово
api.create_persistent_dl_variables(CONTAINER_ID, template, {
    "userId": "DL - userId (persistent)",
    "userType": "DL - userType (persistent)",
})
```

**Решение 2 — DL Interceptor через window._ytm_dl_cache:**

```python
# Установить перехватчик (один раз на контейнер)
tag, trigger = api.setup_dl_interceptor(CONTAINER_ID)

# Создать переменные
api.create_intercepted_dl_variables(CONTAINER_ID, {
    "userId": "DL - userId",
    "userType": "DL - userType",
})

api.publish(CONTAINER_ID)
```

### Экспорт и импорт контейнера

```python
# Экспорт
export = api.export_container("1080803", metrika_id="106472777")
export.save("backup.json")

# Импорт в другой контейнер
export = ContainerExport.load("backup.json")
tag_codes = {
    "YM Goal - form_submit": "<script>ym(NEW_ID, 'reachGoal', 'form_submit')</script>",
}
result = api.import_container("NEW_CONTAINER", export, tag_codes=tag_codes)
```

### Preview-режим

```python
# Получить preview-ссылку
url = api.preview(CONTAINER_ID, site_url="https://example.ru")
# "https://example.ru/?_ytm_preview=2788228429716318020"
```

---

## Ключевые особенности API ЯТМ (результаты reverse-engineering)

### 1. GraphQL API

Единый эндпоинт: `POST https://metrika.yandex.ru/api/metrika`

Тело запроса — стандартный GraphQL: `{ "query": "...", "variables": { ... } }`

### 2. Авторизация

Три обязательных заголовка:
- `x-csrf-token` — меняется каждую сессию
- `x-uid` — постоянный ID пользователя Яндекса
- `Cookie: Session_id=...` — сессионная cookie

Дополнительные заголовки для корректной работы:
- `Origin: https://metrika.yandex.ru`
- `Referer: https://metrika.yandex.ru/`
- `Content-Type: application/json`

### 3. Кастомные шаблоны — lifecycle

1. `createYtmTemplate` — создаёт **draft** шаблона
2. `publishYtmTemplate` — публикует draft, **меняет parameterId** параметров
3. После публикации шаблон можно использовать для создания экземпляров

**Критично:** `parameterId` параметров назначается сервером при создании и **меняется при публикации**. Финальные ID — только в ответе `publishYtmTemplate`.

### 4. templateVersion

В input-ах мутаций `templateVersion` нужно передавать **строкой**, не числом. При передаче int — 500 Internal Server Error.

### 5. enablingConditions

Поле `enablingConditions: []` **обязательно** для параметров шаблона, даже если пустое. Без него API возвращает ошибку.

### 6. Custom JavaScript Variables отсутствуют

В отличие от GTM, ЯТМ **не поддерживает** тип переменной Custom JavaScript (`custom_js`). Для произвольной JS-логики нужно создавать кастомный шаблон на sandboxed JS.

### 7. dataLayer не накапливает состояние

`dataLayer.push({key: val})` без ключа `event` **полностью игнорируется** ЯТМ. Значения из eventless-пушей не доступны через DL-переменные.

Два обходных пути реализованы в SDK:
- **Persistent DL через templateStorage** — кеширует значения на уровне шаблона
- **DL Interceptor** — перехватывает `push()` и кеширует в `window._ytm_dl_cache`

### 8. Container ID vs Metrika ID

Container ID — внутренний ID контейнера ЯТМ, отличается от ID счётчика Метрики. Виден в Payload запросов к API, а не в URL.

### 9. localStorage — permissions

Sandbox ЯТМ требует **явный список ключей** localStorage в permissions шаблона. Wildcard `*` не поддерживается.

```python
permissions = {
    "canAccessLocalStorage": [
        {"key": "my_key", "read": True, "write": False},
    ],
}
```

### 10. Sandbox API шаблонов

Кастомные шаблоны пишутся на sandboxed JS с доступом через `require()`:

```javascript
const getUrl = require('getUrl');                   // Компоненты URL
const getReferrerUrl = require('getReferrerUrl');    // Компоненты реферера
const localStorage = require('localStorage');       // localStorage (с permissions)
const getCookieValues = require('getCookieValues'); // Чтение cookie
const templateStorage = require('templateStorage'); // Persistent storage шаблона
const getTimestamp = require('getTimestamp');        // Unix timestamp
const JSON = require('JSON');                       // JSON.parse/stringify
const Math = require('Math');                       // Math functions
```

### 11. Типы параметров шаблонов

| Тип | Описание |
|-----|----------|
| `TextInput` | Текстовое поле (нужен `textInputConfiguration`) |
| `Checkbox` | Чекбокс |
| `DropDownMenu` | Выпадающий список (нужен `listConfiguration.items`) |
| `Code` | Редактор кода (используется для HTML-кода тегов) |
| `Table` | Таблица (для Lookup Table) |

### 12. Операторы условий

Для `ActivationCondition.operator`:
```
equals, contains, starts_with, ends_with, matches_regex,
less_than, greater_than, less_than_or_equals, greater_than_or_equals
```

### 13. Типы триггеров (template_id)

```
initialization, page_view, dom_ready, window_loaded,
click_all_elements, click_just_links, form_submission,
custom_event, timer, scroll_depth, element_visibility
```

### 14. API не возвращает код тегов

При экспорте контейнера API возвращает метаданные тегов (имя, шаблон, триггеры, параметры), но **не возвращает HTML-код** для тегов типа `chtml`. Код нужно хранить отдельно.

---

## Обработка ошибок

SDK бросает `YTMError` с полями `kind`, `message`, `location`:

```python
from ytm_api import YTMError

try:
    api.create_tag(...)
except YTMError as e:
    print(f"Ошибка [{e.kind}]: {e.message}")
```

---

## Файлы в архиве

```
ytm_api/
  __init__.py               # Публичный API пакета
  client.py                 # Класс YandexTagManagerAPI (все методы)
  models.py                 # Dataclass-модели и константы
  queries.py                # GraphQL запросы и мутации
examples/
  basic_usage.py            # Базовые CRUD-операции
  create_variable_templates.py  # Создание шаблонов для галереи
  export_import.py          # Экспорт/импорт контейнера
  generate_tag_codes.py     # Генерация кода тегов для нового счётчика
  setup_dinamika_goals.py   # Настройка целей (пример реального проекта)
config.example.py           # Шаблон конфигурации
requirements.txt            # Зависимости (requests)
README.md                   # Краткое описание и quick start
docs/DOCUMENTATION.md       # Эта документация
```

---

## Версия

SDK v0.1.0 — Python 3.10+, единственная зависимость `requests>=2.28.0`.
