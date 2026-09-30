#!/usr/bin/env python3
"""
Утилита для генерации кода тегов при импорте в другой счётчик Метрики.

Использование:
    python generate_tag_codes.py 123456789

Где 123456789 - ID нового счётчика Метрики.
"""

import sys
import json

def generate_tag_codes(metrika_id: str, export_path: str = "../exports/dinamika_ytm_export.json") -> dict[str, str]:
    """
    Генерирует код для всех тегов с новым ID счётчика Метрики.

    Args:
        metrika_id: ID нового счётчика Метрики
        export_path: Путь к файлу экспорта

    Returns:
        Словарь {tag_name: html_code}
    """
    with open(export_path, 'r', encoding='utf-8') as f:
        export = json.load(f)

    tag_codes = {}

    for tag in export['tags']:
        name = tag['name']

        # Извлекаем имя цели из названия тега
        # "YM Goal - form_submit" → "form_submit"
        if name.startswith("YM Goal - "):
            goal_name = name.replace("YM Goal - ", "")
            tag_codes[name] = f"<script>ym({metrika_id}, 'reachGoal', '{goal_name}')</script>"
        elif tag.get('htmlCode'):
            # Заменяем старый ID на новый в существующем коде
            old_code = tag['htmlCode']
            # Простая замена ID метрики
            new_code = old_code
            for old_id in ['106472777']:  # Список известных старых ID
                new_code = new_code.replace(old_id, metrika_id)
            tag_codes[name] = new_code

    return tag_codes


def main():
    if len(sys.argv) < 2:
        print("Использование: python generate_tag_codes.py <METRIKA_ID>")
        print("Пример: python generate_tag_codes.py 123456789")
        sys.exit(1)

    metrika_id = sys.argv[1]

    print(f"Генерация кода тегов для счётчика {metrika_id}...")
    print()

    tag_codes = generate_tag_codes(metrika_id)

    print("tag_codes = {")
    for name, code in tag_codes.items():
        print(f'    "{name}": "{code}",')
    print("}")

    print()
    print("# Использование при импорте:")
    print("# result = api.import_container(container_id, export, tag_codes=tag_codes)")


if __name__ == "__main__":
    main()
