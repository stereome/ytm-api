# Yandex Tag Manager API (Unofficial)

Неофициальный Python SDK для программного управления Яндекс Тег Менеджером.

## Возможности

- ✅ Получение списка тегов и триггеров
- ✅ Создание, редактирование, удаление тегов
- ✅ Создание, удаление триггеров
- ✅ Публикация контейнера
- ✅ Получение списка шаблонов и переменных
- ✅ **Кастомные шаблоны** — создание, публикация, редактирование пользовательских шаблонов
- ✅ **Persistent DataLayer переменные** — кэширование значений dataLayer через templateStorage
- ✅ **Экспорт/Импорт контейнера** — бэкап и миграция между счётчиками

## Установка

```bash
pip install requests
```

## Получение данных авторизации

1. Открой https://metrika.yandex.ru → Тег Менеджер для нужного счётчика
2. Открой DevTools (F12) → вкладка **Network**
3. Обнови страницу и найди любой запрос к `api/metrika`
4. Кликни на запрос → вкладка **Headers**
5. Скопируй из **Request Headers**:
   - **x-csrf-token**
   - **x-uid**
6. Скопируй из **Cookies** (или вкладка Cookies):
   - **Session_id** — длинная строка вида `3:1769918318...`

### Важно: Container ID ≠ ID счётчика Метрики

**Container ID** для YTM API — это **НЕ** номер счётчика Яндекс Метрики!

Чтобы найти правильный Container ID:
1. Открой ЯТМ для нужного счётчика
2. В DevTools → Network найди запрос к `api/metrika`
3. Посмотри в **Payload** или **Request Body** параметр `containerId`

Например:
- ID счётчика Метрики: `106472777` (виден в URL)
- Container ID для YTM API: `1080803` (виден в теле запроса)

```python
# Правильно — используй Container ID из запроса
api.get_tags("1080803")

# Неправильно — ID счётчика метрики вернёт FORBIDDEN
api.get_tags("106472777")
```

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
from ytm_api import ActivationCondition, ConditionOperators, BuiltInVariables, TriggerTemplates, TemplateParameter

# Триггер: клик по ссылке, содержащей "download"
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="Download Link Click",
    template_id=TriggerTemplates.CLICK_LINKS,
    activation_conditions=[
        ActivationCondition(
            operator=ConditionOperators.CONTAINS,  # ВАЖНО: с большой буквы!
            is_not=False,
            variable_id=BuiltInVariables.CLICK_URL,
            target_value="download",
        ),
    ],
)

# Триггер: клик по элементу с data-goal атрибутом
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="Click - CTA Button",
    template_id="click_just_links",
    activation_conditions=[
        ActivationCondition(
            operator="Contains",
            is_not=False,
            variable_id="click_element",
            target_value="click_cta_header",  # значение data-goal
        ),
    ],
)

# Триггер: dataLayer событие (custom_event)
trigger = api.create_trigger(
    container_id=CONTAINER_ID,
    name="DataLayer - form_focus",
    template_id="custom_event",
    parameters=[
        TemplateParameter(type="TextInput", parameter_id="1", value="form_focus")
    ],
)
```

> ⚠️ **Важно:** Операторы условий должны быть с большой буквы: `"Contains"`, `"Equals"`, `"StartsWith"` и т.д.

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

## Кастомные шаблоны

SDK поддерживает создание, публикацию и редактирование пользовательских шаблонов (тегов, триггеров, переменных).

```python
# Создать и автоматически опубликовать кастомный шаблон переменной
template = api.create_custom_template(
    container_id=CONTAINER_ID,
    name="My Custom Variable",
    template_type="Variable",
    sandbox_code="return data.myParam;",
    parameters=[{
        "parameterId": "0",
        "name": "myParam",
        "label": "My Parameter",
        "order": 0,
        "type": "TextInput",
        "isRequired": False,
        "enablingConditions": [],
        "textInputConfiguration": {"defaultValue": "", "placeholder": ""},
    }],
    permissions={"canAccessTemplateStorage": True},
)

# template["templateId"] — ID для создания экземпляров
# template["data"]["parameters"][0]["parameterId"] — финальный parameterId
```

> **Важно:** `parameterId` назначается сервером и **меняется при каждой публикации** шаблона. Всегда берите актуальный `parameterId` из ответа `create_custom_template()` или `publish_template()`.

```python
# Опубликовать шаблон отдельно (если создан с publish=False)
published = api.publish_template(container_id, template_id)

# Список шаблонов (включая пользовательские)
templates = api.get_templates(container_id, template_type="Variable", sources=["Personal"])
```

## Persistent DataLayer переменные

ЯТМ (в отличие от GTM) **не накапливает состояние dataLayer** — данные из одного пуша недоступны в последующих. SDK решает это через кастомный шаблон с `templateStorage`.

### Как это работает

Для каждого ключа создаётся **пара переменных**:
1. **Обычная DL-переменная** — ловит значение из текущего пуша
2. **Persistent-переменная** (кастомный шаблон) — читает DL-переменную и кэширует в `templateStorage`

```python
# 1. Создать шаблон (один раз на контейнер)
template = api.create_persistent_dl_template(CONTAINER_ID)

# 2. Создать переменные (каждый вызов создаёт 2 переменные: DL + persistent)
api.create_persistent_dl_variable(
    CONTAINER_ID, template, "DL - userId (persistent)", "userId",
)
# Создаст: "DL - userId" (обычная) + "DL - userId (persistent)" (с кэшем)

# Или массово:
api.create_persistent_dl_variables(
    CONTAINER_ID,
    template,
    {
        "userId": "DL - userId (persistent)",
        "userType": "DL - userType (persistent)",
        "clientId": "DL - clientId (persistent)",
    },
)

# 3. Опубликовать контейнер
api.publish(CONTAINER_ID, name="Add persistent DL variables")
```

### Сценарий использования

```js
// Пуш 1: userId вместе с event → переменная ловит и кэширует
dataLayer.push({userId: 'user_42', event: 'login'});

// Пуш 2: другой event БЕЗ userId → persistent-переменная возвращает из кэша
dataLayer.push({event: 'page_view'});
// {{DL - userId (persistent)}} === 'user_42' ✅
```

> **Ограничение:** значение должно быть отправлено хотя бы раз **вместе с event**. Eventless-пуши (`dataLayer.push({userId: 'x'})` без ключа `event`) ЯТМ полностью игнорирует. Для перехвата eventless-пушей используйте DL Interceptor (ниже).

## DL Interceptor (перехват eventless-пушей)

ЯТМ полностью игнорирует `dataLayer.push()` без ключа `event`. DL Interceptor решает это через monkey-patch `dataLayer.push` — перехватывает **все** пуши и кэширует в `window._ytm_dl_cache`.

```python
# 1. Установить перехватчик (один раз на контейнер)
tag, trigger = api.setup_dl_interceptor(CONTAINER_ID)

# 2. Создать переменные для нужных ключей
api.create_intercepted_dl_variable(CONTAINER_ID, "DL - userId", "userId")

# Или массово:
api.create_intercepted_dl_variables(
    CONTAINER_ID,
    {
        "userId": "DL - userId",
        "userType": "DL - userType",
        "clientId": "DL - clientId",
    },
)

# 3. Опубликовать
api.publish(CONTAINER_ID)
```

### Сценарий

```js
// Eventless-пуш — ЯТМ игнорирует, но перехватчик ловит
dataLayer.push({userId: 'user_42'});

// Любое событие — переменная доступна
dataLayer.push({event: 'page_view'});
// {{DL - userId}} === 'user_42' ✅
```

### Как работает

1. Тег на `Initialization` (самый ранний триггер) — сканирует существующие записи в `dataLayer` и перехватывает будущие пуши
2. Все значения (кроме `event`) кэшируются в `window._ytm_dl_cache`
3. Переменные типа `js_variable` читают `window._ytm_dl_cache.keyName`

## Экспорт и импорт контейнера

Позволяет сохранить все теги, триггеры и переменные в JSON и восстановить в другом контейнере.

### Экспорт

```python
from ytm_api import YandexTagManagerAPI, ContainerExport

api = YandexTagManagerAPI(session_id=..., csrf_token=..., uid=...)

# Экспортировать контейнер
export = api.export_container(
    container_id="1080803",
    metrika_id="106472777",  # опционально, для информации
)

# Сохранить в файл
export.save("backup.json")

print(f"Экспортировано: {len(export.tags)} тегов, {len(export.triggers)} триггеров")
```

### Импорт

```python
from ytm_api import ContainerExport

# Загрузить из файла
export = ContainerExport.load("backup.json")

# ВАЖНО: API Яндекса не возвращает код тегов!
# Для chtml тегов нужно передать код отдельно:
tag_codes = {
    "YM Goal - form_submit": "<script>ym(123, 'reachGoal', 'form_submit')</script>",
    "YM Goal - click_email": "<script>ym(123, 'reachGoal', 'click_email')</script>",
}

# Импортировать в новый контейнер
result = api.import_container(
    container_id="NEW_CONTAINER_ID",
    export=export,
    skip_existing=True,  # пропускать если уже есть
    tag_codes=tag_codes,  # код для chtml тегов
)

print(f"Создано тегов: {len(result['tags_created'])}")
print(f"Создано триггеров: {len(result['triggers_created'])}")
if result["errors"]:
    print(f"Ошибки: {result['errors']}")

# Опубликовать изменения
api.publish("NEW_CONTAINER_ID", name="Imported from backup")
```

### Формат экспорта

```json
{
  "container_id": "1080803",
  "metrika_id": "106472777",
  "export_date": "2026-02-01T17:23:36.477788",
  "tags": [
    {
      "name": "YM Goal - form_submit",
      "templateId": "chtml",
      "triggerNames": ["DataLayer - form_submit"],
      "status": "Active"
    }
  ],
  "triggers": [
    {
      "name": "DataLayer - form_submit",
      "templateId": "custom_event",
      "activationConditions": [],
      "parameters": [{"type": "TextInput", "parameterId": "1", "value": "form_submit"}]
    }
  ],
  "variables": []
}
```

> ⚠️ **Ограничение list-эндпоинта:** стандартный `get_tags()` и `export_container()` НЕ возвращают `html_code` (поле `parameters` отсутствует в `YtmTag` GraphQL-схеме для list).
>
> **Workaround:** используйте `get_tags_with_code()` или `get_container_snapshot()` (см. раздел «Чтение тегов с кодом» выше) — они идут через `ytmContainerVersionChangelog`, который возвращает `YtmTagDetailed` с parameters. Для бэкапа: соберите `tag_codes` через `get_tags_with_code()` перед `export_container()`.

## Чтение тегов с кодом и диагностика контейнера

Стандартный `get_tags()` возвращает только метаданные — поле `parameters` (где лежит код) **отсутствует** в GraphQL-схеме `YtmTag` для list-эндпоинта. Чтобы получить полный код тегов, используйте методы через `ytmContainerVersionChangelog` (который возвращает `YtmTagDetailed` с parameters):

```python
# Полный код тегов (включая html_code)
tags = api.get_tags_with_code(container_id)
for t in tags:
    if t.html_code:
        print(t.name, '→', t.html_code[:80])

# Полные параметры триггеров (нужно для диагностики custom_event на dataLayer)
triggers = api.get_triggers_with_params(container_id)

# Snapshot всего контейнера за один запрос (теги + триггеры + переменные с parameters)
snap = api.get_container_snapshot(container_id)
print(f"Version {snap['version']}: {len(snap['tags'])} tags, {len(snap['triggers'])} triggers")

# Прочитать историческую версию
snap_old = api.get_container_snapshot(container_id, version=12)
```

### Удобный property `Tag.html_code`

```python
tag.html_code  # вернёт значение parameter type='Code' parameterId='0'
               # либо None, если тег не chtml или получен через get_tags() без кода
```

### Диагностика «зомби-триггеров»

Частая проблема: тег создан и привязан к триггеру, потом триггер удалён или потерял published-статус — тег остаётся active, но никогда не срабатывает. SDK умеет находить такие случаи одной командой:

```python
zombies = api.find_zombie_trigger_refs(container_id)
for z in zombies:
    print(f"❌ {z['tag_name']} → triggers {z['missing_trigger_ids']} missing")

# Анализ по версиям (где случилась поломка):
for v in range(10, 15):
    snap = api.get_container_snapshot(container_id, version=v)
    zombies = api.find_zombie_trigger_refs(container_id, version=v)
    print(f"v{v} «{snap['name']}»: {len(zombies)}/{len(snap['tags'])} zombies")
```

Реальный кейс: контейнер NLMK после bulk-import операции потерял связь tag→trigger у 121 из 125 тегов. Дашборды Метрики показывали поломку аналитики, корневая причина была обнаружена этим методом за 5 минут.

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
