# Yandex Tag Manager API (Unofficial)

Неофициальный Python SDK для программного управления Яндекс Тег Менеджером.

## Возможности

- ✅ Получение списка тегов и триггеров
- ✅ Создание, редактирование, удаление тегов
- ✅ Создание, удаление триггеров
- ✅ Публикация контейнера
- ✅ Получение списка шаблонов и переменных

## Установка

```bash
pip install requests
```

## Получение данных авторизации

1. Открой https://metrika.yandex.ru → Тег Менеджер
2. Открой DevTools (F12) → Network
3. Найди любой запрос к `api/metrika`
4. Скопируй из запроса:
   - **Session_id** — из Cookies
   - **x-csrf-token** — из Headers
   - **x-uid** — из Headers
5. **Container ID** — из URL страницы: `/ytm/overview?id=XXXXX`

## Быстрый старт

```python
from ytm_api import YandexTagManagerAPI

# Инициализация
api = YandexTagManagerAPI(
    session_id="3:1769918318...",
    csrf_token="8980da54d11975764818941ad58f1588",
    uid="1153393446",
)

container_id = "70978"

# Получить список тегов
tags = api.get_tags(container_id)
for tag in tags:
    print(f"{tag.name} - {tag.status}")

# Создать HTML тег
tag = api.create_tag(
    container_id=container_id,
    name="My Tag",
    html_code="<script>console.log('test');</script>",
    trigger_ids=["26125"],  # ID триггера
)
print(f"Создан тег: {tag.tag_id}")

# Создать триггер
trigger = api.create_trigger(
    container_id=container_id,
    name="All Pages",
    template_id="page_view",
)
print(f"Создан триггер: {trigger.trigger_id}")

# Опубликовать изменения
api.publish(container_id, name="v1.0", description="Initial release")
```

## API Reference

### YandexTagManagerAPI

#### Конструктор

```python
YandexTagManagerAPI(
    session_id: str,     # Cookie Session_id
    csrf_token: str,     # Header x-csrf-token
    uid: str,            # Header x-uid
    lang: str = "ru",    # Язык (ru/en)
)
```

### Теги

```python
# Список тегов
api.get_tags(container_id, offset=0, limit=50, search="", ids=None) -> list[Tag]

# Создать тег
api.create_tag(
    container_id,
    name,
    template_id="chtml",     # "chtml" для Custom HTML
    html_code=None,          # HTML код (для chtml)
    trigger_ids=None,        # Список ID триггеров
    tag_priority=0,
    parameters=None,         # Параметры шаблона
) -> Tag

# Обновить тег
api.update_tag(
    container_id,
    tag_id,
    name=None,
    html_code=None,
    trigger_ids=None,
    tag_priority=None,
    template_id="chtml",
    parameters=None,
) -> Tag

# Удалить тег
api.delete_tag(container_id, tag_id) -> bool
```

### Триггеры

```python
# Список триггеров
api.get_triggers(container_id, offset=0, limit=50, search="", ids=None) -> list[Trigger]

# Создать триггер
api.create_trigger(
    container_id,
    name,
    template_id="page_view",    # Тип триггера
    tag_ids=None,               # Связанные теги
    activation_conditions=None, # Условия активации
    parameters=None,
) -> Trigger

# Удалить триггер
api.delete_trigger(container_id, trigger_id) -> bool
```

### Шаблоны триггеров

```python
from ytm_api import TriggerTemplates

api.create_trigger(
    container_id=CONTAINER_ID,
    name="My Trigger",
    template_id=TriggerTemplates.PAGE_VIEW,
)
```

| Константа | template_id | Описание |
|-----------|-------------|----------|
| `INITIALIZATION` | `initialization` | Инициализация (самый ранний) |
| `PAGE_VIEW` | `page_view` | Просмотр страницы |
| `DOM_READY` | `dom_ready` | Модель DOM готова |
| `WINDOW_LOADED` | `window_loaded` | Окно загружено |
| `CLICK_ALL` | `click_all_elements` | Клики - все элементы |
| `CLICK_LINKS` | `click_just_links` | Клики - только ссылки |
| `FORM_SUBMIT` | `form_submission` | Отправка формы |
| `CUSTOM_EVENT` | `custom_event` | Специальное событие |
| `TIMER` | `timer` | Таймер |
| `SCROLL_DEPTH` | `scroll_depth` | Глубина прокрутки |
| `ELEMENT_VISIBILITY` | `element_visibility` | Видимость элемента |

### Шаблоны тегов

```python
from ytm_api import TagTemplates

api.create_tag(
    container_id=CONTAINER_ID,
    name="My Tag",
    template_id=TagTemplates.CUSTOM_HTML,
    html_code="<script>...</script>",
)
```

| Константа | template_id | Описание |
|-----------|-------------|----------|
| `CUSTOM_HTML` | `chtml` | Пользовательский HTML |
| `YANDEX_METRIKA` | `149` | Яндекс Метрика |
| `ECOMMERCE` | `1338` | Отправка ecommerce-событий |
| `DEBUGGER` | `178` | Мини дебагер триггеров |

### Шаблоны переменных

```python
from ytm_api import VariableTemplates, TemplateParameter

api.create_variable(
    container_id=CONTAINER_ID,
    name="My Variable",
    template_id=VariableTemplates.JS_VARIABLE,
    parameters=[
        TemplateParameter(type="TextInput", parameter_id="1", value="myGlobalVar")
    ],
)
```

| Константа | template_id | Описание |
|-----------|-------------|----------|
| `JS_VARIABLE` | `js_variable` | Переменная JavaScript (window.xxx) |
| `DATA_LAYER` | `datalayer` | Переменная уровня данных |
| `CONSTANT` | `constant` | Константа |
| `URL` | `url` | Адрес страницы |
| `REFERRER` | `referrer` | URL перехода HTTP |
| `DOM_ELEMENT` | `element_dom` | Элемент DOM |
| `COOKIE` | `first_party_cookie` | Собственный файл cookie |
| `RANDOM_NUMBER` | `random_number` | Случайное число |
| `LOOKUP_TABLE` | `match_table` | Таблица поиска |

### Кастомные переменные

```python
# Список кастомных переменных
api.get_custom_variables(container_id) -> list[dict]

# Создать переменную (базовый метод)
api.create_variable(container_id, name, template_id, parameters) -> dict

# Удалить переменную
api.delete_variable(container_id, variable_id) -> bool

# --- Хелперы для создания переменных ---

# JavaScript Variable (window.xxx)
api.create_js_variable(container_id, name, js_variable_name) -> dict

# Data Layer Variable (dataLayer)
api.create_data_layer_variable(container_id, name, data_layer_key) -> dict

# Cookie Variable
api.create_cookie_variable(container_id, name, cookie_name, url_decode=True) -> dict

# Константа
api.create_constant_variable(container_id, name, value) -> dict

# DOM Element Variable
api.create_dom_element_variable(container_id, name, selector, attribute="", selection_method="css") -> dict

# URL Variable (компоненты текущего URL)
api.create_url_variable(container_id, name, component="full") -> dict
# component: "full", "protocol", "host", "port", "path", "extension", "query", "fragment"

# Referrer Variable (компоненты URL перехода)
api.create_referrer_variable(container_id, name, component="full") -> dict
# component: "full", "protocol", "host", "port", "path", "extension", "query", "fragment"

# Random Number (случайное число)
api.create_random_number_variable(container_id, name) -> dict

# Lookup Table (таблица поиска)
api.create_lookup_table_variable(
    container_id, name,
    input_variable="{{ Page Path }}",  # Входная переменная
    lookup_table=[("/", "home"), ("/cart", "cart")],  # Маппинг
    default_value="other",  # Значение по умолчанию
) -> dict
```

### Шаблоны и переменные

```python
# Список шаблонов
api.get_templates(
    container_id,
    template_type="Tag",    # "Tag", "Trigger", "Variable"
    sources=None,           # ["Yandex", "Personal", "Saved"]
    offset=0,
    limit=100,
    search="",
) -> list[Template]

# Список переменных для подстановки
api.get_variables(container_id) -> list[Variable]
```

### Публикация

```python
# Changelog перед публикацией
api.get_changelog(container_id, version1=None, version2=None) -> dict

# Публикация
api.publish(
    container_id,
    name="",           # Название версии
    description="",    # Описание
    is_preview=False,  # Preview режим
) -> bool
```

### Вспомогательные методы

```python
# Создать тег с новым триггером одним вызовом
tag, trigger = api.create_html_tag_with_trigger(
    container_id,
    tag_name="My Tag",
    html_code="<script>...</script>",
    trigger_name="All Pages",
    trigger_template="page_view",
)
```

## Создание триггера с условиями

```python
from ytm_api import ActivationCondition, ConditionOperators, BuiltInVariables, TriggerTemplates

# Триггер: клик по ссылке, содержащей "download"
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="Download Link Click",
    template_id=TriggerTemplates.CLICK_LINKS,
    activation_conditions=[
        ActivationCondition(
            operator=ConditionOperators.CONTAINS,
            is_not=False,
            variable_id=BuiltInVariables.CLICK_URL,
            target_value="download",
        ),
    ],
)
```

## Операторы условий

```python
from ytm_api import ConditionOperators
```

| Константа | Значение | Описание |
|-----------|----------|----------|
| `EQUALS` | `equals` | Равно |
| `CONTAINS` | `contains` | Содержит |
| `STARTS_WITH` | `starts_with` | Начинается с |
| `ENDS_WITH` | `ends_with` | Заканчивается на |
| `MATCHES_REGEX` | `matches_regex` | Регулярное выражение |
| `LESS_THAN` | `less_than` | Меньше |
| `GREATER_THAN` | `greater_than` | Больше |

## Встроенные переменные

```python
from ytm_api import BuiltInVariables
```

### Клики
| Константа | variable_id | Описание |
|-----------|-------------|----------|
| `CLICK_ELEMENT` | `click_element` | DOM элемент |
| `CLICK_CLASSES` | `click_classes` | CSS классы |
| `CLICK_ID` | `click_id` | ID элемента |
| `CLICK_URL` | `click_url` | URL ссылки |
| `CLICK_TEXT` | `click_text` | Текст элемента |

### Формы
| Константа | variable_id | Описание |
|-----------|-------------|----------|
| `FORM_ELEMENT` | `form_element` | DOM элемент формы |
| `FORM_ID` | `form_id` | ID формы |
| `FORM_URL` | `form_url` | URL action формы |

### Страница
| Константа | variable_id | Описание |
|-----------|-------------|----------|
| `PAGE_URL` | `page_url` | Полный URL |
| `PAGE_PATH` | `page_path` | Путь (/about) |
| `PAGE_HOSTNAME` | `page_hostname` | Домен |
| `REFERRER` | `referrer` | Откуда пришёл |

### Другие
| Константа | variable_id | Описание |
|-----------|-------------|----------|
| `EVENT` | `event` | Событие из dataLayer |
| `SCROLL_DEPTH_THRESHOLD` | `scroll_depth_threshold` | % прокрутки |
| `RANDOM_NUMBER` | `random_number` | Случайное число |

Полный список: `api.get_variables(container_id)`

## Ограничения

- ⚠️ **Неофициальный API** — Яндекс может изменить его без предупреждения
- ⚠️ **Session-based auth** — сессия истекает, нужно обновлять credentials
- ⚠️ **Rate limits** — возможны ограничения при частых запросах

## Troubleshooting

### Ошибка авторизации
```
YTMError: [Unauthorized] ...
```
→ Обнови Session_id, csrf_token и uid из DevTools

### Тег не появляется на сайте
→ Не забудь вызвать `api.publish()` после создания/изменения тегов

### Container not found
→ Проверь правильность container_id (из URL страницы YTM)

## Лицензия

MIT
