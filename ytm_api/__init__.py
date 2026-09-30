"""
Yandex Tag Manager API - Неофициальный Python SDK

Reverse-engineered API для программного управления Яндекс Тег Менеджером.
"""

from .client import YandexTagManagerAPI, YTMError
from .models import (
    # Модели данных
    Tag,
    Trigger,
    Template,
    Variable,
    TemplateParameter,
    ActivationCondition,
    # Экспорт/Импорт
    ContainerExport,
    ExportedTag,
    ExportedTrigger,
    ExportedVariable,
    # Шаблоны
    TagTemplates,
    TriggerTemplates,
    VariableTemplates,
    # Константы
    ConditionOperators,
    BuiltInVariables,
)

__version__ = "0.1.0"
__all__ = [
    # Клиент
    "YandexTagManagerAPI",
    "YTMError",
    # Модели
    "Tag",
    "Trigger",
    "Template",
    "Variable",
    "TemplateParameter",
    "ActivationCondition",
    # Экспорт/Импорт
    "ContainerExport",
    "ExportedTag",
    "ExportedTrigger",
    "ExportedVariable",
    # Шаблоны
    "TagTemplates",
    "TriggerTemplates",
    "VariableTemplates",
    # Константы
    "ConditionOperators",
    "BuiltInVariables",
]
