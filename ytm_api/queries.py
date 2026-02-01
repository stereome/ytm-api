"""
GraphQL запросы для Yandex Tag Manager API
"""

# Общие фрагменты
FRAGMENT_API_ERROR = """
fragment apiErrorReason on ApiErrorReason { kind message location }
fragment apiError on ApiError { kind reason { ...apiErrorReason } }
"""

FRAGMENT_DATE_TIME = """
fragment dateTimeDto on DateTimeDto { day month year apiFormat hours minutes seconds }
"""

FRAGMENT_DATE = """
fragment dateDto on DateDto { day month year apiFormat }
"""

FRAGMENT_TEMPLATE_PARAMETER = """
fragment ytmTemplateItemParameter on YtmTemplateItemParameter {
    type parameterId value rawValue
    tableValue { ...ytmTableTemplateData }
}
fragment ytmTableTemplateData on YtmTableTemplateData { rows { ...ytmTableTemplateRow } }
fragment ytmTableTemplateRow on YtmTableTemplateRow { columns { ...ytmTableTemplateColumn } }
fragment ytmTableTemplateColumn on YtmTableTemplateColumn { columnNumber value rawValue }
"""

FRAGMENT_TRIGGER_CONDITION = """
fragment ytmTriggerActivationCondition on YtmTriggerActivationCondition {
    operator isNot variableId targetValue
}
"""

# ============ ТЕГИ ============

# Список тегов
QUERY_TAGS_LIST = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + """
fragment ytmTag on YtmTag {
    tagId originalTagId name type status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    triggerIds templateId templateVersion updatedBy
}
fragment ytmTagsList on YtmTagsList { tags { ...ytmTag } total }

query ytmTags2($containerId: String!, $offset: Int, $limit: Int, $search: String, $ids: [String!]) {
    ytmTags2(containerId: $containerId, offset: $offset, limit: $limit, search: $search, ids: $ids) {
        data { ...ytmTagsList }
        error { ...apiError }
    }
}
"""
)

# Создание тега
MUTATION_CREATE_TAG = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TEMPLATE_PARAMETER
    + """
fragment ytmTagDetailed on YtmTagDetailed {
    tagId originalTagId name type status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    triggerIds templateId templateVersion updatedBy
    parameters { ...ytmTemplateItemParameter }
}

mutation createYtmTag($containerId: String!, $tag: YtmTagInput!) {
    createYtmTag(containerId: $containerId, tag: $tag) {
        data { ...ytmTagDetailed }
        error { ...apiError }
    }
}
"""
)

# Обновление тега
MUTATION_EDIT_TAG = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TEMPLATE_PARAMETER
    + """
fragment ytmTagDetailed on YtmTagDetailed {
    tagId originalTagId name type status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    triggerIds templateId templateVersion updatedBy
    parameters { ...ytmTemplateItemParameter }
}

mutation editYtmTag($containerId: String!, $tagId: String!, $tag: YtmTagInput!) {
    editYtmTag(containerId: $containerId, tagId: $tagId, tag: $tag) {
        data { ...ytmTagDetailed }
        error { ...apiError }
    }
}
"""
)

# Удаление тега
MUTATION_DELETE_TAG = (
    FRAGMENT_API_ERROR
    + """
mutation deleteYtmTag($containerId: String!, $tagId: String!) {
    deleteYtmTag(containerId: $containerId, tagId: $tagId) {
        data
        error { ...apiError }
    }
}
"""
)

# ============ ТРИГГЕРЫ ============

# Список триггеров
QUERY_TRIGGERS_LIST = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TRIGGER_CONDITION
    + """
fragment ytmTrigger on YtmTrigger {
    triggerId originalTriggerId name type status linksNumber
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    templateId templateVersion updatedBy
    activationConditions { ...ytmTriggerActivationCondition }
}
fragment ytmTriggersList on YtmTriggersList { triggers { ...ytmTrigger } total }

query ytmTriggers2($containerId: String!, $offset: Int, $limit: Int, $search: String, $ids: [String!]) {
    ytmTriggers2(containerId: $containerId, offset: $offset, limit: $limit, search: $search, ids: $ids) {
        data { ...ytmTriggersList }
        error { ...apiError }
    }
}
"""
)

# Создание триггера
MUTATION_CREATE_TRIGGER = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TRIGGER_CONDITION
    + FRAGMENT_TEMPLATE_PARAMETER
    + """
fragment ytmTriggerDetailed on YtmTriggerDetailed {
    triggerId originalTriggerId name type status linksNumber
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    templateId templateVersion updatedBy
    activationConditions { ...ytmTriggerActivationCondition }
    tagIds
    parameters { ...ytmTemplateItemParameter }
}

mutation createYtmTrigger($containerId: String!, $trigger: YtmTriggerInput!) {
    createYtmTrigger(containerId: $containerId, trigger: $trigger) {
        data { ...ytmTriggerDetailed }
        error { ...apiError }
    }
}
"""
)

# Удаление триггера
MUTATION_DELETE_TRIGGER = (
    FRAGMENT_API_ERROR
    + """
mutation deleteYtmTrigger($containerId: String!, $triggerId: String!) {
    deleteYtmTrigger(containerId: $containerId, triggerId: $triggerId) {
        data
        error { ...apiError }
    }
}
"""
)

# ============ ШАБЛОНЫ ============

# Список доступных шаблонов
QUERY_AVAILABLE_TEMPLATES = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE
    + """
fragment ytmTemplateBase on YtmTemplateBase {
    containerId templateId name author type definitionType publicity
    variableTemplateType triggerTemplateType tagTemplateType
    templateVersion hasPublishedVersion isHidden versionStatus
    moderationStatus moderationRequestId moderationRejectReason
    versionUpdated { ...dateDto }
    description documentationLink mainPageLink email changes status linksNumber
    created { ...dateDto }
    updated { ...dateDto }
}
fragment ytmTemplatesList on YtmTemplatesList { total templates { ...ytmTemplateBase } }

query ytmAvailableTemplates(
    $containerId: String!
    $sources: [YtmTemplateSource!]
    $templateType: YtmTemplateType
    $offset: Int
    $limit: Int
    $search: String
) {
    ytmAvailableTemplates(
        containerId: $containerId
        sources: $sources
        templateType: $templateType
        offset: $offset
        limit: $limit
        search: $search
    ) {
        data { ...ytmTemplatesList }
        error { ...apiError }
    }
}
"""
)

# ============ ПЕРЕМЕННЫЕ ============

# Список встроенных переменных (для подстановки в теги)
QUERY_VARIABLES_SUGGEST = (
    FRAGMENT_API_ERROR
    + """
query ytmVariablesSuggest($containerId: String!) {
    ytmVariablesSuggest(containerId: $containerId) {
        data {
            variableId
            originalVariableId
            name
            category
        }
        error { ...apiError }
    }
}
"""
)

# Список кастомных переменных
QUERY_CUSTOM_VARIABLES_LIST = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + """
fragment ytmVariable on YtmVariable {
    variableId originalVariableId name templateType variableType status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    category linksNumber templateId templateVersion updatedBy
}
fragment ytmVariablesList on YtmVariablesList { variables { ...ytmVariable } total }

query ytmVariables2(
    $containerId: String!
    $variableType: YtmVariableType
    $offset: Int
    $limit: Int
    $search: String
    $ids: [String!]
) {
    ytmVariables2(
        containerId: $containerId
        variableType: $variableType
        offset: $offset
        limit: $limit
        search: $search
        ids: $ids
    ) {
        data { ...ytmVariablesList }
        error { ...apiError }
    }
}
"""
)

# Создание кастомной переменной
MUTATION_CREATE_VARIABLE = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TEMPLATE_PARAMETER
    + """
fragment ytmVariableDetailed on YtmVariableDetailed {
    variableId originalVariableId name templateType variableType status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    category linksNumber templateId templateVersion updatedBy
    tagIds triggerIds variableIds
    parameters { ...ytmTemplateItemParameter }
    dataType
}

mutation createYtmVariable($containerId: String!, $variable: YtmVariableInput!) {
    createYtmVariable(containerId: $containerId, variable: $variable) {
        data { ...ytmVariableDetailed }
        error { ...apiError }
    }
}
"""
)

# Удаление кастомной переменной
MUTATION_DELETE_VARIABLE = (
    FRAGMENT_API_ERROR
    + """
mutation deleteYtmVariable($containerId: String!, $variableId: String!) {
    deleteYtmVariable(containerId: $containerId, variableId: $variableId) {
        data
        error { ...apiError }
    }
}
"""
)

# ============ ПУБЛИКАЦИЯ ============

# Changelog перед публикацией
QUERY_VERSION_CHANGELOG = (
    FRAGMENT_API_ERROR
    + FRAGMENT_DATE_TIME
    + FRAGMENT_TRIGGER_CONDITION
    + FRAGMENT_TEMPLATE_PARAMETER
    + """
fragment ytmTagDetailed on YtmTagDetailed {
    tagId originalTagId name type status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    triggerIds templateId templateVersion updatedBy
    parameters { ...ytmTemplateItemParameter }
}
fragment ytmTriggerDetailed on YtmTriggerDetailed {
    triggerId originalTriggerId name type status linksNumber
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    templateId templateVersion updatedBy
    activationConditions { ...ytmTriggerActivationCondition }
    tagIds
    parameters { ...ytmTemplateItemParameter }
}
fragment ytmVariableDetailed on YtmVariableDetailed {
    variableId originalVariableId name templateType variableType status
    created { ...dateTimeDto }
    updated { ...dateTimeDto }
    category linksNumber templateId templateVersion updatedBy
    tagIds triggerIds variableIds
    parameters { ...ytmTemplateItemParameter }
    dataType
}
fragment ytmContainerVersionDetailed on YtmContainerVersionDetailed {
    version name description status
    creationDate { ...dateTimeDto }
    updated { ...dateTimeDto }
    activationDate { ...dateTimeDto }
    activatedBy errorMessage previewKey
    tags { ...ytmTagDetailed }
    triggers { ...ytmTriggerDetailed }
    variables { ...ytmVariableDetailed }
}
fragment ytmContainerVersionChangelog on YtmContainerVersionChangelog {
    version1 { ...ytmContainerVersionDetailed }
    version2 { ...ytmContainerVersionDetailed }
}

query ytmContainerVersionChangelog($containerId: String!, $version1: Int, $version2: Int) {
    ytmContainerVersionChangelog(containerId: $containerId, version1: $version1, version2: $version2) {
        data { ...ytmContainerVersionChangelog }
        error { ...apiError }
    }
}
"""
)

# Публикация версии
MUTATION_PUBLISH_VERSION = (
    FRAGMENT_API_ERROR
    + """
mutation publishYtmVersion($containerId: String!, $isPreview: Boolean, $input: YtmPublishVersionInput) {
    publishYtmVersion(containerId: $containerId, isPreview: $isPreview, input: $input) {
        data
        error { ...apiError }
    }
}
"""
)
