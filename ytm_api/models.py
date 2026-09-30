"""
Модели данных для Yandex Tag Manager API
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime


@dataclass
class DateTime:
    """Дата и время из API"""
    day: int
    month: int
    year: int
    hours: Optional[int] = None
    minutes: Optional[int] = None
    seconds: Optional[int] = None

    def to_datetime(self) -> datetime:
        return datetime(
            year=self.year,
            month=self.month,
            day=self.day,
            hour=self.hours or 0,
            minute=self.minutes or 0,
            second=self.seconds or 0
        )

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional["DateTime"]:
        if not data:
            return None
        return cls(
            day=data.get("day", 1),
            month=data.get("month", 1),
            year=data.get("year", 2025),
            hours=data.get("hours"),
            minutes=data.get("minutes"),
            seconds=data.get("seconds"),
        )


@dataclass
class TemplateParameter:
    """Параметр шаблона тега/триггера"""
    type: str  # "Code", "String", "Boolean", etc.
    parameter_id: str
    value: str
    raw_value: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "parameterId": self.parameter_id,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateParameter":
        return cls(
            type=data.get("type", ""),
            parameter_id=data.get("parameterId", ""),
            value=data.get("value", ""),
            raw_value=data.get("rawValue"),
        )


@dataclass
class TemplateData:
    """Данные шаблона для создания тега/триггера"""
    template_id: str
    parameters: list[TemplateParameter] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "templateId": self.template_id,
            "parameters": [p.to_dict() for p in self.parameters],
        }


@dataclass
class ActivationCondition:
    """Условие активации триггера"""
    operator: str  # "equals", "contains", "regex", etc.
    is_not: bool
    variable_id: str
    target_value: str

    def to_dict(self) -> dict:
        return {
            "operator": self.operator,
            "isNot": self.is_not,
            "variableId": self.variable_id,
            "targetValue": self.target_value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActivationCondition":
        return cls(
            operator=data.get("operator", ""),
            is_not=data.get("isNot", False),
            variable_id=data.get("variableId", ""),
            target_value=data.get("targetValue", ""),
        )


@dataclass
class Tag:
    """Тег Яндекс Тег Менеджера"""
    tag_id: str
    name: str
    type: str
    status: str
    template_id: str
    template_version: Optional[str] = None
    trigger_ids: list[str] = field(default_factory=list)
    parameters: list[TemplateParameter] = field(default_factory=list)
    created: Optional[DateTime] = None
    updated: Optional[DateTime] = None
    updated_by: Optional[str] = None
    original_tag_id: Optional[str] = None
    tag_priority: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Tag":
        return cls(
            tag_id=data.get("tagId", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            status=data.get("status", ""),
            template_id=data.get("templateId", ""),
            template_version=data.get("templateVersion"),
            trigger_ids=data.get("triggerIds", []),
            parameters=[
                TemplateParameter.from_dict(p)
                for p in data.get("parameters", [])
            ],
            created=DateTime.from_dict(data.get("created")),
            updated=DateTime.from_dict(data.get("updated")),
            updated_by=data.get("updatedBy"),
            original_tag_id=data.get("originalTagId"),
        )

    @property
    def html_code(self) -> Optional[str]:
        """
        HTML/JS код для chtml-тегов.
        Заполнен только если тег получен через get_tags_with_code() или из changelog.
        Стандартный get_tags() не возвращает parameters → html_code будет None.
        """
        for p in self.parameters:
            if p.type == "Code" and p.parameter_id == "0":
                return p.value
        return None


@dataclass
class Trigger:
    """Триггер Яндекс Тег Менеджера"""
    trigger_id: str
    name: str
    type: str
    status: str
    template_id: str
    template_version: Optional[str] = None
    tag_ids: list[str] = field(default_factory=list)
    activation_conditions: list[ActivationCondition] = field(default_factory=list)
    parameters: list[TemplateParameter] = field(default_factory=list)
    links_number: int = 0
    created: Optional[DateTime] = None
    updated: Optional[DateTime] = None
    updated_by: Optional[str] = None
    original_trigger_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Trigger":
        return cls(
            trigger_id=data.get("triggerId", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            status=data.get("status", ""),
            template_id=data.get("templateId", ""),
            template_version=data.get("templateVersion"),
            tag_ids=data.get("tagIds", []),
            activation_conditions=[
                ActivationCondition.from_dict(c)
                for c in data.get("activationConditions", [])
            ],
            parameters=[
                TemplateParameter.from_dict(p)
                for p in data.get("parameters", [])
            ],
            links_number=data.get("linksNumber", 0),
            created=DateTime.from_dict(data.get("created")),
            updated=DateTime.from_dict(data.get("updated")),
            updated_by=data.get("updatedBy"),
            original_trigger_id=data.get("originalTriggerId"),
        )


@dataclass
class Template:
    """Шаблон тега/триггера/переменной"""
    template_id: str
    name: str
    type: Literal["Tag", "Trigger", "Variable"]
    container_id: str
    definition_type: str  # "BuiltIn", "User"
    publicity: Optional[str] = None  # "Yandex", "Personal", "Saved"
    author: Optional[str] = None
    description: Optional[str] = None
    template_version: Optional[str] = None
    tag_template_type: Optional[str] = None  # "Chtml" для Custom HTML
    trigger_template_type: Optional[str] = None
    variable_template_type: Optional[str] = None
    documentation_link: Optional[str] = None
    status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        return cls(
            template_id=data.get("templateId", ""),
            name=data.get("name", ""),
            type=data.get("type", "Tag"),
            container_id=data.get("containerId", ""),
            definition_type=data.get("definitionType", ""),
            publicity=data.get("publicity"),
            author=data.get("author"),
            description=data.get("description"),
            template_version=data.get("templateVersion"),
            tag_template_type=data.get("tagTemplateType"),
            trigger_template_type=data.get("triggerTemplateType"),
            variable_template_type=data.get("variableTemplateType"),
            documentation_link=data.get("documentationLink"),
            status=data.get("status"),
        )


@dataclass
class Variable:
    """Встроенная переменная для использования в тегах"""
    variable_id: str
    name: str
    category: str
    original_variable_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Variable":
        return cls(
            variable_id=data.get("variableId", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            original_variable_id=data.get("originalVariableId"),
        )


# ============ ШАБЛОНЫ ТРИГГЕРОВ ============

class TriggerTemplates:
    """
    Шаблоны триггеров Яндекс Тег Менеджера.

    Использование:
        from ytm_api.models import TriggerTemplates

        api.create_trigger(
            container_id="70978",
            name="My Trigger",
            template_id=TriggerTemplates.PAGE_VIEW,
        )
    """
    # Загрузка страницы
    INITIALIZATION = "initialization"       # Инициализация (самый ранний)
    PAGE_VIEW = "page_view"                 # Просмотр страницы
    ALL_PAGES = "page_view"                 # Алиас для PAGE_VIEW
    DOM_READY = "dom_ready"                 # Модель DOM готова
    WINDOW_LOADED = "window_loaded"         # Окно загружено

    # Взаимодействия
    CLICK_ALL = "click_all_elements"        # Клики - все элементы
    CLICK_LINKS = "click_just_links"        # Клики - только ссылки
    FORM_SUBMIT = "form_submission"         # Отправка формы

    # Другие
    CUSTOM_EVENT = "custom_event"           # Специальное событие (dataLayer.push)
    TIMER = "timer"                         # Таймер
    SCROLL_DEPTH = "scroll_depth"           # Глубина прокрутки
    ELEMENT_VISIBILITY = "element_visibility"  # Видимость элемента


# ============ ШАБЛОНЫ ТЕГОВ ============

class TagTemplates:
    """
    Шаблоны тегов Яндекс Тег Менеджера.

    Использование:
        from ytm_api.models import TagTemplates

        api.create_tag(
            container_id="70978",
            name="My Tag",
            template_id=TagTemplates.CUSTOM_HTML,
            html_code="<script>...</script>",
        )
    """
    CUSTOM_HTML = "chtml"                   # Пользовательский HTML
    YANDEX_METRIKA = "149"                  # Яндекс Метрика
    ECOMMERCE = "1338"                      # Отправка ecommerce-событий
    DEBUGGER = "178"                        # Мини дебагер триггеров и переменных


# ============ ШАБЛОНЫ ПЕРЕМЕННЫХ ============

class VariableTemplates:
    """
    Шаблоны переменных Яндекс Тег Менеджера.

    Использование:
        from ytm_api.models import VariableTemplates, TemplateParameter

        api.create_variable(
            container_id="70978",
            name="My Variable",
            template_id=VariableTemplates.JS_VARIABLE,
            parameters=[
                TemplateParameter(type="TextInput", parameter_id="1", value="myGlobalVar")
            ],
        )
    """
    # Основные
    JS_VARIABLE = "js_variable"             # Переменная JavaScript (window.xxx)
    DATA_LAYER = "datalayer"                # Переменная уровня данных (dataLayer)
    CONSTANT = "constant"                   # Константа

    # Страница
    URL = "url"                             # Адрес страницы (path, host, query, etc.)
    REFERRER = "referrer"                   # URL перехода HTTP

    # DOM
    DOM_ELEMENT = "element_dom"             # Элемент DOM (по CSS селектору)

    # Другие
    COOKIE = "first_party_cookie"           # Собственный файл cookie
    RANDOM_NUMBER = "random_number"         # Случайное число
    LOOKUP_TABLE = "match_table"            # Таблица поиска (маппинг значений)


# ============ ОПЕРАТОРЫ ДЛЯ УСЛОВИЙ ТРИГГЕРОВ ============

class ConditionOperators:
    """
    Операторы для условий активации триггеров.

    Использование:
        from ytm_api.models import ConditionOperators, ActivationCondition

        condition = ActivationCondition(
            operator=ConditionOperators.CONTAINS,
            is_not=False,
            variable_id="click_url",
            target_value="download",
        )
    """
    EQUALS = "equals"                       # Равно
    CONTAINS = "contains"                   # Содержит
    STARTS_WITH = "starts_with"             # Начинается с
    ENDS_WITH = "ends_with"                 # Заканчивается на
    MATCHES_REGEX = "matches_regex"         # Соответствует регулярному выражению
    LESS_THAN = "less_than"                 # Меньше
    GREATER_THAN = "greater_than"           # Больше
    LESS_THAN_OR_EQUALS = "less_than_or_equals"      # Меньше или равно
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"  # Больше или равно


# ============ ВСТРОЕННЫЕ ПЕРЕМЕННЫЕ ============

class BuiltInVariables:
    """
    Встроенные переменные для использования в условиях триггеров.

    Эти переменные доступны без создания — просто используйте их ID.

    Использование в условиях:
        condition = ActivationCondition(
            operator="contains",
            is_not=False,
            variable_id=BuiltInVariables.CLICK_URL,
            target_value="download",
        )

    Использование в HTML тегах:
        html = f"<script>console.log('{{{{ {BuiltInVariables.PAGE_URL} }}}}')</script>"
    """
    # Клики
    CLICK_ELEMENT = "click_element"         # Click Element (DOM элемент)
    CLICK_CLASSES = "click_classes"         # Click Classes
    CLICK_ID = "click_id"                   # Click ID
    CLICK_TARGET = "click_target"           # Click Target
    CLICK_URL = "click_url"                 # Click URL
    CLICK_TEXT = "click_text"               # Click Text

    # Формы
    FORM_ELEMENT = "form_element"           # Form Element
    FORM_CLASSES = "form_classes"           # Form Classes
    FORM_ID = "form_id"                     # Form ID
    FORM_TARGET = "form_target"             # Form Target
    FORM_URL = "form_url"                   # Form URL

    # Страница
    PAGE_URL = "page_url"                   # Page URL
    PAGE_PATH = "page_path"                 # Page Path
    PAGE_HOSTNAME = "page_hostname"         # Page Hostname
    REFERRER = "referrer"                   # Referrer

    # Прокрутка
    SCROLL_DEPTH_THRESHOLD = "scroll_depth_threshold"  # Scroll Depth Threshold

    # Видимость
    PERCENT_VISIBLE = "percent_visible"     # Percent Visible
    ON_SCREEN_DURATION = "on_screen_duration"  # On Screen Duration

    # Утилиты
    EVENT = "event"                         # Event (из dataLayer)
    CONTAINER_VERSION = "container_version" # Container Version
    RANDOM_NUMBER = "random_number"         # Random Number


# ============ ЭКСПОРТ/ИМПОРТ КОНТЕЙНЕРА ============

@dataclass
class ExportedTag:
    """Тег для экспорта (без внутренних ID)"""
    name: str
    template_id: str
    trigger_names: list[str]  # Имена триггеров вместо ID
    status: str = "Active"
    tag_priority: int = 0
    # Код тега (для chtml) - должен быть заполнен вручную, т.к. API не возвращает
    html_code: Optional[str] = None
    parameters: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "templateId": self.template_id,
            "triggerNames": self.trigger_names,
            "status": self.status,
            "tagPriority": self.tag_priority,
            "htmlCode": self.html_code,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExportedTag":
        return cls(
            name=data.get("name", ""),
            template_id=data.get("templateId", ""),
            trigger_names=data.get("triggerNames", []),
            status=data.get("status", "Active"),
            tag_priority=data.get("tagPriority", 0),
            html_code=data.get("htmlCode"),
            parameters=data.get("parameters", []),
        )


@dataclass
class ExportedTrigger:
    """Триггер для экспорта"""
    name: str
    template_id: str
    activation_conditions: list[dict] = field(default_factory=list)
    parameters: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "templateId": self.template_id,
            "activationConditions": self.activation_conditions,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExportedTrigger":
        return cls(
            name=data.get("name", ""),
            template_id=data.get("templateId", ""),
            activation_conditions=data.get("activationConditions", []),
            parameters=data.get("parameters", []),
        )


@dataclass
class ExportedVariable:
    """Кастомная переменная для экспорта"""
    name: str
    template_id: str
    parameters: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "templateId": self.template_id,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExportedVariable":
        return cls(
            name=data.get("name", ""),
            template_id=data.get("templateId", ""),
            parameters=data.get("parameters", []),
        )


@dataclass
class ContainerExport:
    """
    Экспорт контейнера YTM.

    Содержит все теги, триггеры и переменные контейнера.
    Может быть сохранён в JSON и импортирован в другой контейнер.

    Ограничение: API Яндекса не возвращает код тегов (html_code),
    поэтому для полного бэкапа код нужно хранить отдельно.
    """
    container_id: str
    metrika_id: str
    export_date: str
    tags: list[ExportedTag] = field(default_factory=list)
    triggers: list[ExportedTrigger] = field(default_factory=list)
    variables: list[ExportedVariable] = field(default_factory=list)
    # Маппинг триггер ID → имя (для восстановления связей при импорте)
    trigger_id_to_name: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "container_id": self.container_id,
            "metrika_id": self.metrika_id,
            "export_date": self.export_date,
            "tags": [t.to_dict() for t in self.tags],
            "triggers": [t.to_dict() for t in self.triggers],
            "variables": [v.to_dict() for v in self.variables],
            "trigger_id_to_name": self.trigger_id_to_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContainerExport":
        return cls(
            container_id=data.get("container_id", ""),
            metrika_id=data.get("metrika_id", ""),
            export_date=data.get("export_date", ""),
            tags=[ExportedTag.from_dict(t) for t in data.get("tags", [])],
            triggers=[ExportedTrigger.from_dict(t) for t in data.get("triggers", [])],
            variables=[ExportedVariable.from_dict(v) for v in data.get("variables", [])],
            trigger_id_to_name=data.get("trigger_id_to_name", {}),
        )

    def to_json(self, indent: int = 2) -> str:
        """Сериализовать в JSON строку"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "ContainerExport":
        """Десериализовать из JSON строки"""
        import json
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        """Сохранить в файл"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "ContainerExport":
        """Загрузить из файла"""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())
