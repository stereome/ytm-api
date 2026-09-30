"""
Настройка YTM тегов для целей dinamikapro.ru

Этот скрипт создаёт триггеры и теги для отслеживания целей на сайте.
Цели привязаны к элементам с data-goal атрибутами.

Перед запуском:
1. Открой https://metrika.yandex.ru в браузере
2. Войди в свой аккаунт
3. Открой YTM для счётчика 106472777
4. В DevTools → Network найди запрос к api/metrika
5. Скопируй данные из Headers и Cookies (см. README)
"""

import sys
sys.path.insert(0, '..')

from ytm_api import YandexTagManagerAPI
from ytm_api.models import ActivationCondition, TemplateParameter


# ============ НАСТРОЙКИ ============

# Данные авторизации (из DevTools браузера)
SESSION_ID = "..."  # Cookie Session_id
CSRF_TOKEN = "..."  # Header x-csrf-token
UID = "..."  # Header x-uid

# ВАЖНО: Container ID ≠ ID счётчика Метрики!
# Container ID: 1080803 (из Payload запроса к api/metrika)
# Metrika ID: 106472777 (ID счётчика в URL)
CONTAINER_ID = "1080803"
METRIKA_ID = "106472777"


# Цели для отслеживания через YTM
# Элементы на сайте помечены атрибутами data-goal="<goal_name>"
CLICK_GOALS = [
    ("click_cta_header", "Click - CTA Header"),
    ("click_cta_hero", "Click - CTA Hero"),
    ("click_cta_team", "Click - CTA Team"),
    ("click_cta_howtostart", "Click - CTA How To Start"),
    ("click_cta_early", "Click - CTA Early Adopters"),
    ("click_cta_resources", "Click - CTA Resources"),
    ("click_email", "Click - Email"),
    ("click_telegram", "Click - Telegram"),
    ("click_whatsapp", "Click - WhatsApp"),
]


def create_ym_goal_html(goal_name: str) -> str:
    """Генерирует HTML код для отправки цели в Яндекс Метрику"""
    return f"""<script>
    if (typeof ym !== 'undefined') {{
        ym({METRIKA_ID}, 'reachGoal', '{goal_name}');
        console.log('[YTM] Goal sent: {goal_name}');
    }}
</script>"""


def main():
    # Создаём клиент
    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    print("=" * 60)
    print("Настройка целей для dinamikapro.ru")
    print(f"Container ID: {CONTAINER_ID}")
    print(f"Metrika ID: {METRIKA_ID}")
    print("=" * 60)

    # ============ ПОЛУЧАЕМ ТЕКУЩИЕ ТЕГИ И ТРИГГЕРЫ ============

    print("\n1. Получаем текущие теги и триггеры...")

    existing_tags = api.get_tags(CONTAINER_ID)
    existing_triggers = api.get_triggers(CONTAINER_ID)

    print(f"   Найдено тегов: {len(existing_tags)}")
    print(f"   Найдено триггеров: {len(existing_triggers)}")

    # Показываем существующие
    if existing_tags:
        print("\n   Существующие теги:")
        for tag in existing_tags:
            print(f"     [{tag.tag_id}] {tag.name}")

    if existing_triggers:
        print("\n   Существующие триггеры:")
        for trigger in existing_triggers:
            print(f"     [{trigger.trigger_id}] {trigger.name}")

    # ============ УДАЛЯЕМ СТАРЫЙ ТЕГ click_cta ============

    print("\n2. Проверяем и удаляем старый тег click_cta...")

    old_tag = None
    old_trigger = None

    for tag in existing_tags:
        if tag.name == "YM Goal - click_cta":
            old_tag = tag
            break

    for trigger in existing_triggers:
        if trigger.name == "Click - CTA Demo":
            old_trigger = trigger
            break

    if old_tag:
        api.delete_tag(CONTAINER_ID, old_tag.tag_id)
        print(f"   Удалён тег: {old_tag.name} [{old_tag.tag_id}]")

    if old_trigger:
        api.delete_trigger(CONTAINER_ID, old_trigger.trigger_id)
        print(f"   Удалён триггер: {old_trigger.name} [{old_trigger.trigger_id}]")

    if not old_tag and not old_trigger:
        print("   Старых тегов click_cta не найдено")

    # ============ СОЗДАЁМ НОВЫЕ ТРИГГЕРЫ И ТЕГИ ============

    print("\n3. Создаём триггеры и теги для целей...")

    created_items = []

    for goal_name, trigger_name in CLICK_GOALS:
        tag_name = f"YM Goal - {goal_name}"

        # Проверяем, существует ли уже
        exists = any(t.name == tag_name for t in existing_tags)
        if exists:
            print(f"   [SKIP] {tag_name} уже существует")
            continue

        # Создаём триггер клика с условием data-goal
        # Условие: Click Element содержит атрибут data-goal с нужным значением
        trigger = api.create_trigger(
            container_id=CONTAINER_ID,
            name=trigger_name,
            template_id="click",  # Клик по всем элементам
            activation_conditions=[
                ActivationCondition(
                    operator="Contains",  # Важно: с большой буквы!
                    is_not=False,
                    variable_id="click_element",  # Элемент клика
                    target_value=f'data-goal="{goal_name}"',
                ),
            ],
        )

        # Создаём HTML тег для отправки цели
        html_code = create_ym_goal_html(goal_name)

        tag = api.create_tag(
            container_id=CONTAINER_ID,
            name=tag_name,
            html_code=html_code,
            trigger_ids=[trigger.trigger_id],
        )

        print(f"   [OK] {tag_name}")
        print(f"        Триггер: {trigger.name} [{trigger.trigger_id}]")
        print(f"        Тег: {tag.name} [{tag.tag_id}]")

        created_items.append((goal_name, trigger, tag))

    # ============ СОЗДАЁМ ТРИГГЕР ДЛЯ ОТПРАВКИ ФОРМЫ ============

    print("\n4. Создаём триггер для form_submit...")

    form_tag_name = "YM Goal - form_submit"
    form_exists = any(t.name == form_tag_name for t in existing_tags)

    if form_exists:
        print(f"   [SKIP] {form_tag_name} уже существует")
    else:
        # Триггер отправки формы с условием data-goal
        form_trigger = api.create_trigger(
            container_id=CONTAINER_ID,
            name="Form Submit - Contact",
            template_id="form_submit",
            activation_conditions=[
                ActivationCondition(
                    operator="Contains",
                    is_not=False,
                    variable_id="form_element",
                    target_value='data-goal="form_submit"',
                ),
            ],
        )

        form_html = create_ym_goal_html("form_submit")

        form_tag = api.create_tag(
            container_id=CONTAINER_ID,
            name=form_tag_name,
            html_code=form_html,
            trigger_ids=[form_trigger.trigger_id],
        )

        print(f"   [OK] {form_tag_name}")
        print(f"        Триггер: {form_trigger.name} [{form_trigger.trigger_id}]")
        print(f"        Тег: {form_tag.name} [{form_tag.tag_id}]")

    # ============ ПУБЛИКАЦИЯ ============

    print("\n5. Проверяем изменения для публикации...")

    changelog = api.get_changelog(CONTAINER_ID)
    v2 = changelog.get("version2", {})

    if v2:
        tags_changed = v2.get("tags", [])
        triggers_changed = v2.get("triggers", [])

        if tags_changed or triggers_changed:
            print(f"   Тегов изменено: {len(tags_changed)}")
            print(f"   Триггеров изменено: {len(triggers_changed)}")

            for tag in tags_changed:
                print(f"     - Тег: {tag.get('name')} ({tag.get('status')})")

            for trigger in triggers_changed:
                print(f"     - Триггер: {trigger.get('name')} ({trigger.get('status')})")

            # Публикуем
            print("\n6. Публикуем изменения...")
            api.publish(
                container_id=CONTAINER_ID,
                name="CTA Goals Setup",
                description="Настройка целей для отслеживания CTA кликов и отправки формы",
            )
            print("   [OK] Контейнер опубликован!")
        else:
            print("   Нет изменений для публикации")

    print("\n" + "=" * 60)
    print("Готово!")
    print("=" * 60)


def list_current_state():
    """Показать текущее состояние контейнера"""
    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    print("=" * 60)
    print("ТЕКУЩЕЕ СОСТОЯНИЕ КОНТЕЙНЕРА")
    print("=" * 60)

    print("\nТЕГИ:")
    tags = api.get_tags(CONTAINER_ID)
    for tag in tags:
        print(f"  [{tag.tag_id}] {tag.name}")
        print(f"       Status: {tag.status}")
        print(f"       Triggers: {tag.trigger_ids}")
        print()

    print("\nТРИГГЕРЫ:")
    triggers = api.get_triggers(CONTAINER_ID)
    for trigger in triggers:
        print(f"  [{trigger.trigger_id}] {trigger.name}")
        print(f"       Template: {trigger.template_id}")
        print(f"       Conditions: {len(trigger.activation_conditions)}")
        print()


if __name__ == "__main__":
    # Раскомментируй нужную функцию:

    # Показать текущее состояние:
    # list_current_state()

    # Создать теги и триггеры:
    main()
