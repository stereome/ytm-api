"""
Основной клиент для Yandex Tag Manager API
"""

import requests
from typing import Literal, Optional

from .models import (
    Tag,
    Trigger,
    Template,
    Variable,
    TemplateData,
    TemplateParameter,
    ActivationCondition,
)
from . import queries


class YTMError(Exception):
    """Ошибка API Яндекс Тег Менеджера"""

    def __init__(self, kind: str, message: str, location: Optional[str] = None):
        self.kind = kind
        self.message = message
        self.location = location
        super().__init__(f"[{kind}] {message}")


class YandexTagManagerAPI:
    """
    Неофициальный клиент для Яндекс Тег Менеджера.

    Использует внутренний GraphQL API metrika.yandex.ru.

    Пример использования:
    ```python
    api = YandexTagManagerAPI(
        session_id="...",  # Cookie Session_id
        csrf_token="...",  # Header x-csrf-token
        uid="...",         # Header x-uid
    )

    # Получить список тегов
    tags = api.get_tags("70978")

    # Создать тег
    tag = api.create_tag(
        container_id="70978",
        name="Мой тег",
        template_id="chtml",
        html_code="<script>console.log('test');</script>",
        trigger_ids=["26125"],
    )

    # Опубликовать изменения
    api.publish("70978", name="v1.0")
    ```
    """

    BASE_URL = "https://metrika.yandex.ru/api/metrika"

    def __init__(
        self,
        session_id: str,
        csrf_token: str,
        uid: str,
        lang: str = "ru",
    ):
        """
        Инициализация клиента.

        Args:
            session_id: Cookie Session_id из браузера
            csrf_token: Header x-csrf-token из запросов
            uid: Header x-uid (ID пользователя Яндекса)
            lang: Язык интерфейса (ru/en)
        """
        self.session = requests.Session()

        # Cookies
        self.session.cookies.set("Session_id", session_id, domain=".yandex.ru")

        # Headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": "https://metrika.yandex.ru",
                "Referer": "https://metrika.yandex.ru/",
                "x-csrf-token": csrf_token,
                "x-uid": uid,
                "x-lang": lang,
            }
        )

    def _request(self, query: str, variables: dict) -> dict:
        """Выполнить GraphQL запрос"""
        response = self.session.post(
            self.BASE_URL,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()

        data = response.json()

        # Проверяем на ошибки GraphQL
        if "errors" in data:
            error = data["errors"][0]
            raise YTMError(
                kind="GraphQLError",
                message=error.get("message", "Unknown error"),
            )

        return data

    def _check_error(self, result: dict, operation_name: str) -> dict:
        """Проверить результат операции на ошибки"""
        if "data" not in result:
            raise YTMError(kind="NoData", message=f"No data in response for {operation_name}")

        operation_data = result["data"].get(operation_name, {})

        if operation_data.get("error"):
            error = operation_data["error"]
            reason = error.get("reason", [{}])[0] if error.get("reason") else {}
            raise YTMError(
                kind=reason.get("kind", error.get("kind", "Unknown")),
                message=reason.get("message", "Unknown error"),
                location=reason.get("location"),
            )

        return operation_data.get("data", operation_data)

    # ============ ТЕГИ ============

    def get_tags(
        self,
        container_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str = "",
        ids: Optional[list[str]] = None,
    ) -> list[Tag]:
        """
        Получить список тегов контейнера.

        Args:
            container_id: ID контейнера
            offset: Смещение для пагинации
            limit: Лимит записей
            search: Поисковый запрос
            ids: Фильтр по ID тегов
        """
        variables = {
            "containerId": container_id,
            "offset": offset,
            "limit": limit,
            "search": search,
        }
        if ids:
            variables["ids"] = ids

        result = self._request(queries.QUERY_TAGS_LIST, variables)
        data = self._check_error(result, "ytmTags2")

        return [Tag.from_dict(t) for t in data.get("tags", [])]

    def create_tag(
        self,
        container_id: str,
        name: str,
        template_id: str = "chtml",
        html_code: Optional[str] = None,
        trigger_ids: Optional[list[str]] = None,
        tag_priority: int = 0,
        parameters: Optional[list[TemplateParameter]] = None,
    ) -> Tag:
        """
        Создать новый тег.

        Args:
            container_id: ID контейнера
            name: Название тега
            template_id: ID шаблона (по умолчанию "chtml" - пользовательский HTML)
            html_code: HTML код (для шаблона chtml)
            trigger_ids: Список ID триггеров для активации
            tag_priority: Приоритет тега
            parameters: Параметры шаблона (если не chtml)

        Returns:
            Созданный тег
        """
        # Формируем параметры
        if parameters:
            params = [p.to_dict() for p in parameters]
        elif html_code and template_id == "chtml":
            params = [{"type": "Code", "parameterId": "0", "value": html_code}]
        else:
            params = []

        tag_input = {
            "name": name,
            "tagPriority": tag_priority,
            "triggerIds": trigger_ids or [],
            "templateData": {
                "templateId": template_id,
                "parameters": params,
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_TAG,
            {"containerId": container_id, "tag": tag_input},
        )
        data = self._check_error(result, "createYtmTag")

        return Tag.from_dict(data)

    def update_tag(
        self,
        container_id: str,
        tag_id: str,
        name: Optional[str] = None,
        html_code: Optional[str] = None,
        trigger_ids: Optional[list[str]] = None,
        tag_priority: Optional[int] = None,
        template_id: str = "chtml",
        parameters: Optional[list[TemplateParameter]] = None,
    ) -> Tag:
        """
        Обновить существующий тег.

        Args:
            container_id: ID контейнера
            tag_id: ID тега для обновления
            name: Новое название
            html_code: Новый HTML код
            trigger_ids: Новый список триггеров
            tag_priority: Новый приоритет
            template_id: ID шаблона
            parameters: Параметры шаблона
        """
        # Получаем текущий тег для заполнения недостающих полей
        current_tags = self.get_tags(container_id, ids=[tag_id])
        if not current_tags:
            raise YTMError(kind="NotFound", message=f"Tag {tag_id} not found")

        current = current_tags[0]

        # Формируем параметры
        if parameters:
            params = [p.to_dict() for p in parameters]
        elif html_code:
            params = [{"type": "Code", "parameterId": "0", "value": html_code}]
        else:
            params = [p.to_dict() for p in current.parameters]

        tag_input = {
            "name": name or current.name,
            "tagPriority": tag_priority if tag_priority is not None else current.tag_priority,
            "triggerIds": trigger_ids if trigger_ids is not None else current.trigger_ids,
            "templateData": {
                "templateId": template_id or current.template_id,
                "parameters": params,
            },
        }

        result = self._request(
            queries.MUTATION_EDIT_TAG,
            {"containerId": container_id, "tagId": tag_id, "tag": tag_input},
        )
        data = self._check_error(result, "editYtmTag")

        return Tag.from_dict(data)

    def delete_tag(self, container_id: str, tag_id: str) -> bool:
        """
        Удалить тег.

        Args:
            container_id: ID контейнера
            tag_id: ID тега

        Returns:
            True если успешно
        """
        result = self._request(
            queries.MUTATION_DELETE_TAG,
            {"containerId": container_id, "tagId": tag_id},
        )
        self._check_error(result, "deleteYtmTag")
        return True

    # ============ ТРИГГЕРЫ ============

    def get_triggers(
        self,
        container_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str = "",
        ids: Optional[list[str]] = None,
    ) -> list[Trigger]:
        """
        Получить список триггеров контейнера.

        Args:
            container_id: ID контейнера
            offset: Смещение для пагинации
            limit: Лимит записей
            search: Поисковый запрос
            ids: Фильтр по ID триггеров
        """
        variables = {
            "containerId": container_id,
            "offset": offset,
            "limit": limit,
            "search": search,
        }
        if ids:
            variables["ids"] = ids

        result = self._request(queries.QUERY_TRIGGERS_LIST, variables)
        data = self._check_error(result, "ytmTriggers2")

        return [Trigger.from_dict(t) for t in data.get("triggers", [])]

    def create_trigger(
        self,
        container_id: str,
        name: str,
        template_id: str = "page_view",
        tag_ids: Optional[list[str]] = None,
        activation_conditions: Optional[list[ActivationCondition]] = None,
        parameters: Optional[list[TemplateParameter]] = None,
    ) -> Trigger:
        """
        Создать новый триггер.

        Args:
            container_id: ID контейнера
            name: Название триггера
            template_id: ID шаблона триггера (page_view, click, form_submit, etc.)
            tag_ids: Список ID тегов для связи
            activation_conditions: Условия активации
            parameters: Параметры шаблона

        Returns:
            Созданный триггер
        """
        trigger_input = {
            "name": name,
            "tagIds": tag_ids or [],
            "activationConditions": [c.to_dict() for c in (activation_conditions or [])],
            "templateData": {
                "templateId": template_id,
                "parameters": [p.to_dict() for p in (parameters or [])],
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_TRIGGER,
            {"containerId": container_id, "trigger": trigger_input},
        )
        data = self._check_error(result, "createYtmTrigger")

        return Trigger.from_dict(data)

    def delete_trigger(self, container_id: str, trigger_id: str) -> bool:
        """
        Удалить триггер.

        Args:
            container_id: ID контейнера
            trigger_id: ID триггера

        Returns:
            True если успешно
        """
        result = self._request(
            queries.MUTATION_DELETE_TRIGGER,
            {"containerId": container_id, "triggerId": trigger_id},
        )
        self._check_error(result, "deleteYtmTrigger")
        return True

    # ============ ШАБЛОНЫ ============

    def get_templates(
        self,
        container_id: str,
        template_type: Literal["Tag", "Trigger", "Variable"] = "Tag",
        sources: Optional[list[Literal["Yandex", "Personal", "Saved"]]] = None,
        offset: int = 0,
        limit: int = 100,
        search: str = "",
    ) -> list[Template]:
        """
        Получить список доступных шаблонов.

        Args:
            container_id: ID контейнера
            template_type: Тип шаблона (Tag, Trigger, Variable)
            sources: Источники шаблонов (Yandex - встроенные, Personal - свои, Saved)
            offset: Смещение
            limit: Лимит
            search: Поиск
        """
        variables = {
            "containerId": container_id,
            "templateType": template_type,
            "sources": sources or ["Yandex", "Personal", "Saved"],
            "offset": offset,
            "limit": limit,
            "search": search,
        }

        result = self._request(queries.QUERY_AVAILABLE_TEMPLATES, variables)
        data = self._check_error(result, "ytmAvailableTemplates")

        return [Template.from_dict(t) for t in data.get("templates", [])]

    # ============ ПЕРЕМЕННЫЕ ============

    def get_variables(self, container_id: str) -> list[Variable]:
        """
        Получить список встроенных переменных для подстановки в теги.

        Args:
            container_id: ID контейнера

        Returns:
            Список переменных (Click URL, Page Path, etc.)
        """
        result = self._request(
            queries.QUERY_VARIABLES_SUGGEST,
            {"containerId": container_id},
        )
        data = self._check_error(result, "ytmVariablesSuggest")

        return [Variable.from_dict(v) for v in data]

    def get_custom_variables(
        self,
        container_id: str,
        offset: int = 0,
        limit: int = 50,
        search: str = "",
        variable_type: Optional[str] = None,
        ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Получить список кастомных переменных контейнера.

        Args:
            container_id: ID контейнера
            offset: Смещение для пагинации
            limit: Лимит записей
            search: Поисковый запрос
            variable_type: Тип переменных (фильтр)
            ids: Фильтр по ID

        Returns:
            Список кастомных переменных
        """
        variables = {
            "containerId": container_id,
            "offset": offset,
            "limit": limit,
            "search": search,
        }
        if variable_type:
            variables["variableType"] = variable_type
        if ids:
            variables["ids"] = ids

        result = self._request(queries.QUERY_CUSTOM_VARIABLES_LIST, variables)
        data = self._check_error(result, "ytmVariables2")

        return data.get("variables", [])

    def create_variable(
        self,
        container_id: str,
        name: str,
        template_id: str,
        parameters: Optional[list[TemplateParameter]] = None,
    ) -> dict:
        """
        Создать кастомную переменную.

        Args:
            container_id: ID контейнера
            name: Название переменной
            template_id: ID шаблона переменной (js_variable, data_layer, cookie, etc.)
            parameters: Параметры шаблона

        Returns:
            Созданная переменная

        Примеры template_id:
            - js_variable: JavaScript Variable (параметр "1" = имя переменной)
            - data_layer: Data Layer Variable
            - cookie: First-Party Cookie
            - url: URL Variable
            - custom_js: Custom JavaScript
        """
        variable_input = {
            "name": name,
            "templateData": {
                "templateId": template_id,
                "parameters": [p.to_dict() for p in (parameters or [])],
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_VARIABLE,
            {"containerId": container_id, "variable": variable_input},
        )
        return self._check_error(result, "createYtmVariable")

    def create_js_variable(
        self,
        container_id: str,
        name: str,
        js_variable_name: str,
    ) -> dict:
        """
        Создать JavaScript Variable (читает window.xxx).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            js_variable_name: Имя JS переменной (например "myGlobalVar")

        Returns:
            Созданная переменная

        Пример:
            # Читает window.userEmail
            api.create_js_variable(CONTAINER_ID, "User Email", "userEmail")
        """
        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="js_variable",
            parameters=[
                TemplateParameter(
                    type="TextInput",
                    parameter_id="1",
                    value=js_variable_name,
                ),
            ],
        )

    def create_data_layer_variable(
        self,
        container_id: str,
        name: str,
        data_layer_key: str,
    ) -> dict:
        """
        Создать Data Layer Variable (читает из dataLayer).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            data_layer_key: Ключ в dataLayer (поддерживает вложенность через точку)

        Returns:
            Созданная переменная

        Примеры:
            # Читает dataLayer[i].event
            api.create_data_layer_variable(CONTAINER_ID, "Event Name", "event")

            # Читает вложенное значение dataLayer[i].ecommerce.purchase.revenue
            api.create_data_layer_variable(CONTAINER_ID, "Revenue", "ecommerce.purchase.revenue")
        """
        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="datalayer",
            parameters=[
                TemplateParameter(
                    type="TextInput",
                    parameter_id="1",
                    value=data_layer_key,
                ),
            ],
        )

    def create_cookie_variable(
        self,
        container_id: str,
        name: str,
        cookie_name: str,
        url_decode: bool = True,
    ) -> dict:
        """
        Создать Cookie Variable (читает first-party cookie).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            cookie_name: Имя cookie
            url_decode: URL-декодировать значение (по умолчанию True)

        Returns:
            Созданная переменная

        Пример:
            api.create_cookie_variable(CONTAINER_ID, "GA Client ID", "_ga")
        """
        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="first_party_cookie",
            parameters=[
                TemplateParameter(
                    type="TextInput",
                    parameter_id="1",
                    value=cookie_name,
                ),
                TemplateParameter(
                    type="Checkbox",
                    parameter_id="2",
                    value="true" if url_decode else "false",
                ),
            ],
        )

    def create_constant_variable(
        self,
        container_id: str,
        name: str,
        value: str,
    ) -> dict:
        """
        Создать константу.

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            value: Значение константы

        Returns:
            Созданная переменная

        Пример:
            api.create_constant_variable(CONTAINER_ID, "API Key", "pk_live_xxx")
        """
        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="constant",
            parameters=[
                TemplateParameter(
                    type="TextInput",
                    parameter_id="1",
                    value=value,
                ),
            ],
        )

    def create_dom_element_variable(
        self,
        container_id: str,
        name: str,
        selector: str,
        attribute: str = "",
        selection_method: str = "css",
    ) -> dict:
        """
        Создать DOM Element Variable (читает элемент страницы).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            selector: CSS селектор или ID элемента
            attribute: Атрибут для чтения (пусто = текст элемента)
            selection_method: Метод выбора ("id" или "css")

        Returns:
            Созданная переменная

        Примеры:
            # Текст элемента по CSS
            api.create_dom_element_variable(CONTAINER_ID, "Page Title", "h1.title")

            # Атрибут href ссылки
            api.create_dom_element_variable(CONTAINER_ID, "Logo Link", "a.logo", "href")

            # Элемент по ID
            api.create_dom_element_variable(CONTAINER_ID, "Form Email", "email", "value", "id")
        """
        # Метод выбора: 1 = ID, 2 = CSS селектор
        method_value = "1" if selection_method == "id" else "2"

        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="element_dom",
            parameters=[
                TemplateParameter(
                    type="DropDownMenu",
                    parameter_id="1",
                    value=method_value,
                ),
                TemplateParameter(
                    type="TextInput",
                    parameter_id="3",
                    value=selector,
                ),
                TemplateParameter(
                    type="TextInput",
                    parameter_id="4",
                    value=attribute,
                ),
            ],
        )

    def create_url_variable(
        self,
        container_id: str,
        name: str,
        component: Literal["full", "protocol", "host", "port", "path", "extension", "query", "fragment"] = "full",
    ) -> dict:
        """
        Создать URL Variable (читает компоненты текущего URL страницы).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            component: Компонент URL для извлечения:
                - "full" (0): Полный URL
                - "protocol" (1): Протокол (http/https)
                - "host" (2): Имя хоста
                - "port" (3): Порт
                - "path" (4): Путь
                - "extension" (5): Расширение имени файла
                - "query" (6): Запрос (query string)
                - "fragment" (7): Фрагмент (#...)

        Returns:
            Созданная переменная

        Примеры:
            # Полный URL страницы
            api.create_url_variable(CONTAINER_ID, "Page URL", "full")

            # Только путь
            api.create_url_variable(CONTAINER_ID, "Page Path", "path")

            # Расширение файла (.html, .php, etc.)
            api.create_url_variable(CONTAINER_ID, "File Extension", "extension")

            # Query параметры
            api.create_url_variable(CONTAINER_ID, "Query String", "query")
        """
        component_map = {
            "full": "0",
            "protocol": "1",
            "host": "2",
            "port": "3",
            "path": "4",
            "extension": "5",
            "query": "6",
            "fragment": "7",
        }
        component_value = component_map.get(component, "0")

        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="url",
            parameters=[
                TemplateParameter(
                    type="DropDownMenu",
                    parameter_id="1",
                    value=component_value,
                ),
            ],
        )

    def create_referrer_variable(
        self,
        container_id: str,
        name: str,
        component: Literal["full", "protocol", "host", "port", "path", "extension", "query", "fragment"] = "full",
    ) -> dict:
        """
        Создать Referrer Variable (читает компоненты URL перехода).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            component: Компонент URL для извлечения:
                - "full" (0): Полный URL
                - "protocol" (1): Протокол
                - "host" (2): Имя хоста
                - "port" (3): Порт
                - "path" (4): Путь
                - "extension" (5): Расширение имени файла
                - "query" (6): Запрос (query string)
                - "fragment" (7): Фрагмент

        Returns:
            Созданная переменная

        Примеры:
            # Полный URL перехода
            api.create_referrer_variable(CONTAINER_ID, "Referrer URL", "full")

            # Только хост источника
            api.create_referrer_variable(CONTAINER_ID, "Referrer Host", "host")
        """
        component_map = {
            "full": "0",
            "protocol": "1",
            "host": "2",
            "port": "3",
            "path": "4",
            "extension": "5",
            "query": "6",
            "fragment": "7",
        }
        component_value = component_map.get(component, "0")

        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="referrer",
            parameters=[
                TemplateParameter(
                    type="DropDownMenu",
                    parameter_id="1",
                    value=component_value,
                ),
            ],
        )

    def create_lookup_table_variable(
        self,
        container_id: str,
        name: str,
        input_variable: str,
        lookup_table: list[tuple[str, str]],
        default_value: str = "",
    ) -> dict:
        """
        Создать Lookup Table Variable (таблица поиска/маппинг значений).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            input_variable: Входная переменная в формате {{ Variable Name }}
            lookup_table: Список кортежей (входное_значение, результат)
            default_value: Значение по умолчанию, если совпадение не найдено

        Returns:
            Созданная переменная

        Примеры:
            # Маппинг глубины прокрутки на категории
            api.create_lookup_table_variable(
                CONTAINER_ID,
                "Scroll Category",
                "{{ Scroll Depth Threshold }}",
                lookup_table=[
                    ("25", "shallow"),
                    ("50", "medium"),
                    ("75", "deep"),
                    ("100", "complete"),
                ],
                default_value="unknown",
            )

            # Маппинг страниц на типы
            api.create_lookup_table_variable(
                CONTAINER_ID,
                "Page Type",
                "{{ Page Path }}",
                lookup_table=[
                    ("/", "home"),
                    ("/products", "catalog"),
                    ("/cart", "cart"),
                ],
            )
        """
        # Формируем строки таблицы
        rows = []
        for i, (input_val, output_val) in enumerate(lookup_table, start=1):
            rows.append({
                "rowNumber": i,
                "columns": [
                    {"columnNumber": 1, "value": "1"},  # Оператор "=" (equals)
                    {"columnNumber": 2, "value": input_val},
                    {"columnNumber": 3, "value": output_val},
                ],
            })

        # Table требует специальную структуру с rows, поэтому формируем вручную
        variable_input = {
            "name": name,
            "templateData": {
                "templateId": "match_table",
                "parameters": [
                    {
                        "type": "DropDownMenu",
                        "parameterId": "1",
                        "value": input_variable,
                    },
                    {
                        "type": "Table",
                        "parameterId": "2",
                        "rows": rows,
                    },
                    {
                        "type": "TextInput",
                        "parameterId": "3",
                        "value": default_value,
                    },
                ],
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_VARIABLE,
            {"containerId": container_id, "variable": variable_input},
        )
        return self._check_error(result, "createYtmVariable")

    def create_random_number_variable(
        self,
        container_id: str,
        name: str,
    ) -> dict:
        """
        Создать Random Number Variable (генерирует случайное число).

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ

        Returns:
            Созданная переменная

        Пример:
            api.create_random_number_variable(CONTAINER_ID, "Random Number")
        """
        return self.create_variable(
            container_id=container_id,
            name=name,
            template_id="random_number",
            parameters=[],
        )

    def delete_variable(self, container_id: str, variable_id: str) -> bool:
        """
        Удалить кастомную переменную.

        Args:
            container_id: ID контейнера
            variable_id: ID переменной

        Returns:
            True если успешно
        """
        result = self._request(
            queries.MUTATION_DELETE_VARIABLE,
            {"containerId": container_id, "variableId": variable_id},
        )
        self._check_error(result, "deleteYtmVariable")
        return True

    # ============ ПУБЛИКАЦИЯ ============

    def get_changelog(
        self,
        container_id: str,
        version1: Optional[int] = None,
        version2: Optional[int] = None,
    ) -> dict:
        """
        Получить changelog изменений между версиями.

        Args:
            container_id: ID контейнера
            version1: Первая версия (None = текущая опубликованная)
            version2: Вторая версия (None = черновик)

        Returns:
            Словарь с изменениями
        """
        variables = {"containerId": container_id}
        if version1 is not None:
            variables["version1"] = version1
        if version2 is not None:
            variables["version2"] = version2

        result = self._request(queries.QUERY_VERSION_CHANGELOG, variables)
        return self._check_error(result, "ytmContainerVersionChangelog")

    def publish(
        self,
        container_id: str,
        name: str = "",
        description: str = "",
        is_preview: bool = False,
    ) -> bool:
        """
        Опубликовать версию контейнера.

        Args:
            container_id: ID контейнера
            name: Название версии
            description: Описание версии
            is_preview: True для preview режима

        Returns:
            True если успешно
        """
        result = self._request(
            queries.MUTATION_PUBLISH_VERSION,
            {
                "containerId": container_id,
                "isPreview": is_preview,
                "input": {
                    "name": name,
                    "description": description,
                },
            },
        )
        self._check_error(result, "publishYtmVersion")
        return True

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    def create_html_tag_with_trigger(
        self,
        container_id: str,
        tag_name: str,
        html_code: str,
        trigger_name: str = "All Pages",
        trigger_template: str = "page_view",
    ) -> tuple[Tag, Trigger]:
        """
        Создать HTML тег с новым триггером.

        Удобный метод для быстрого создания тега с триггером.

        Args:
            container_id: ID контейнера
            tag_name: Название тега
            html_code: HTML код
            trigger_name: Название триггера
            trigger_template: Шаблон триггера

        Returns:
            Кортеж (созданный тег, созданный триггер)
        """
        # Создаём триггер
        trigger = self.create_trigger(
            container_id=container_id,
            name=trigger_name,
            template_id=trigger_template,
        )

        # Создаём тег с привязкой к триггеру
        tag = self.create_tag(
            container_id=container_id,
            name=tag_name,
            html_code=html_code,
            trigger_ids=[trigger.trigger_id],
        )

        return tag, trigger
