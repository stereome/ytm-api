#!/usr/bin/env python3
"""
Пример экспорта и импорта контейнера YTM.

Workflow:
1. Экспортировать контейнер из одного счётчика
2. Сгенерировать код тегов для нового счётчика
3. Импортировать в новый контейнер
4. Опубликовать
"""

import sys
sys.path.insert(0, "..")

from ytm_api import YandexTagManagerAPI, ContainerExport
from generate_tag_codes import generate_tag_codes

# ============ CREDENTIALS ============
# Получить из DevTools браузера (см. README.md)

SESSION_ID = "..."  # Cookie Session_id
CSRF_TOKEN = "..."  # Header x-csrf-token
UID = "..."         # Header x-uid

# ============ CONTAINERS ============

# Источник (откуда экспортируем)
SOURCE_CONTAINER = "1080803"
SOURCE_METRIKA = "106472777"

# Цель (куда импортируем)
TARGET_CONTAINER = "NEW_CONTAINER_ID"  # Найти в DevTools
TARGET_METRIKA = "NEW_METRIKA_ID"      # ID нового счётчика


def export_container():
    """Шаг 1: Экспортировать контейнер"""
    print("=" * 50)
    print("ЭКСПОРТ КОНТЕЙНЕРА")
    print("=" * 50)

    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    export = api.export_container(
        container_id=SOURCE_CONTAINER,
        metrika_id=SOURCE_METRIKA,
    )

    # Сохраняем
    export_path = "../exports/dinamika_ytm_export.json"
    export.save(export_path)

    print(f"Экспортировано в: {export_path}")
    print(f"  Теги: {len(export.tags)}")
    print(f"  Триггеры: {len(export.triggers)}")
    print(f"  Переменные: {len(export.variables)}")

    return export


def import_container(target_metrika_id: str):
    """Шаг 2-4: Импортировать в новый контейнер"""
    print("\n" + "=" * 50)
    print("ИМПОРТ КОНТЕЙНЕРА")
    print("=" * 50)

    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    # Загружаем экспорт
    export = ContainerExport.load("../exports/dinamika_ytm_export.json")
    print(f"Загружено из файла:")
    print(f"  Дата экспорта: {export.export_date}")
    print(f"  Теги: {len(export.tags)}")
    print(f"  Триггеры: {len(export.triggers)}")

    # Генерируем код тегов для нового счётчика
    tag_codes = generate_tag_codes(target_metrika_id)
    print(f"\nСгенерировано {len(tag_codes)} кодов тегов для счётчика {target_metrika_id}")

    # Импортируем
    print(f"\nИмпортируем в контейнер {TARGET_CONTAINER}...")
    result = api.import_container(
        container_id=TARGET_CONTAINER,
        export=export,
        skip_existing=True,
        tag_codes=tag_codes,
    )

    print("\nРезультат:")
    print(f"  Триггеры создано: {len(result['triggers_created'])}")
    print(f"  Триггеры пропущено: {len(result['triggers_skipped'])}")
    print(f"  Теги создано: {len(result['tags_created'])}")
    print(f"  Теги пропущено: {len(result['tags_skipped'])}")

    if result["errors"]:
        print(f"\nОшибки ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  - {error}")
        return False

    # Публикуем
    print("\nПубликация...")
    api.publish(
        container_id=TARGET_CONTAINER,
        name="Imported from backup",
        description=f"Импортировано из контейнера {SOURCE_CONTAINER}",
    )
    print("Опубликовано!")

    return True


def show_export_contents():
    """Показать содержимое экспорта без импорта"""
    export = ContainerExport.load("../exports/dinamika_ytm_export.json")

    print("=" * 50)
    print("СОДЕРЖИМОЕ ЭКСПОРТА")
    print("=" * 50)
    print(f"Контейнер: {export.container_id}")
    print(f"Метрика: {export.metrika_id}")
    print(f"Дата: {export.export_date}")

    print("\nТеги:")
    for tag in export.tags:
        triggers = ", ".join(tag.trigger_names)
        code_preview = (tag.html_code[:50] + "...") if tag.html_code and len(tag.html_code) > 50 else tag.html_code
        print(f"  • {tag.name}")
        print(f"    Триггеры: {triggers}")
        print(f"    Код: {code_preview}")

    print("\nТриггеры:")
    for trigger in export.triggers:
        conditions = []
        for c in trigger.activation_conditions:
            conditions.append(f"{c.get('variableId')} {c.get('operator')} '{c.get('targetValue')}'")

        print(f"  • {trigger.name} ({trigger.template_id})")
        if conditions:
            print(f"    Условия: {', '.join(conditions)}")
        if trigger.parameters:
            for p in trigger.parameters:
                print(f"    Параметр: {p.get('parameterId')} = {p.get('value')}")


if __name__ == "__main__":
    # Показать содержимое экспорта (не требует credentials)
    show_export_contents()

    # Для экспорта/импорта раскомментировать и заполнить credentials:
    # export_container()
    # import_container(TARGET_METRIKA)
