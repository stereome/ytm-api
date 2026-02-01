"""
Примеры использования Yandex Tag Manager API

Перед запуском:
1. Открой https://metrika.yandex.ru в браузере
2. Войди в свой аккаунт
3. Открой DevTools → Network
4. Найди любой запрос к api/metrika
5. Скопируй нужные данные из Headers и Cookies
"""

import sys
sys.path.insert(0, '..')

from ytm_api import YandexTagManagerAPI
from ytm_api.models import TriggerTemplates, TagTemplates, ActivationCondition


# ============ НАСТРОЙКИ ============

# Данные авторизации (из DevTools браузера)
SESSION_ID = "3:1769918318.5.2..."  # Cookie Session_id
CSRF_TOKEN = "8980da54d11975764818941ad58f1588"  # Header x-csrf-token
UID = "1153393446"  # Header x-uid

# ID контейнера (из URL: /ytm/overview?id=XXXXX)
CONTAINER_ID = "70978"


def main():
    # Создаём клиент
    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    # ============ ПОЛУЧЕНИЕ ДАННЫХ ============

    print("=" * 50)
    print("СПИСОК ТЕГОВ")
    print("=" * 50)

    tags = api.get_tags(CONTAINER_ID)
    for tag in tags:
        print(f"  [{tag.tag_id}] {tag.name} ({tag.status})")
        print(f"       Шаблон: {tag.template_id}")
        print(f"       Триггеры: {tag.trigger_ids}")
        print()

    print("=" * 50)
    print("СПИСОК ТРИГГЕРОВ")
    print("=" * 50)

    triggers = api.get_triggers(CONTAINER_ID)
    for trigger in triggers:
        print(f"  [{trigger.trigger_id}] {trigger.name} ({trigger.status})")
        print(f"       Шаблон: {trigger.template_id}")
        print()

    print("=" * 50)
    print("ДОСТУПНЫЕ ПЕРЕМЕННЫЕ")
    print("=" * 50)

    variables = api.get_variables(CONTAINER_ID)
    by_category = {}
    for var in variables:
        by_category.setdefault(var.category, []).append(var)

    for category, vars in by_category.items():
        print(f"  {category}:")
        for v in vars:
            print(f"    - {v.name} ({{{{ {v.variable_id} }}}})")
        print()

    # ============ СОЗДАНИЕ ТЕГА ============

    print("=" * 50)
    print("СОЗДАНИЕ ТЕГА")
    print("=" * 50)

    # Пример 1: Простой HTML тег
    html_code = """<script>
    console.log('YTM Tag fired!');
    console.log('Page URL:', window.location.href);
</script>"""

    # Находим триггер "Все страницы" или создаём новый
    all_pages_trigger = None
    for trigger in triggers:
        if trigger.template_id == "page_view":
            all_pages_trigger = trigger
            break

    if all_pages_trigger:
        trigger_id = all_pages_trigger.trigger_id
        print(f"  Используем существующий триггер: {all_pages_trigger.name}")
    else:
        # Создаём триггер
        new_trigger = api.create_trigger(
            container_id=CONTAINER_ID,
            name="All Pages (API)",
            template_id=TriggerTemplates.PAGE_VIEW,
        )
        trigger_id = new_trigger.trigger_id
        print(f"  Создан триггер: {new_trigger.name} [{new_trigger.trigger_id}]")

    # Создаём тег
    new_tag = api.create_tag(
        container_id=CONTAINER_ID,
        name="Console Log (API Test)",
        template_id=TagTemplates.CUSTOM_HTML,
        html_code=html_code,
        trigger_ids=[trigger_id],
    )
    print(f"  Создан тег: {new_tag.name} [{new_tag.tag_id}]")

    # ============ ОБНОВЛЕНИЕ ТЕГА ============

    print("=" * 50)
    print("ОБНОВЛЕНИЕ ТЕГА")
    print("=" * 50)

    updated_html = """<script>
    console.log('YTM Tag UPDATED via API!');
    console.log('Timestamp:', new Date().toISOString());
</script>"""

    updated_tag = api.update_tag(
        container_id=CONTAINER_ID,
        tag_id=new_tag.tag_id,
        html_code=updated_html,
    )
    print(f"  Обновлён тег: {updated_tag.name}")

    # ============ ПУБЛИКАЦИЯ ============

    print("=" * 50)
    print("ПУБЛИКАЦИЯ")
    print("=" * 50)

    # Смотрим changelog
    changelog = api.get_changelog(CONTAINER_ID)
    print("  Изменения для публикации:")

    v2 = changelog.get("version2", {})
    if v2:
        for tag in v2.get("tags", []):
            print(f"    - Тег: {tag.get('name')} ({tag.get('status')})")
        for trigger in v2.get("triggers", []):
            print(f"    - Триггер: {trigger.get('name')} ({trigger.get('status')})")

    # Публикуем (раскомментируй для реальной публикации)
    # api.publish(
    #     container_id=CONTAINER_ID,
    #     name="API Test Publish",
    #     description="Тестовая публикация через API",
    # )
    # print("  Опубликовано!")

    # ============ УДАЛЕНИЕ ============

    print("=" * 50)
    print("УДАЛЕНИЕ (опционально)")
    print("=" * 50)

    # Раскомментируй для удаления созданного тега
    # api.delete_tag(CONTAINER_ID, new_tag.tag_id)
    # print(f"  Удалён тег: {new_tag.tag_id}")


def example_create_with_conditions():
    """Пример создания триггера с условиями"""

    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    # Триггер: клик по ссылке, содержащей "download"
    trigger = api.create_trigger(
        container_id=CONTAINER_ID,
        name="Download Link Click",
        template_id=TriggerTemplates.LINK_CLICK,
        activation_conditions=[
            ActivationCondition(
                operator="contains",
                is_not=False,
                variable_id="click_url",
                target_value="download",
            ),
        ],
    )
    print(f"Создан триггер с условием: {trigger.name}")


def example_posthog_tag():
    """Пример создания тега PostHog/Динамика"""

    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    posthog_html = """<script>
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){
        // ... PostHog snippet ...
    })}(document,window.posthog||[]);
    posthog.init('phc_YOUR_PROJECT_KEY', {
        api_host: 'https://your-posthog-instance.com',
        person_profiles: 'identified_only',
    })
</script>"""

    tag = api.create_tag(
        container_id=CONTAINER_ID,
        name="PostHog Analytics",
        html_code=posthog_html,
        trigger_ids=["26125"],  # ID триггера All Pages
    )
    print(f"Создан PostHog тег: {tag.tag_id}")


if __name__ == "__main__":
    main()
