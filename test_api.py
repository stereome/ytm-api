#!/usr/bin/env python3
"""
Быстрый тест API — проверяет что credentials работают
"""

import sys
sys.path.insert(0, '.')

from ytm_api import YandexTagManagerAPI

try:
    from config import SESSION_ID, CSRF_TOKEN, UID, CONTAINER_ID
except ImportError:
    print("Ошибка: скопируй config.example.py в config.py и заполни данными")
    sys.exit(1)


def main():
    print("Инициализация API...")
    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    print(f"\nКонтейнер: {CONTAINER_ID}")
    print("=" * 50)

    # Тест 1: Список тегов
    print("\n📋 Список тегов:")
    try:
        tags = api.get_tags(CONTAINER_ID)
        print(f"   Найдено: {len(tags)} тегов")
        for tag in tags[:5]:  # Первые 5
            print(f"   - [{tag.tag_id}] {tag.name}")
        if len(tags) > 5:
            print(f"   ... и ещё {len(tags) - 5}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return

    # Тест 2: Список триггеров
    print("\n🎯 Список триггеров:")
    try:
        triggers = api.get_triggers(CONTAINER_ID)
        print(f"   Найдено: {len(triggers)} триггеров")
        for trigger in triggers[:5]:
            print(f"   - [{trigger.trigger_id}] {trigger.name} ({trigger.template_id})")
        if len(triggers) > 5:
            print(f"   ... и ещё {len(triggers) - 5}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # Тест 3: Переменные
    print("\n📊 Доступные переменные:")
    try:
        variables = api.get_variables(CONTAINER_ID)
        print(f"   Найдено: {len(variables)} переменных")
        categories = set(v.category for v in variables)
        print(f"   Категории: {', '.join(categories)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    # Тест 4: Шаблоны
    print("\n📦 Шаблоны тегов:")
    try:
        templates = api.get_templates(CONTAINER_ID, template_type="Tag")
        print(f"   Найдено: {len(templates)} шаблонов")
        for tmpl in templates[:3]:
            print(f"   - {tmpl.name} ({tmpl.template_id})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

    print("\n" + "=" * 50)
    print("✅ API работает!")
    print("\nТеперь можно использовать:")
    print("  api.create_tag(...)")
    print("  api.create_trigger(...)")
    print("  api.publish(...)")


if __name__ == "__main__":
    main()
