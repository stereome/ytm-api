"""
Основной клиент для Yandex Tag Manager API
"""

import requests
from typing import Literal, Optional
from datetime import datetime

from .models import (
    Tag,
    Trigger,
    Template,
    Variable,
    TemplateData,
    TemplateParameter,
    ActivationCondition,
    ContainerExport,
    ExportedTag,
    ExportedTrigger,
    ExportedVariable,
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

        # Headers (включая Cookie напрямую для надёжности)
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": "https://metrika.yandex.ru",
                "Referer": "https://metrika.yandex.ru/",
                "x-csrf-token": csrf_token,
                "x-uid": uid,
                "x-lang": lang,
                "Cookie": f"Session_id={session_id}",
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

    def create_custom_template(
        self,
        container_id: str,
        name: str,
        template_type: Literal["Tag", "Trigger", "Variable"],
        sandbox_code: str,
        parameters: Optional[list[dict]] = None,
        permissions: Optional[dict] = None,
        description: str = "",
        publish: bool = True,
    ) -> dict:
        """
        Создать кастомный шаблон (тег, триггер или переменная).

        Создаёт draft шаблона и по умолчанию сразу публикует его.
        Только опубликованный шаблон можно использовать для создания
        экземпляров (тегов, триггеров, переменных).

        ВАЖНО: parameterId параметров назначается сервером при создании
        и меняется при публикации. Финальные parameterId доступны только
        в ответе publishYtmTemplate.

        Args:
            container_id: ID контейнера
            name: Название шаблона
            template_type: Тип шаблона ("Tag", "Trigger", "Variable")
            sandbox_code: Код шаблона на sandboxed JS
            parameters: Определения параметров шаблона. Каждый параметр — словарь
                с обязательными полями: parameterId (любое, назначится сервером),
                name, label, order (int), type ("TextInput", "Checkbox", etc.).
                Также обязателен enablingConditions (обычно []).
                Для TextInput нужен textInputConfiguration: {defaultValue, placeholder}.
            permissions: Разрешения sandbox (canAccessTemplateStorage, и т.д.)
            description: Описание шаблона
            publish: Автоматически опубликовать (по умолчанию True)

        Returns:
            Данные опубликованного шаблона. Ключевые поля:
            - templateId: ID для создания экземпляров
            - templateVersion: версия для создания экземпляров
            - data.parameters[].parameterId: ID параметров для create_variable()

        Пример:
            template = api.create_custom_template(
                container_id="70978",
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
            # template["data"]["parameters"][0]["parameterId"] — для create_variable
        """
        template_input = {
            "containerId": container_id,
            "templateId": "",
            "name": name,
            "author": "",
            "type": template_type,
            "publicity": "Private",
            "data": {
                "code": sandbox_code,
                "parameters": parameters or [],
                "permissions": permissions or {},
                "description": description,
                "documentationLink": "",
                "mainPageLink": "",
                "email": "",
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_TEMPLATE,
            {"containerId": container_id, "template": template_input},
        )
        template_data = self._check_error(result, "createYtmTemplate")

        if publish:
            return self.publish_template(container_id, template_data["templateId"])

        return template_data

    def publish_template(self, container_id: str, template_id: str) -> dict:
        """
        Опубликовать кастомный шаблон.

        Публикует текущий draft шаблона. Только опубликованные шаблоны
        можно использовать для создания экземпляров.

        ВАЖНО: при публикации parameterId параметров меняются.
        Финальные ID доступны в возвращённом словаре.

        Args:
            container_id: ID контейнера
            template_id: ID шаблона

        Returns:
            Данные опубликованного шаблона с финальными parameterId
        """
        result = self._request(
            queries.MUTATION_PUBLISH_TEMPLATE,
            {"containerId": container_id, "templateId": template_id},
        )
        return self._check_error(result, "publishYtmTemplate")

    def create_persistent_dl_template(
        self,
        container_id: str,
        name: str = "Persistent DataLayer Variable",
    ) -> dict:
        """
        Создать и опубликовать шаблон «Persistent DataLayer Variable».

        ЯТМ (в отличие от GTM) не ведёт накопленного состояния dataLayer.
        Этот шаблон работает в связке с обычной DL-переменной:

        1. Обычная DL-переменная ловит значение из текущего пуша
        2. Шаблон получает это значение через параметр и кэширует
           в templateStorage. Если DL-переменная пуста — возвращает
           последнее закэшированное значение.

        ВАЖНО: значение должно быть отправлено хотя бы раз ВМЕСТЕ с event:
            dataLayer.push({userId: 'user_42', event: 'login'})
        После этого persistent-переменная будет возвращать userId
        даже в событиях без userId.

        Args:
            container_id: ID контейнера
            name: Название шаблона (по умолчанию "Persistent DataLayer Variable")

        Returns:
            Данные опубликованного шаблона. Передайте этот словарь в
            create_persistent_dl_variable() или create_persistent_dl_variables().

        Пример:
            # Создать шаблон (один раз)
            template = api.create_persistent_dl_template("70978")

            # Создать экземпляры переменных (каждый вызов создаёт 2 переменные)
            api.create_persistent_dl_variable("70978", template, "DL - userId", "userId")
            api.create_persistent_dl_variable("70978", template, "DL - userType", "userType")
        """
        sandbox_code = (
            "const templateStorage = require('templateStorage');\n"
            "const key = data.keyName;\n"
            "const value = data.variableValue;\n"
            "if (value !== undefined && value !== null && value !== '') {\n"
            "  templateStorage.setItem(key, value);\n"
            "  return value;\n"
            "}\n"
            "return templateStorage.getItem(key);\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "keyName",
                "label": "Storage Key",
                "helpText": "Ключ для хранения в templateStorage",
                "order": 0,
                "type": "TextInput",
                "isRequired": False,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "",
                    "placeholder": "например: userId",
                },
            },
            {
                "parameterId": "1",
                "name": "variableValue",
                "label": "DataLayer Variable",
                "helpText": "Переменная ЯТМ вида {{DL - userId}}",
                "order": 1,
                "type": "TextInput",
                "isRequired": False,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "",
                    "placeholder": "{{DL - userId}}",
                },
            },
        ]

        permissions = {
            "canAccessTemplateStorage": True,
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description="Переменная dataLayer с persistent-хранением через templateStorage",
        )

    def create_persistent_dl_variable(
        self,
        container_id: str,
        template_data: dict,
        name: str,
        key_name: str,
        dl_variable_name: Optional[str] = None,
    ) -> dict:
        """
        Создать persistent DataLayer переменную (пару: DL + templateStorage).

        Создаёт ДВЕ переменные:
        1. Обычная DataLayer переменная — ловит значение из текущего пуша
        2. Persistent-переменная на кастомном шаблоне — кэширует через templateStorage

        Шаблон должен быть предварительно создан через create_persistent_dl_template().

        Args:
            container_id: ID контейнера
            template_data: Словарь, возвращённый create_persistent_dl_template()
            name: Название persistent-переменной в ЯТМ
            key_name: Ключ в dataLayer для чтения
            dl_variable_name: Название обычной DL-переменной (по умолчанию "DL - {key_name}")

        Returns:
            Созданная persistent-переменная (dict)

        Пример:
            template = api.create_persistent_dl_template("70978")
            api.create_persistent_dl_variable(
                "70978", template, "DL - userId (persistent)", "userId",
            )
            # Создаст 2 переменные:
            #   "DL - userId" — обычная DL-переменная
            #   "DL - userId (persistent)" — persistent с templateStorage
        """
        template_id = template_data["templateId"]

        # Находим parameterId для параметров
        param_ids = {}
        for p in template_data.get("data", {}).get("parameters", []):
            param_ids[p.get("name")] = p["parameterId"]

        if "keyName" not in param_ids or "variableValue" not in param_ids:
            raise YTMError(
                kind="InvalidTemplate",
                message="Параметры 'keyName' и/или 'variableValue' не найдены в шаблоне. "
                        "Убедитесь, что template_data — результат create_persistent_dl_template().",
            )

        # 1. Создаём обычную DataLayer переменную
        dl_name = dl_variable_name or f"DL - {key_name}"
        self.create_data_layer_variable(
            container_id=container_id,
            name=dl_name,
            data_layer_key=key_name,
        )

        # 2. Создаём persistent-переменную (ссылается на DL-переменную)
        variable_input = {
            "name": name,
            "templateData": {
                "templateId": template_id,
                "parameters": [
                    {
                        "type": "TextInput",
                        "parameterId": param_ids["keyName"],
                        "value": key_name,
                    },
                    {
                        "type": "TextInput",
                        "parameterId": param_ids["variableValue"],
                        "value": "{{" + dl_name + "}}",
                    },
                ],
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_VARIABLE,
            {"containerId": container_id, "variable": variable_input},
        )
        return self._check_error(result, "createYtmVariable")

    def create_persistent_dl_variables(
        self,
        container_id: str,
        template_data: dict,
        keys_map: dict[str, str],
    ) -> list[dict]:
        """
        Массово создать persistent DataLayer переменные.

        Для каждого ключа создаёт пару переменных (DL + persistent).

        Args:
            container_id: ID контейнера
            template_data: Словарь, возвращённый create_persistent_dl_template()
            keys_map: Словарь {key_name: variable_name}, где
                key_name — ключ в dataLayer,
                variable_name — название persistent-переменной в ЯТМ

        Returns:
            Список созданных persistent-переменных

        Пример:
            template = api.create_persistent_dl_template("70978")
            results = api.create_persistent_dl_variables(
                "70978",
                template,
                {
                    "userId": "DL - userId (persistent)",
                    "userType": "DL - userType (persistent)",
                    "clientId": "DL - clientId (persistent)",
                },
            )
            # Создаст 6 переменных (3 пары):
            #   "DL - userId" + "DL - userId (persistent)"
            #   "DL - userType" + "DL - userType (persistent)"
            #   "DL - clientId" + "DL - clientId (persistent)"
        """
        results = []
        for key_name, variable_name in keys_map.items():
            result = self.create_persistent_dl_variable(
                container_id=container_id,
                template_data=template_data,
                name=variable_name,
                key_name=key_name,
            )
            results.append(result)
        return results

    # ============ ШАБЛОНЫ ПЕРЕМЕННЫХ ДЛЯ ГАЛЕРЕИ ============

    def create_url_query_param_template(
        self,
        container_id: str,
        name: str = "URL Query Parameter",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «URL Query Parameter».

        Извлекает значение конкретного GET-параметра из URL страницы.
        Подходит для UTM-меток и любых query-параметров.

        Этот шаблон отсутствует как среди встроенных переменных ЯТМ,
        так и в галерее. Встроенная переменная «URL» возвращает query-строку
        целиком, но извлечь отдельный параметр нельзя.

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            # Создать шаблон (один раз на контейнер)
            template = api.create_url_query_param_template("70978")

            # Создать переменные для UTM-меток
            api.create_variable_from_template("70978", template,
                name="UTM Source", param_values={"paramName": "utm_source"})
            api.create_variable_from_template("70978", template,
                name="UTM Medium", param_values={"paramName": "utm_medium"})
            api.create_variable_from_template("70978", template,
                name="UTM Campaign", param_values={"paramName": "utm_campaign"})
        """
        sandbox_code = (
            "const getUrl = require('getUrl');\n"
            "return getUrl('queryVar', data.paramName);\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "paramName",
                "label": "Имя параметра",
                "helpText": "Имя GET-параметра URL (например: utm_source, utm_medium, gclid)",
                "order": 0,
                "type": "TextInput",
                "isRequired": True,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "",
                    "placeholder": "utm_source",
                },
            },
        ]

        permissions = {
            "canGetUrl": {
                "allComponents": True,
            },
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Извлекает значение GET-параметра из URL страницы. "
                "Подходит для UTM-меток и любых query-параметров."
            ),
        )

    def create_local_storage_template(
        self,
        container_id: str,
        keys: list[str],
        name: str = "localStorage Variable",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «localStorage Variable».

        Читает значение из localStorage браузера по указанному ключу.
        Подходит для SPA-приложений, quiz-платформ, корзин.

        ВАЖНО: ЯТМ требует явный список ключей localStorage в permissions
        шаблона. Wildcard (*) не поддерживается. Передайте все ключи,
        которые планируете читать через переменные этого шаблона.

        Args:
            container_id: ID контейнера
            keys: Список ключей localStorage, к которым шаблон получит доступ
                на чтение (например: ["quiz_result", "cart_id", "user_prefs"])
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_local_storage_template(
                "70978",
                keys=["quiz_result", "cart_id", "user_prefs"],
            )

            api.create_variable_from_template("70978", template,
                name="Quiz Result", param_values={"keyName": "quiz_result"})
            api.create_variable_from_template("70978", template,
                name="Cart ID", param_values={"keyName": "cart_id"})
        """
        sandbox_code = (
            "const localStorage = require('localStorage');\n"
            "if (localStorage) {\n"
            "  return localStorage.getItem(data.keyName);\n"
            "}\n"
            "return undefined;\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "keyName",
                "label": "Ключ localStorage",
                "helpText": "Имя ключа в localStorage для чтения",
                "order": 0,
                "type": "TextInput",
                "isRequired": True,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "",
                    "placeholder": "my_key",
                },
            },
        ]

        permissions = {
            "canAccessLocalStorage": [
                {"key": key, "read": True, "write": False}
                for key in keys
            ],
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Читает значение из localStorage браузера по ключу. "
                "Подходит для SPA, quiz-платформ, корзин."
            ),
        )

    def create_cookie_value_template(
        self,
        container_id: str,
        name: str = "Cookie Value",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Cookie Value».

        Читает значение cookie по имени. Встроенная переменная ЯТМ
        «Собственный файл cookie» (first_party_cookie) существует,
        но доступна только через встроенные шаблоны — этот кастомный
        шаблон удобнее для массового создания через API.

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_cookie_value_template("70978")

            api.create_variable_from_template("70978", template,
                name="YM Client ID", param_values={"cookieName": "_ym_uid"})
            api.create_variable_from_template("70978", template,
                name="GA Client ID", param_values={"cookieName": "_ga"})
        """
        sandbox_code = (
            "const getCookieValues = require('getCookieValues');\n"
            "const values = getCookieValues(data.cookieName);\n"
            "return values && values.length > 0 ? values[0] : undefined;\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "cookieName",
                "label": "Имя cookie",
                "helpText": "Имя cookie для чтения (например: _ym_uid, _ga, utm_source)",
                "order": 0,
                "type": "TextInput",
                "isRequired": True,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "",
                    "placeholder": "_ym_uid",
                },
            },
        ]

        permissions = {
            "canGetCookies": {
                "allKeys": True,
            },
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Читает значение cookie по имени. "
                "Подходит для интеграции с аналитикой, CRM, рекламными системами."
            ),
        )

    def create_referrer_domain_template(
        self,
        container_id: str,
        name: str = "Referrer Domain",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Referrer Domain».

        Извлекает чистый домен (hostname) из document.referrer.
        Встроенная переменная «Referrer» возвращает полный URL,
        этот шаблон — только домен. Параметров не имеет.

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_referrer_domain_template("70978")
            api.create_variable_from_template("70978", template,
                name="Referrer Domain", param_values={})
        """
        sandbox_code = (
            "const getReferrerUrl = require('getReferrerUrl');\n"
            "return getReferrerUrl('host');\n"
        )

        permissions = {
            "canGetReferrer": {
                "allComponents": True,
            },
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=[],
            permissions=permissions,
            description=description or (
                "Извлекает домен из реферера. "
                "Для фильтрации трафика по конкретным площадкам."
            ),
        )

    def create_session_page_views_template(
        self,
        container_id: str,
        name: str = "Session Page Views",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Session Page Views».

        Считает количество просмотров страниц за текущую сессию.
        Использует localStorage с таймаутом 30 минут — если пользователь
        неактивен дольше, счётчик сбрасывается. Параметров не имеет.

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_session_page_views_template("70978")
            api.create_variable_from_template("70978", template,
                name="Session Page Views", param_values={})
        """
        sandbox_code = (
            "const localStorage = require('localStorage');\n"
            "const getTimestamp = require('getTimestamp');\n"
            "const JSON = require('JSON');\n"
            "const templateStorage = require('templateStorage');\n"
            "if (!localStorage) return 1;\n"
            "const now = getTimestamp();\n"
            "const raw = localStorage.getItem('_ytm_spv');\n"
            "let count = 0;\n"
            "if (raw) {\n"
            "  const obj = JSON.parse(raw);\n"
            "  if (obj && (now - obj.t) < 1800000) {\n"
            "    count = obj.c || 0;\n"
            "  }\n"
            "}\n"
            "const done = templateStorage.getItem('spv_done');\n"
            "if (!done) {\n"
            "  count = count + 1;\n"
            "  localStorage.setItem('_ytm_spv', JSON.stringify({c: count, t: now}));\n"
            "  templateStorage.setItem('spv_done', '1');\n"
            "}\n"
            "return count;\n"
        )

        permissions = {
            "canAccessLocalStorage": [
                {"key": "_ytm_spv", "read": True, "write": True},
            ],
            "canAccessTemplateStorage": True,
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=[],
            permissions=permissions,
            description=description or (
                "Счётчик просмотров страниц за сессию (таймаут 30 мин). "
                "Хранится в localStorage."
            ),
        )

    def create_visit_number_template(
        self,
        container_id: str,
        name: str = "Visit Number",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Visit Number».

        Возвращает порядковый номер визита пользователя (1, 2, 3...).
        Визит определяется через localStorage: если с последнего обращения
        прошло больше 30 минут — считается новым визитом.

        Не требует параметров и дополнительных тегов.

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_visit_number_template("70978")
            api.create_variable_from_template("70978", template,
                name="Visit Number", param_values={})
        """
        sandbox_code = (
            "const localStorage = require('localStorage');\n"
            "const getTimestamp = require('getTimestamp');\n"
            "if (!localStorage) return 0;\n"
            "const TIMEOUT = 30 * 60 * 1000;\n"
            "const now = getTimestamp();\n"
            "const rawCount = localStorage.getItem('_ytm_visit_count');\n"
            "const rawTs = localStorage.getItem('_ytm_visit_ts');\n"
            "const count = rawCount ? +rawCount : 0;\n"
            "const lastTs = rawTs ? +rawTs : 0;\n"
            "if (!lastTs || (now - lastTs) > TIMEOUT) {\n"
            "  const newCount = count + 1;\n"
            "  localStorage.setItem('_ytm_visit_count', '' + newCount);\n"
            "  localStorage.setItem('_ytm_visit_ts', '' + now);\n"
            "  return newCount;\n"
            "}\n"
            "localStorage.setItem('_ytm_visit_ts', '' + now);\n"
            "return count;\n"
        )

        permissions = {
            "canAccessLocalStorage": [
                {"key": "_ytm_visit_count", "read": True, "write": True},
                {"key": "_ytm_visit_ts",    "read": True, "write": True},
            ],
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=[],
            permissions=permissions,
            description=description or (
                "Порядковый номер визита пользователя (1, 2, 3...). "
                "Новый визит — таймаут 30 мин без активности. Хранится в localStorage. "
                "Внимание: Safari ITP очищает localStorage после 7 дней неактивности — "
                "при более длинных перерывах счётчик сбросится."
            ),
        )

    def create_traffic_source_template(
        self,
        container_id: str,
        name: str = "Traffic Source",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Traffic Source».

        Возвращает JSON-строку со всеми данными об источнике трафика:
            {"type":"utm","utm_source":"yandex","utm_medium":"cpc",
             "utm_campaign":"brand","utm_content":"","utm_term":"","referrer":""}

        type = "utm" | "referrer" | "direct"
        UTM имеет приоритет над реферером и не перезаписывается им.
        Хранится в localStorage (_ytm_attrib) — совместим с Attribution Source.

        Удобно для скрытого поля формы: одна переменная передаёт всё в CRM.

        Пример:
            template = api.create_traffic_source_template("70978")
            api.create_variable_from_template("70978", template,
                name="Traffic Source", param_values={})
        """
        sandbox_code = (
            "const getUrl = require('getUrl');\n"
            "const getReferrerUrl = require('getReferrerUrl');\n"
            "const localStorage = require('localStorage');\n"
            "const JSON = require('JSON');\n"
            "const STORE_KEY = '_ytm_attrib';\n"
            "const UTM_KEYS = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];\n"
            "if (localStorage) {\n"
            "  const utmSource = getUrl('queryVar', 'utm_source');\n"
            "  if (utmSource) {\n"
            # UTM-визит — перезаписываем всегда
            "    const obj = {type:'utm',utm_source:'',utm_medium:'',utm_campaign:'',utm_content:'',utm_term:'',referrer:''};\n"
            "    for (let i = 0; i < UTM_KEYS.length; i++) {\n"
            "      const v = getUrl('queryVar', UTM_KEYS[i]);\n"
            "      obj[UTM_KEYS[i]] = v || '';\n"
            "    }\n"
            "    localStorage.setItem(STORE_KEY, JSON.stringify(obj));\n"
            "  } else {\n"
            "    const refHost = getReferrerUrl('host');\n"
            "    const curHost = getUrl('host');\n"
            "    if (refHost && refHost !== curHost) {\n"
            # Внешний реферер без UTM — перезаписываем (last non-direct: реферер > старый UTM)
            "      localStorage.setItem(STORE_KEY, JSON.stringify({type:'referrer',utm_source:'',utm_medium:'',utm_campaign:'',utm_content:'',utm_term:'',referrer:refHost}));\n"
            "    }\n"
            # Прямой заход — ничего не трогаем
            "  }\n"
            "}\n"
            "if (!localStorage) return '{\"type\":\"direct\",\"utm_source\":\"\",\"utm_medium\":\"\",\"utm_campaign\":\"\",\"utm_content\":\"\",\"utm_term\":\"\",\"referrer\":\"\"}';\n"
            "const raw = localStorage.getItem(STORE_KEY);\n"
            "return raw || '{\"type\":\"direct\",\"utm_source\":\"\",\"utm_medium\":\"\",\"utm_campaign\":\"\",\"utm_content\":\"\",\"utm_term\":\"\",\"referrer\":\"\"}';\n"
        )

        permissions = {
            "canGetUrl": {
                "allComponents": True,
            },
            "canGetReferrer": {
                "allComponents": True,
            },
            "canAccessLocalStorage": [
                {"key": "_ytm_attrib", "read": True, "write": True},
            ],
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=[],
            permissions=permissions,
            description=description or (
                "Источник трафика в виде JSON: type, utm_source, utm_medium, "
                "utm_campaign, utm_content, utm_term, referrer. "
                "type = utm | referrer | direct. UTM приоритетнее реферера. "
                "Для скрытого поля формы — передаёт всё в CRM одной переменной."
            ),
        )

    def create_attribution_source_template(
        self,
        container_id: str,
        name: str = "Attribution Source",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Attribution Source».

        Сохраняет источник визита в localStorage. Приоритет: UTM > реферер.
        Если пользователь пришёл с UTM — сохраняет UTM-метки.
        Если без UTM, но с внешним реферером, и UTM ещё не сохранён — сохраняет реферер.
        UTM не перезаписывается реферером.

        Из одного шаблона создаётся до 7 переменных:
            type, utm_source, utm_medium, utm_campaign,
            utm_content, utm_term, referrer

        Пример:
            template = api.create_attribution_source_template("70978")
            for field in ["type", "utm_source", "utm_medium", "referrer"]:
                api.create_variable_from_template("70978", template,
                    name=f"Attribution - {field}",
                    param_values={"field": field})
        """
        sandbox_code = (
            "const getUrl = require('getUrl');\n"
            "const getReferrerUrl = require('getReferrerUrl');\n"
            "const localStorage = require('localStorage');\n"
            "const JSON = require('JSON');\n"
            "const STORE_KEY = '_ytm_attrib';\n"
            "const UTM_KEYS = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];\n"
            "const utmSource = getUrl('queryVar', 'utm_source');\n"
            "if (utmSource && localStorage) {\n"
            "  const obj = {type: 'utm'};\n"
            "  for (let i = 0; i < UTM_KEYS.length; i++) {\n"
            "    const v = getUrl('queryVar', UTM_KEYS[i]);\n"
            "    if (v) obj[UTM_KEYS[i]] = v;\n"
            "  }\n"
            "  localStorage.setItem(STORE_KEY, JSON.stringify(obj));\n"
            "} else {\n"
            "  const refHost = getReferrerUrl('host');\n"
            "  const curHost = getUrl('host');\n"
            "  if (refHost && refHost !== curHost && localStorage) {\n"
            "    const raw = localStorage.getItem(STORE_KEY);\n"
            "    const stored = raw ? JSON.parse(raw) : null;\n"
            "    if (!stored || stored.type !== 'utm') {\n"
            "      localStorage.setItem(STORE_KEY, JSON.stringify({type: 'referrer', referrer: refHost}));\n"
            "    }\n"
            "  }\n"
            "}\n"
            "if (!localStorage) return undefined;\n"
            "const raw = localStorage.getItem(STORE_KEY);\n"
            "if (!raw) return undefined;\n"
            "const stored = JSON.parse(raw);\n"
            "return stored ? stored[data.field] : undefined;\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "field",
                "label": "Поле",
                "helpText": "Что возвращать из сохранённого источника визита",
                "order": 0,
                "type": "DropDownMenu",
                "isRequired": True,
                "enablingConditions": [],
                "listConfiguration": {
                    "items": [
                        {"id": "1", "name": "type — utm или referrer",         "value": "type"},
                        {"id": "2", "name": "utm_source",                       "value": "utm_source"},
                        {"id": "3", "name": "utm_medium",                       "value": "utm_medium"},
                        {"id": "4", "name": "utm_campaign",                     "value": "utm_campaign"},
                        {"id": "5", "name": "utm_content",                      "value": "utm_content"},
                        {"id": "6", "name": "utm_term",                         "value": "utm_term"},
                        {"id": "7", "name": "referrer — домен реферера",        "value": "referrer"},
                    ],
                },
            },
        ]

        permissions = {
            "canGetUrl": {
                "allComponents": True,
            },
            "canGetReferrer": {
                "allComponents": True,
            },
            "canAccessLocalStorage": [
                {"key": "_ytm_attrib", "read": True, "write": True},
            ],
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Источник визита: UTM-метки или реферер. "
                "UTM имеет приоритет над реферером и не перезаписывается им. "
                "Хранится в localStorage. Используйте для атрибуции форм и заявок."
            ),
        )

    def create_utm_last_touch_template(
        self,
        container_id: str,
        name: str = "UTM Last Touch",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «UTM Last Touch».

        Возвращает UTM-метку последнего перехода с рекламы. Если на текущей
        странице есть UTM-параметры — сохраняет их в localStorage и возвращает.
        На последующих страницах (без UTM) возвращает сохранённое значение.

        Один шаблон — пять переменных (по одной на каждую UTM-метку):
            utm_source, utm_medium, utm_campaign, utm_content, utm_term

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_utm_last_touch_template("70978")
            for param in ["utm_source", "utm_medium", "utm_campaign"]:
                api.create_variable_from_template("70978", template,
                    name=f"UTM Last Touch — {param}",
                    param_values={"paramName": param})
        """
        sandbox_code = (
            "const getUrl = require('getUrl');\n"
            "const localStorage = require('localStorage');\n"
            "const JSON = require('JSON');\n"
            "const STORE_KEY = '_ytm_utm_last';\n"
            "const UTM_KEYS = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];\n"
            "const source = getUrl('queryVar', 'utm_source');\n"
            "if (source && localStorage) {\n"
            "  const utms = {};\n"
            "  for (let i = 0; i < UTM_KEYS.length; i++) {\n"
            "    const val = getUrl('queryVar', UTM_KEYS[i]);\n"
            "    if (val) utms[UTM_KEYS[i]] = val;\n"
            "  }\n"
            "  localStorage.setItem(STORE_KEY, JSON.stringify(utms));\n"
            "}\n"
            "if (!localStorage) return undefined;\n"
            "const raw = localStorage.getItem(STORE_KEY);\n"
            "if (!raw) return undefined;\n"
            "const stored = JSON.parse(raw);\n"
            "return stored ? stored[data.paramName] : undefined;\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "paramName",
                "label": "UTM-параметр",
                "helpText": "Какую UTM-метку возвращать",
                "order": 0,
                "type": "DropDownMenu",
                "isRequired": True,
                "enablingConditions": [],
                "listConfiguration": {
                    "items": [
                        {"id": "1", "name": "utm_source",   "value": "utm_source"},
                        {"id": "2", "name": "utm_medium",   "value": "utm_medium"},
                        {"id": "3", "name": "utm_campaign", "value": "utm_campaign"},
                        {"id": "4", "name": "utm_content",  "value": "utm_content"},
                        {"id": "5", "name": "utm_term",     "value": "utm_term"},
                    ],
                },
            },
        ]

        permissions = {
            "canGetUrl": {
                "allComponents": True,
            },
            "canAccessLocalStorage": [
                {"key": "_ytm_utm_last", "read": True, "write": True},
            ],
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "UTM-метка последнего рекламного перехода. "
                "Сохраняется в localStorage при заходе с UTM и доступна "
                "на всех последующих страницах сессии."
            ),
        )

    def create_ym_client_id_template(
        self,
        container_id: str,
        name: str = "Metrica Client ID",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Metrica Client ID».

        Возвращает Client ID Яндекс.Метрики из cookie _ym_uid.
        Аналог GA Client ID для Яндекс.Метрики.

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_ym_client_id_template("70978")
            api.create_variable_from_template("70978", template,
                name="Metrica Client ID", param_values={})
        """
        sandbox_code = (
            "const getCookieValues = require('getCookieValues');\n"
            "const values = getCookieValues('_ym_uid');\n"
            "if (values && values.length > 0) {\n"
            "  return values[0];\n"
            "}\n"
            "return undefined;\n"
        )

        permissions = {
            "canGetCookies": {
                "allKeys": True,
            },
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=[],
            permissions=permissions,
            description=description or (
                "Client ID Яндекс.Метрики из cookie _ym_uid. "
                "Требует установленного счётчика Метрики на странице."
            ),
        )

    def create_is_returning_visitor_template(
        self,
        container_id: str,
        name: str = "Is Returning Visitor",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Is Returning Visitor».

        Возвращает "new" для первого визита и "returning" для повторных.
        Проверяет наличие cookie с настраиваемым именем.

        ВАЖНО: эта переменная только читает cookie. Для корректной работы
        нужен тег (Custom HTML), который ставит cookie при первом визите:
        document.cookie = "имя_cookie=1; max-age=31536000; path=/";

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_is_returning_visitor_template("70978")
            api.create_variable_from_template("70978", template,
                name="Visitor Type", param_values={"cookieName": "_ytm_visited"})
        """
        sandbox_code = (
            "const getCookieValues = require('getCookieValues');\n"
            "const values = getCookieValues(data.cookieName);\n"
            "if (values && values.length > 0) {\n"
            "  return 'returning';\n"
            "}\n"
            "return 'new';\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "cookieName",
                "label": "Имя cookie",
                "helpText": "Cookie, по которой определяется повторный визит",
                "order": 0,
                "type": "TextInput",
                "isRequired": True,
                "enablingConditions": [],
                "textInputConfiguration": {
                    "defaultValue": "_ytm_visited",
                    "placeholder": "_ytm_visited",
                },
            },
        ]

        permissions = {
            "canGetCookies": {
                "allKeys": True,
            },
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Определяет новый или вернувшийся посетитель (new / returning). "
                "Читает cookie; для установки cookie нужен отдельный тег."
            ),
        )

    def create_timestamp_template(
        self,
        container_id: str,
        name: str = "Timestamp",
        description: str = "",
    ) -> dict:
        """
        Создать и опубликовать шаблон переменной «Timestamp».

        Возвращает текущее время в выбранном формате.
        Параметр format: "ms" (unix ms, по умолчанию), "s" (unix seconds).

        Args:
            container_id: ID контейнера
            name: Название шаблона
            description: Описание шаблона

        Returns:
            Данные опубликованного шаблона. Передайте в create_variable_from_template().

        Пример:
            template = api.create_timestamp_template("70978")

            api.create_variable_from_template("70978", template,
                name="Timestamp (ms)", param_values={"format": "ms"})
            api.create_variable_from_template("70978", template,
                name="Timestamp (s)", param_values={"format": "s"})
        """
        sandbox_code = (
            "const getTimestamp = require('getTimestamp');\n"
            "const Math = require('Math');\n"
            "const ts = getTimestamp();\n"
            "if (data.format === 'iso') {\n"
            "  const s = Math.floor(ts / 1000);\n"
            "  const tod = s % 86400;\n"
            "  const h = Math.floor(tod / 3600);\n"
            "  const mn = Math.floor((tod % 3600) / 60);\n"
            "  const sc = tod % 60;\n"
            "  const z = Math.floor(s / 86400) + 719468;\n"
            "  const era = Math.floor((z >= 0 ? z : z - 146096) / 146097);\n"
            "  const doe = z - era * 146097;\n"
            "  const yoe = Math.floor((doe - Math.floor(doe/1460) + Math.floor(doe/36524) - Math.floor(doe/146096)) / 365);\n"
            "  const y = yoe + era * 400;\n"
            "  const doy = doe - (365*yoe + Math.floor(yoe/4) - Math.floor(yoe/100));\n"
            "  const mp = Math.floor((5*doy + 2) / 153);\n"
            "  const day = doy - Math.floor((153*mp+2)/5) + 1;\n"
            "  const month = mp + (mp < 10 ? 3 : -9);\n"
            "  const year = y + (month <= 2 ? 1 : 0);\n"
            "  const ph = h < 10 ? '0'+h : ''+h;\n"
            "  const pm = mn < 10 ? '0'+mn : ''+mn;\n"
            "  const ps = sc < 10 ? '0'+sc : ''+sc;\n"
            "  const pmo = month < 10 ? '0'+month : ''+month;\n"
            "  const pd = day < 10 ? '0'+day : ''+day;\n"
            "  return year+'-'+pmo+'-'+pd+'T'+ph+':'+pm+':'+ps+'Z';\n"
            "}\n"
            "if (data.format === 's') {\n"
            "  return Math.floor(ts / 1000);\n"
            "}\n"
            "return ts;\n"
        )

        parameters = [
            {
                "parameterId": "0",
                "name": "format",
                "label": "Формат",
                "helpText": "Выберите формат возвращаемого значения",
                "order": 0,
                "type": "DropDownMenu",
                "isRequired": True,
                "enablingConditions": [],
                "listConfiguration": {
                    "items": [
                        {"id": "1", "name": "Unix мс — 1234567890123", "value": "ms"},
                        {"id": "2", "name": "Unix сек — 1234567890",   "value": "s"},
                        {"id": "3", "name": "ISO 8601 UTC — 2026-03-05T10:14:07Z", "value": "iso"},
                    ],
                },
            },
        ]

        permissions = {}

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Variable",
            sandbox_code=sandbox_code,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Текущее время в формате unix мс или unix сек. "
                "Для отметок времени в тегах и триггерах."
            ),
        )

    def create_variable_from_template(
        self,
        container_id: str,
        template_data: dict,
        name: str,
        param_values: dict[str, str],
    ) -> dict:
        """
        Создать переменную из опубликованного кастомного шаблона.

        Универсальный метод для создания экземпляров любых кастомных шаблонов
        переменных. Автоматически маппит имена параметров на их parameterId.

        Args:
            container_id: ID контейнера
            template_data: Словарь, возвращённый create_custom_template(),
                create_url_query_param_template(), create_local_storage_template() и т.д.
            name: Название переменной в ЯТМ
            param_values: Словарь {имя_параметра: значение}

        Returns:
            Созданная переменная (dict)

        Пример:
            template = api.create_url_query_param_template("70978")

            api.create_variable_from_template(
                "70978", template,
                name="UTM Source",
                param_values={"paramName": "utm_source"},
            )
        """
        template_id = template_data["templateId"]

        # Маппинг имён параметров на их ID и тип
        param_ids = {}
        param_types = {}
        for p in template_data.get("data", {}).get("parameters", []):
            param_ids[p.get("name")] = p["parameterId"]
            param_types[p.get("name")] = p.get("type", "TextInput")

        # Формируем параметры
        parameters = []
        for param_name, value in param_values.items():
            if param_name not in param_ids:
                raise YTMError(
                    kind="InvalidParameter",
                    message=f"Параметр '{param_name}' не найден в шаблоне. "
                            f"Доступные: {list(param_ids.keys())}",
                )
            parameters.append({
                "type": param_types[param_name],
                "parameterId": param_ids[param_name],
                "value": value,
            })

        variable_input = {
            "name": name,
            "templateData": {
                "templateId": template_id,
                "parameters": parameters,
            },
        }

        result = self._request(
            queries.MUTATION_CREATE_VARIABLE,
            {"containerId": container_id, "variable": variable_input},
        )
        return self._check_error(result, "createYtmVariable")

    # ============ ШАБЛОНЫ ТЕГОВ ДЛЯ ГАЛЕРЕИ ============
    #
    # Sandbox тегов ЯТМ (проверено линтером 1.61.0, 30.09.2026):
    # - колбэки завершения: data.ytmOnSuccess / data.ytmOnFailure (обязательны)
    # - загрузка скрипта: require('loadScript'), НЕ injectScript
    # - есть: callInWindow, copyFromWindow, setInWindow, createQueue,
    #   createArgumentsQueue, sendPixel, injectHiddenIframe, callLater, setCookie,
    #   isConsentGranted, addConsentListener, makeNumber, makeTableMap, getType
    # - нет: injectScript, makeString, makeInteger, createPushToDataLayer,
    #   addEventCallback, sha256, toBase64, parseUrl
    # - permissions.logging — enum ("Always" работает, "Debug"/"DebugOnly" нет)
    # - canAccessAllGlobals во входных данных отсутствует, только canAccessGlobals

    WEB_VITALS_LIB_URLS = {
        "unpkg": "https://unpkg.com/web-vitals@5/dist/web-vitals.iife.js",
        "jsdelivr": "https://cdn.jsdelivr.net/npm/web-vitals@5/dist/web-vitals.iife.js",
    }

    _WEB_VITALS_CODE = """const loadScript = require('loadScript');
const callInWindow = require('callInWindow');
const templateStorage = require('templateStorage');
const getUrl = require('getUrl');
const makeNumber = require('makeNumber');
const Math = require('Math');

const LIBS = {
  unpkg: 'https://unpkg.com/web-vitals@5/dist/web-vitals.iife.js',
  jsdelivr: 'https://cdn.jsdelivr.net/npm/web-vitals@5/dist/web-vitals.iife.js'
};
const counterId = makeNumber(data.counterId);
const names = data.metricSet === 'all' ? ['LCP', 'INP', 'CLS', 'FCP', 'TTFB'] : ['LCP', 'INP', 'CLS'];
const path = data.detail === 'path' ? getUrl('path') : '';

const send = function(metric) {
  const value = metric.name === 'CLS'
    ? Math.round(metric.value * 1000) / 1000
    : Math.round(metric.value);
  const byRating = {};
  if (path) {
    const byPath = {};
    byPath[path] = value;
    byRating[metric.rating] = byPath;
  } else {
    byRating[metric.rating] = value;
  }
  const byMetric = {};
  byMetric[metric.name] = byRating;
  callInWindow('ym', counterId, 'params', {'Web Vitals': byMetric});
  if (data.poorGoal && metric.rating === 'poor') {
    callInWindow('ym', counterId, 'reachGoal', data.poorGoal, {metric: metric.name, value: value});
  }
};

// Подписка один раз на загрузку страницы, даже если тег сработал повторно
if (templateStorage.getItem('registered')) {
  data.ytmOnSuccess();
} else {
  templateStorage.setItem('registered', true);
  loadScript(LIBS[data.cdn] || LIBS.unpkg, function() {
    for (let i = 0; i < names.length; i++) {
      callInWindow('webVitals.on' + names[i], send);
    }
    data.ytmOnSuccess();
  }, function() {
    templateStorage.removeItem('registered');
    data.ytmOnFailure();
  });
}
"""

    # Откуда шаблон грузит трекер. В рантайме ЯТМ маски в хосте
    # (https://*.ru/, *.dinamikapro.ru, **.ru) не работают — «Permission denied
    # for loadScript», хотя линтер их пропускает; работает только точный хост
    # (путь может быть с *). Поэтому трекер — с фиксированного хоста, а события
    # идут на api_host клиента. Проверено в превью dpmn.ru 30.09.2026.
    DINAMIKA_SCRIPT_HOST = "https://demo.dinamikapro.ru"

    _DINAMIKA_CODE = """const loadScript = require('loadScript');
const callInWindow = require('callInWindow');
const copyFromWindow = require('copyFromWindow');
const createQueue = require('createQueue');
const getCookieValues = require('getCookieValues');
const templateStorage = require('templateStorage');

const SCRIPT_URL = '__SCRIPT_URL__';
let host = data.apiHost ? data.apiHost.trim() : '';
if (host.charAt(host.length - 1) === '/') {
  host = host.substring(0, host.length - 1);
}

const parseProps = function(str) {
  const props = {};
  if (!str) return props;
  const pairs = str.split(';');
  for (let i = 0; i < pairs.length; i++) {
    const idx = pairs[i].indexOf('=');
    if (idx > 0) {
      const key = pairs[i].substring(0, idx).trim();
      if (key) props[key] = pairs[i].substring(idx + 1).trim();
    }
  }
  return props;
};

// callInWindow/copyFromWindow копируют результат в sandbox; экземпляр PostHog
// цикличен, и его копирование падает с «Maximum call stack size exceeded».
// Поэтому posthog.init не вызываем, а объект posthog не читаем: инициализацию
// делает сам array.js по заглушке posthog._i, как в штатном сниппете,
// а наличие трекера проверяем по примитивам __loaded / __SV.
const run = function() {
  if (data.metrikaClientId !== 'no') {
    const cid = getCookieValues('_ym_uid');
    if (cid && cid.length > 0 && cid[0]) {
      callInWindow('posthog.register', {metrika_client_id: cid[0]});
    }
  }
  if (data.userId) {
    callInWindow('posthog.identify', data.userId);
  }
  if (data.tagType === 'event' && data.eventName) {
    callInWindow('posthog.capture', data.eventName, parseProps(data.eventProps));
  }
  data.ytmOnSuccess();
};

// Трекер уже на странице (загружен или стоит сниппет другого тега) —
// повторно не грузим и не инициализируем
if ((copyFromWindow('posthog.__loaded') || copyFromWindow('posthog.__SV'))
    && !templateStorage.getItem('loading')) {
  run();
} else {
  // Теги, сработавшие до загрузки трекера, ждут в очереди
  const queue = templateStorage.getItem('queue') || [];
  queue.push(run);
  templateStorage.setItem('queue', queue);
  if (!templateStorage.getItem('loading')) {
    templateStorage.setItem('loading', true);
    // Заглушка как у штатного сниппета: window.posthog = [], posthog._i = [[ключ, настройки]].
    // createQueue создаёт настоящие массивы (setInWindow с {_i: [...]} array.js не принимает)
    createQueue('posthog');
    const pushInit = createQueue('posthog._i');
    pushInit([data.apiKey, {
      api_host: host,
      defaults: '2025-05-24',
      person_profiles: data.personProfiles || 'identified_only',
      autocapture: data.autocapture !== 'off'
    }]);
    loadScript(SCRIPT_URL, function() {
      templateStorage.setItem('loading', false);
      const pending = templateStorage.getItem('queue') || [];
      templateStorage.setItem('queue', []);
      for (let i = 0; i < pending.length; i++) {
        pending[i]();
      }
    }, function() {
      templateStorage.setItem('loading', false);
      templateStorage.setItem('queue', []);
      data.ytmOnFailure();
    });
  }
}
"""

    @staticmethod
    def _text_param(name: str, label: str, order: int, help_text: str = "",
                    required: bool = False, default: str = "",
                    placeholder: str = "") -> dict:
        return {
            "parameterId": str(order),
            "name": name,
            "label": label,
            "helpText": help_text,
            "order": order,
            "type": "TextInput",
            "isRequired": required,
            "enablingConditions": [],
            "textInputConfiguration": {
                "defaultValue": default,
                "placeholder": placeholder,
            },
        }

    @staticmethod
    def _dropdown_param(name: str, label: str, order: int,
                        items: list[tuple[str, str]], help_text: str = "") -> dict:
        """items — пары (подпись, значение); первый пункт — значение по умолчанию."""
        return {
            "parameterId": str(order),
            "name": name,
            "label": label,
            "helpText": help_text,
            "order": order,
            "type": "DropDownMenu",
            "isRequired": True,
            "enablingConditions": [],
            "listConfiguration": {
                "items": [
                    {"id": str(i + 1), "name": title, "value": value}
                    for i, (title, value) in enumerate(items)
                ],
            },
        }

    def create_web_vitals_template(
        self,
        container_id: str,
        name: str = "Core Web Vitals → Яндекс Метрика",
        description: str = "",
        publish: bool = True,
    ) -> dict:
        """
        Создать шаблон тега «Core Web Vitals → Яндекс Метрика».

        Загружает библиотеку web-vitals (5,9 КБ) и отправляет LCP, INP, CLS
        (опционально FCP, TTFB) в параметры визита Метрики:
        {"Web Vitals": {"LCP": {"good": 2150}}} или с путём страницы
        {"Web Vitals": {"LCP": {"poor": {"/catalog": 4800}}}}.
        LCP/INP/FCP/TTFB — в миллисекундах, CLS — безразмерный (3 знака).
        Опционально достигает цели при оценке poor.

        Тег ставится на триггер «Просмотр страницы»; повторное срабатывание
        на той же странице игнорируется.

        Пример:
            template = api.create_web_vitals_template("70978")
            api.create_tag_from_template("70978", template, "Web Vitals",
                param_values={"counterId": "12345678"},
                trigger_ids=[page_view_trigger_id])
        """
        parameters = [
            self._text_param(
                "counterId", "Номер счётчика Метрики", 0, required=True,
                placeholder="12345678",
                help_text="Счётчик, в параметры визита которого уйдут метрики",
            ),
            self._dropdown_param(
                "metricSet", "Метрики", 1,
                [("Core Web Vitals — LCP, INP, CLS", "core"),
                 ("Все — LCP, INP, CLS, FCP, TTFB", "all")],
            ),
            self._dropdown_param(
                "detail", "Детализация", 2,
                [("Только оценка и значение", "rating"),
                 ("С путём страницы — для поиска медленных страниц", "path")],
                help_text="С путём страницы в параметрах визита появится "
                          "уровень с адресом, например /catalog",
            ),
            self._text_param(
                "poorGoal", "Цель при плохой оценке", 3,
                placeholder="web_vitals_poor",
                help_text="Идентификатор JavaScript-цели. Пусто — цель "
                          "не отправляется",
            ),
            self._dropdown_param(
                "cdn", "Источник библиотеки web-vitals", 4,
                [("unpkg.com", "unpkg"), ("cdn.jsdelivr.net", "jsdelivr")],
            ),
        ]

        permissions = {
            "canLoadScriptUrls": list(self.WEB_VITALS_LIB_URLS.values()),
            "canAccessGlobals": [
                {"key": "ym", "read": True, "write": False, "execute": True},
            ] + [
                {"key": f"webVitals.on{m}", "read": True, "write": False, "execute": True}
                for m in ("LCP", "INP", "CLS", "FCP", "TTFB")
            ],
            "canGetUrl": {"allComponents": True},
            "canAccessTemplateStorage": True,
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Tag",
            sandbox_code=self._WEB_VITALS_CODE,
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Замеряет скорость загрузки и отзывчивость страниц (LCP, INP, "
                "CLS) у реальных посетителей и отправляет их в параметры "
                "визита Яндекс Метрики."
            ),
            publish=publish,
        )

    def create_dinamika_template(
        self,
        container_id: str,
        name: str = "Динамика",
        description: str = "",
        script_host: Optional[str] = None,
        publish: bool = True,
    ) -> dict:
        """
        Создать шаблон тега «Динамика» (продуктовая аналитика).

        Два режима (параметр tagType):
        - init — загружает трекер (с DINAMIKA_SCRIPT_HOST) и инициализирует
          проект; события уходят на сервер из параметра apiHost;
        - event — отправляет событие с свойствами «ключ=значение; ...».
        В обоих режимах трекер при необходимости загружается и
        инициализируется, поэтому ключ и адрес сервера нужны в каждом теге
        (удобно вынести в переменные-константы).

        Опционально прикрепляет ClientID Метрики (_ym_uid) ко всем событиям
        как metrika_client_id — для склейки с данными Метрики.

        Args:
            script_host: Хост, с которого грузится трекер /static/array.js.
                По умолчанию DINAMIKA_SCRIPT_HOST (для галереи). Для on-prem
                клиента, которому нельзя грузить JS снаружи периметра, —
                его сервер: получится приватный шаблон под этот хост.
        """
        script_url = (script_host or self.DINAMIKA_SCRIPT_HOST).rstrip("/") + "/static/array.js"

        parameters = [
            self._dropdown_param(
                "tagType", "Тип тега", 0,
                [("Инициализация — подключить Динамику", "init"),
                 ("Событие — отправить событие", "event")],
            ),
            self._text_param(
                "apiKey", "Ключ проекта", 1, required=True,
                placeholder="phc_...",
                help_text="Настройки проекта в Динамике → Ключ проекта",
            ),
            self._text_param(
                "apiHost", "Адрес сервера Динамики", 2, required=True,
                placeholder="https://dinamika.example.ru",
                help_text="Адрес, по которому открывается интерфейс Динамики",
            ),
            self._dropdown_param(
                "personProfiles", "Профили пользователей", 3,
                [("Только для идентифицированных", "identified_only"),
                 ("Для всех посетителей", "always")],
            ),
            self._dropdown_param(
                "autocapture", "Автосбор кликов и форм", 4,
                [("Включён", "on"), ("Выключен", "off")],
            ),
            self._dropdown_param(
                "metrikaClientId", "ClientID Яндекс Метрики", 5,
                [("Прикреплять к событиям (metrika_client_id)", "yes"),
                 ("Не прикреплять", "no")],
                help_text="Позволяет связать данные Динамики и Метрики "
                          "по одному посетителю",
            ),
            self._text_param(
                "userId", "ID пользователя", 6,
                placeholder="{{User ID}}",
                help_text="Если задан — посетитель идентифицируется. "
                          "Не передавайте email и телефон",
            ),
            self._text_param(
                "eventName", "Название события", 7,
                placeholder="form_submit",
                help_text="Только для типа «Событие»",
            ),
            self._text_param(
                "eventProps", "Свойства события", 8,
                placeholder="form=callback; page={{Page Path}}",
                help_text="Пары ключ=значение через точку с запятой",
            ),
        ]

        permissions = {
            "canLoadScriptUrls": [script_url],
            "canAccessGlobals": [
                {"key": "posthog", "read": True, "write": True, "execute": False},
                {"key": "posthog.__loaded", "read": True, "write": False, "execute": False},
                {"key": "posthog.__SV", "read": True, "write": False, "execute": False},
                {"key": "posthog._i", "read": True, "write": True, "execute": False},
            ] + [
                {"key": f"posthog.{m}", "read": True, "write": False, "execute": True}
                for m in ("register", "identify", "capture")
            ],
            "canGetCookies": {"allKeys": False, "keys": ["_ym_uid"]},
            "canAccessTemplateStorage": True,
        }

        return self.create_custom_template(
            container_id=container_id,
            name=name,
            template_type="Tag",
            sandbox_code=self._DINAMIKA_CODE.replace("__SCRIPT_URL__", script_url),
            parameters=parameters,
            permissions=permissions,
            description=description or (
                "Подключает Динамику — российскую платформу продуктовой "
                "аналитики — и отправляет события. Прикрепляет ClientID "
                "Яндекс Метрики для сквозного анализа."
            ),
            publish=publish,
        )

    def create_tag_from_template(
        self,
        container_id: str,
        template_data: dict,
        name: str,
        param_values: dict[str, str],
        trigger_ids: Optional[list[str]] = None,
    ) -> Tag:
        """
        Создать тег из опубликованного кастомного шаблона тега.

        Аналог create_variable_from_template(): маппит имена параметров
        на parameterId из ответа publishYtmTemplate.
        """
        param_ids = {}
        param_types = {}
        for p in template_data.get("data", {}).get("parameters", []):
            param_ids[p.get("name")] = p["parameterId"]
            param_types[p.get("name")] = p.get("type", "TextInput")

        parameters = []
        for param_name, value in param_values.items():
            if param_name not in param_ids:
                raise YTMError(
                    kind="InvalidParameter",
                    message=f"Параметр '{param_name}' не найден в шаблоне. "
                            f"Доступные: {list(param_ids.keys())}",
                )
            parameters.append(TemplateParameter(
                type=param_types[param_name],
                parameter_id=param_ids[param_name],
                value=value,
            ))

        return self.create_tag(
            container_id=container_id,
            name=name,
            template_id=template_data["templateId"],
            trigger_ids=trigger_ids,
            parameters=parameters,
        )

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

    # ============ ТЕГИ/ТРИГГЕРЫ С КОДОМ (через changelog) ============

    def get_tags_with_code(
        self,
        container_id: str,
        version: Optional[int] = None,
    ) -> list[Tag]:
        """
        Получить теги контейнера ВКЛЮЧАЯ html_code и parameters.

        Стандартный get_tags() не возвращает параметры (поле parameters в
        GraphQL-схеме YtmTag отсутствует), поэтому код тега всегда None.
        Этот метод обходит ограничение через ytmContainerVersionChangelog,
        который отдаёт ytmTagDetailed (с parameters).

        Args:
            container_id: ID контейнера
            version: Номер версии для чтения (None = последняя published).
                     Например 14 для конкретной версии, None для текущей.

        Returns:
            Список Tag с заполненным parameters. Извлечь код:
                tag.html_code  # property — берёт parameter type='Code' parameterId='0'
                # или вручную:
                next((p.value for p in tag.parameters if p.type=='Code'), None)

        Пример:
            tags = api.get_tags_with_code("70978")
            for t in tags:
                if t.html_code and 'reachGoal' in t.html_code:
                    print(t.name, '→', t.html_code[:80])
        """
        snapshot = self.get_container_snapshot(container_id, version=version)
        return snapshot["tags"]

    def get_triggers_with_params(
        self,
        container_id: str,
        version: Optional[int] = None,
    ) -> list[Trigger]:
        """
        Получить триггеры контейнера ВКЛЮЧАЯ parameters и activationConditions.

        Аналогично get_tags_with_code() — стандартный get_triggers() не возвращает
        parameters (для custom_event там содержится имя event'а dataLayer).

        Args:
            container_id: ID контейнера
            version: Номер версии (None = последняя published)

        Returns:
            Список Trigger с заполненными parameters и activation_conditions
        """
        snapshot = self.get_container_snapshot(container_id, version=version)
        return snapshot["triggers"]

    def get_container_snapshot(
        self,
        container_id: str,
        version: Optional[int] = None,
    ) -> dict:
        """
        Полный snapshot контейнера: tags + triggers + variables, все с parameters.

        Внутри использует ytmContainerVersionChangelog (полные ytmTagDetailed,
        ytmTriggerDetailed, ytmVariableDetailed). Один HTTP-запрос — всё сразу.

        Args:
            container_id: ID контейнера
            version: Версия для чтения (None = последняя published).
                     Передайте конкретное число чтобы прочитать историческую версию.

        Returns:
            {
                "version": int,            # номер версии, прочитанной
                "name": str,               # имя версии
                "tags": [Tag, ...],        # с parameters / html_code
                "triggers": [Trigger, ...],# с parameters / activation_conditions
                "variables": [dict, ...],  # raw dicts (отдельной модели Variable нет)
                "raw": dict,               # сырой response для отладки
            }

        Пример:
            snap = api.get_container_snapshot("70978")
            print(f"Version {snap['version']}: {len(snap['tags'])} tags")

            # Найти теги с zombie-триггерами
            existing_trigger_ids = {t.trigger_id for t in snap['triggers']}
            for tag in snap['tags']:
                missing = [tid for tid in tag.trigger_ids if tid not in existing_trigger_ids]
                if missing:
                    print(f"⚠️  {tag.name} → triggers {missing} НЕ существуют")
        """
        variables = {"containerId": container_id}
        if version is not None:
            variables["version1"] = version

        result = self._request(queries.QUERY_VERSION_CHANGELOG, variables)
        data = self._check_error(result, "ytmContainerVersionChangelog")

        # version1 — основная версия (если version=None, это будет current published)
        v = (data or {}).get("version1") or {}

        return {
            "version": v.get("version"),
            "name": v.get("name", ""),
            "tags": [Tag.from_dict(t) for t in (v.get("tags") or [])],
            "triggers": [Trigger.from_dict(t) for t in (v.get("triggers") or [])],
            "variables": list(v.get("variables") or []),
            "raw": data,
        }

    def find_zombie_trigger_refs(
        self,
        container_id: str,
        version: Optional[int] = None,
    ) -> list[dict]:
        """
        Найти теги, ссылающиеся на несуществующие триггеры (zombie references).

        ВАЖНО про матчинг: в YTM-снапшоте у триггеров два ID:
        - `triggerId` — внутренний ID конкретной версии (меняется при каждом снапшоте)
        - `originalTriggerId` — стабильный публичный ID

        Поле `tag.triggerIds` содержит **originalTriggerId** триггеров, на которые
        тег ссылается. Поэтому матчим именно с `trigger.originalTriggerId`,
        а не с `triggerId` — иначе все триггеры выглядят как «несуществующие».

        Это диагностика частой проблемы: тег создан, привязан к триггеру,
        потом триггер удалён или потерял published-статус — тег остаётся
        active, но никогда не срабатывает.

        Returns:
            [
                {
                    "tag_id": str, "tag_name": str, "tag_status": str,
                    "missing_trigger_ids": [str, ...],
                },
                ...
            ]

        Пример:
            zombies = api.find_zombie_trigger_refs("70978")
            for z in zombies:
                print(f"❌ {z['tag_name']} → triggers {z['missing_trigger_ids']} missing")
        """
        snap = self.get_container_snapshot(container_id, version=version)

        # Матчинг по originalTriggerId — это то, на что ссылается tag.triggerIds.
        # Включаем также trigger_id на случай старых данных с прямыми ID.
        existing = set()
        for t in snap["triggers"]:
            if t.original_trigger_id:
                existing.add(t.original_trigger_id)
            if t.trigger_id:
                existing.add(t.trigger_id)

        result = []
        for tag in snap["tags"]:
            missing = [tid for tid in tag.trigger_ids if tid not in existing]
            if missing:
                result.append({
                    "tag_id": tag.tag_id,
                    "tag_name": tag.name,
                    "tag_status": tag.status,
                    "template_id": tag.template_id,
                    "missing_trigger_ids": missing,
                })
        return result

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

    def preview(
        self,
        container_id: str,
        site_url: Optional[str] = None,
    ) -> str:
        """
        Активировать предварительный просмотр контейнера.

        Публикует preview-версию и возвращает ключ предпросмотра.
        Если передан site_url — возвращает готовую ссылку.

        Args:
            container_id: ID контейнера
            site_url: URL сайта (например "https://dpmn.ru")

        Returns:
            Preview-ключ или полная ссылка (если передан site_url)

        Пример:
            # Только ключ
            key = api.preview("70978")
            # "2788228429716318020"

            # Готовая ссылка
            url = api.preview("70978", site_url="https://dpmn.ru")
            # "https://dpmn.ru/?_ytm_preview=2788228429716318020"
        """
        # 1. Публикуем preview-версию
        self.publish(container_id, is_preview=True)

        # 2. Получаем previewKey из последней preview-версии
        result = self._request(
            queries.QUERY_LATEST_VERSION,
            {"containerId": container_id, "isPreview": True},
        )
        data = self._check_error(result, "ytmLatestContainerVersion")
        preview_key = data.get("previewKey", "")

        if not preview_key:
            raise YTMError(
                kind="NoPreviewKey",
                message="Preview-версия создана, но previewKey не получен",
            )

        if site_url:
            sep = "&" if "?" in site_url else "?"
            return f"{site_url}{sep}_ytm_preview={preview_key}"

        return preview_key

    # ============ ПЕРЕХВАТ EVENTLESS DATALAYER ============

    _DL_INTERCEPTOR_CODE = """<script>
(function() {
  window._ytm_dl_cache = {};
  var dl = window.dataLayer = window.dataLayer || [];
  for (var i = 0; i < dl.length; i++) {
    if (typeof dl[i] === 'object' && dl[i] !== null) {
      for (var key in dl[i]) {
        if (key !== 'event' && dl[i].hasOwnProperty(key)) {
          window._ytm_dl_cache[key] = dl[i][key];
        }
      }
    }
  }
  var origPush = dl.push;
  dl.push = function() {
    for (var j = 0; j < arguments.length; j++) {
      var obj = arguments[j];
      if (typeof obj === 'object' && obj !== null) {
        for (var key in obj) {
          if (key !== 'event' && obj.hasOwnProperty(key)) {
            window._ytm_dl_cache[key] = obj[key];
          }
        }
      }
    }
    return origPush.apply(dl, arguments);
  };
})();
</script>"""

    def setup_dl_interceptor(
        self,
        container_id: str,
        tag_name: str = "DL Interceptor",
        trigger_name: str = "Initialization",
    ) -> tuple[Tag, Trigger]:
        """
        Создать перехватчик eventless dataLayer-пушей.

        ЯТМ игнорирует dataLayer.push() без ключа event.
        Этот метод создаёт тег на триггере Initialization (самый ранний),
        который перехватывает ВСЕ пуши (включая eventless) и кэширует
        их значения в window._ytm_dl_cache.

        Затем через create_intercepted_dl_variable() создаются переменные
        типа js_variable, читающие из этого кэша.

        Args:
            container_id: ID контейнера
            tag_name: Название тега-перехватчика
            trigger_name: Название триггера Initialization

        Returns:
            Кортеж (тег, триггер)

        Пример:
            # 1. Установить перехватчик (один раз на контейнер)
            tag, trigger = api.setup_dl_interceptor("70978")

            # 2. Создать переменные для нужных ключей
            api.create_intercepted_dl_variable("70978", "DL - userId", "userId")
            api.create_intercepted_dl_variable("70978", "DL - userType", "userType")

            # 3. Опубликовать
            api.publish("70978")

            # Теперь даже eventless-пуши будут доступны:
            # dataLayer.push({userId: 'user_42'})  // без event!
            # dataLayer.push({event: 'page_view'})
            # {{DL - userId}} === 'user_42' ✅
        """
        trigger = self.create_trigger(
            container_id=container_id,
            name=trigger_name,
            template_id="initialization",
        )

        tag = self.create_tag(
            container_id=container_id,
            name=tag_name,
            html_code=self._DL_INTERCEPTOR_CODE,
            trigger_ids=[trigger.trigger_id],
        )

        return tag, trigger

    def create_intercepted_dl_variable(
        self,
        container_id: str,
        name: str,
        key_name: str,
    ) -> dict:
        """
        Создать переменную, читающую из кэша перехваченных dataLayer-пушей.

        Требует предварительной установки перехватчика через setup_dl_interceptor().
        Создаёт js_variable, читающую window._ytm_dl_cache.{key_name}.

        Args:
            container_id: ID контейнера
            name: Название переменной в ЯТМ
            key_name: Ключ в dataLayer

        Returns:
            Созданная переменная

        Пример:
            api.create_intercepted_dl_variable("70978", "DL - userId", "userId")
        """
        return self.create_js_variable(
            container_id=container_id,
            name=name,
            js_variable_name=f"_ytm_dl_cache.{key_name}",
        )

    def create_intercepted_dl_variables(
        self,
        container_id: str,
        keys_map: dict[str, str],
    ) -> list[dict]:
        """
        Массово создать переменные из кэша перехваченных dataLayer-пушей.

        Args:
            container_id: ID контейнера
            keys_map: Словарь {key_name: variable_name}

        Returns:
            Список созданных переменных

        Пример:
            api.setup_dl_interceptor("70978")
            api.create_intercepted_dl_variables(
                "70978",
                {
                    "userId": "DL - userId",
                    "userType": "DL - userType",
                    "clientId": "DL - clientId",
                },
            )
            api.publish("70978")
        """
        results = []
        for key_name, variable_name in keys_map.items():
            result = self.create_intercepted_dl_variable(
                container_id=container_id,
                name=variable_name,
                key_name=key_name,
            )
            results.append(result)
        return results

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

    # ============ ЭКСПОРТ / ИМПОРТ ============

    def export_container(
        self,
        container_id: str,
        metrika_id: str = "",
    ) -> ContainerExport:
        """
        Экспортировать контейнер в объект ContainerExport.

        Экспортирует все теги, триггеры и кастомные переменные.

        **Ограничение:** API Яндекса не возвращает код тегов (html_code для chtml),
        поэтому экспорт содержит только метаданные. Для полного бэкапа
        храните код тегов отдельно или используйте метод set_tag_code().

        Args:
            container_id: ID контейнера
            metrika_id: ID счётчика Метрики (опционально, для информации)

        Returns:
            ContainerExport с тегами, триггерами и переменными

        Пример:
            export = api.export_container("1080803", "106472777")
            export.save("backup.json")

            # Позже импортировать в другой контейнер:
            export = ContainerExport.load("backup.json")
            api.import_container("NEW_CONTAINER_ID", export)
        """
        # Получаем все теги
        tags = self.get_tags(container_id, limit=1000)

        # Получаем все триггеры
        triggers = self.get_triggers(container_id, limit=1000)

        # Получаем кастомные переменные
        variables = self.get_custom_variables(container_id, limit=1000)

        # Создаём маппинг trigger_id → name
        trigger_id_to_name = {t.trigger_id: t.name for t in triggers}

        # Конвертируем теги в ExportedTag (заменяем trigger_ids на trigger_names)
        exported_tags = []
        for tag in tags:
            trigger_names = [
                trigger_id_to_name.get(tid, f"unknown_{tid}")
                for tid in tag.trigger_ids
            ]
            exported_tags.append(ExportedTag(
                name=tag.name,
                template_id=tag.template_id,
                trigger_names=trigger_names,
                status=tag.status,
                tag_priority=tag.tag_priority,
                html_code=None,  # API не возвращает код
                parameters=[p.to_dict() for p in tag.parameters],
            ))

        # Конвертируем триггеры в ExportedTrigger
        exported_triggers = []
        for trigger in triggers:
            exported_triggers.append(ExportedTrigger(
                name=trigger.name,
                template_id=trigger.template_id,
                activation_conditions=[c.to_dict() for c in trigger.activation_conditions],
                parameters=[p.to_dict() for p in trigger.parameters],
            ))

        # Конвертируем переменные в ExportedVariable
        exported_variables = []
        for var in variables:
            exported_variables.append(ExportedVariable(
                name=var.get("name", ""),
                template_id=var.get("templateId", ""),
                parameters=var.get("templateData", {}).get("parameters", []),
            ))

        return ContainerExport(
            container_id=container_id,
            metrika_id=metrika_id,
            export_date=datetime.now().isoformat(),
            tags=exported_tags,
            triggers=exported_triggers,
            variables=exported_variables,
            trigger_id_to_name=trigger_id_to_name,
        )

    def import_container(
        self,
        container_id: str,
        export: ContainerExport,
        skip_existing: bool = True,
        tag_codes: Optional[dict[str, str]] = None,
    ) -> dict[str, list[str]]:
        """
        Импортировать контейнер из экспорта.

        Создаёт триггеры, затем теги (с правильными связями), затем переменные.

        Args:
            container_id: ID целевого контейнера
            export: Объект ContainerExport для импорта
            skip_existing: Пропускать элементы с такими же именами (по умолчанию True)
            tag_codes: Словарь {tag_name: html_code} с кодом тегов

        Returns:
            Словарь с результатами:
            {
                "triggers_created": ["name1", "name2"],
                "triggers_skipped": ["name3"],
                "tags_created": ["name1"],
                "tags_skipped": ["name2"],
                "variables_created": ["name1"],
                "variables_skipped": [],
                "errors": ["error message 1"],
            }

        Пример:
            # Загрузить экспорт
            export = ContainerExport.load("backup.json")

            # Опционально: добавить код тегов
            tag_codes = {
                "YM Goal - form_submit": "<script>ym(123, 'reachGoal', 'form_submit')</script>",
            }

            # Импортировать
            result = api.import_container("NEW_CONTAINER", export, tag_codes=tag_codes)
            print(f"Created: {len(result['tags_created'])} tags")
        """
        tag_codes = tag_codes or {}
        result = {
            "triggers_created": [],
            "triggers_skipped": [],
            "tags_created": [],
            "tags_skipped": [],
            "variables_created": [],
            "variables_skipped": [],
            "errors": [],
        }

        # Получаем существующие элементы для проверки дубликатов
        existing_triggers = {t.name for t in self.get_triggers(container_id, limit=1000)}
        existing_tags = {t.name for t in self.get_tags(container_id, limit=1000)}
        existing_vars = {v.get("name") for v in self.get_custom_variables(container_id, limit=1000)}

        # 1. Создаём триггеры
        trigger_name_to_id = {}
        for trigger in export.triggers:
            if skip_existing and trigger.name in existing_triggers:
                result["triggers_skipped"].append(trigger.name)
                # Получаем ID существующего триггера
                for t in self.get_triggers(container_id, search=trigger.name, limit=10):
                    if t.name == trigger.name:
                        trigger_name_to_id[trigger.name] = t.trigger_id
                        break
                continue

            try:
                conditions = [
                    ActivationCondition(
                        operator=c.get("operator", "Contains"),
                        is_not=c.get("isNot", False),
                        variable_id=c.get("variableId", ""),
                        target_value=c.get("targetValue", ""),
                    )
                    for c in trigger.activation_conditions
                ]
                parameters = [
                    TemplateParameter(
                        type=p.get("type", ""),
                        parameter_id=p.get("parameterId", ""),
                        value=p.get("value", ""),
                    )
                    for p in trigger.parameters
                ]

                new_trigger = self.create_trigger(
                    container_id=container_id,
                    name=trigger.name,
                    template_id=trigger.template_id,
                    activation_conditions=conditions,
                    parameters=parameters,
                )
                trigger_name_to_id[trigger.name] = new_trigger.trigger_id
                result["triggers_created"].append(trigger.name)
            except Exception as e:
                result["errors"].append(f"Trigger '{trigger.name}': {e}")

        # Дополняем маппинг существующими триггерами
        for t in self.get_triggers(container_id, limit=1000):
            if t.name not in trigger_name_to_id:
                trigger_name_to_id[t.name] = t.trigger_id

        # 2. Создаём теги
        for tag in export.tags:
            if skip_existing and tag.name in existing_tags:
                result["tags_skipped"].append(tag.name)
                continue

            try:
                # Преобразуем trigger_names в trigger_ids
                trigger_ids = []
                for tname in tag.trigger_names:
                    if tname in trigger_name_to_id:
                        trigger_ids.append(trigger_name_to_id[tname])
                    else:
                        result["errors"].append(f"Tag '{tag.name}': trigger '{tname}' not found")

                # Получаем код тега
                html_code = tag_codes.get(tag.name) or tag.html_code

                # Формируем параметры
                if html_code and tag.template_id == "chtml":
                    parameters = [
                        TemplateParameter(type="Code", parameter_id="0", value=html_code)
                    ]
                else:
                    parameters = [
                        TemplateParameter(
                            type=p.get("type", ""),
                            parameter_id=p.get("parameterId", ""),
                            value=p.get("value", ""),
                        )
                        for p in tag.parameters
                    ] if tag.parameters else None

                self.create_tag(
                    container_id=container_id,
                    name=tag.name,
                    template_id=tag.template_id,
                    trigger_ids=trigger_ids,
                    tag_priority=tag.tag_priority,
                    parameters=parameters,
                )
                result["tags_created"].append(tag.name)
            except Exception as e:
                result["errors"].append(f"Tag '{tag.name}': {e}")

        # 3. Создаём переменные
        for var in export.variables:
            if skip_existing and var.name in existing_vars:
                result["variables_skipped"].append(var.name)
                continue

            try:
                parameters = [
                    TemplateParameter(
                        type=p.get("type", ""),
                        parameter_id=p.get("parameterId", ""),
                        value=p.get("value", ""),
                    )
                    for p in var.parameters
                ]

                self.create_variable(
                    container_id=container_id,
                    name=var.name,
                    template_id=var.template_id,
                    parameters=parameters,
                )
                result["variables_created"].append(var.name)
            except Exception as e:
                result["errors"].append(f"Variable '{var.name}': {e}")

        return result
