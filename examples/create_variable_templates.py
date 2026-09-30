"""
Создание шаблонов переменных для галереи Яндекс Тег Менеджера.

Шаблоны переменных — голубой океан в галерее ЯТМ: на момент написания
в ней 0 кастомных шаблонов переменных (все существующие — встроенные).

Этот скрипт создаёт два шаблона Tier 1:
1. URL Query Parameter — извлекает отдельный GET-параметр из URL
2. localStorage Variable — читает значение из localStorage

Workflow:
  1. Шаблон создаётся и публикуется (один раз на контейнер)
  2. На основе шаблона создаются экземпляры переменных
  3. Переменные доступны в тегах и триггерах как {{ Variable Name }}

Перед запуском:
  1. Открой https://metrika.yandex.ru в браузере
  2. Войди в аккаунт, открой DevTools → Network
  3. Найди запрос к api/metrika, скопируй Session_id, x-csrf-token, x-uid
"""

import sys
sys.path.insert(0, '..')

from ytm_api import YandexTagManagerAPI


# ============ НАСТРОЙКИ ============

SESSION_ID = "..."       # Cookie Session_id
CSRF_TOKEN = "..."       # Header x-csrf-token
UID = "..."              # Header x-uid
CONTAINER_ID = "70978"   # ID контейнера


def main():
    api = YandexTagManagerAPI(
        session_id=SESSION_ID,
        csrf_token=CSRF_TOKEN,
        uid=UID,
    )

    # ============================================================
    # 1. URL Query Parameter — шаблон + переменные для UTM
    # ============================================================
    print("=" * 60)
    print("СОЗДАНИЕ ШАБЛОНА: URL Query Parameter")
    print("=" * 60)

    # Создаём и публикуем шаблон (один раз)
    qp_template = api.create_url_query_param_template(CONTAINER_ID)
    print(f"  Шаблон создан: {qp_template['name']}")
    print(f"  templateId: {qp_template['templateId']}")
    print(f"  templateVersion: {qp_template.get('templateVersion')}")

    # Создаём переменные для всех UTM-меток
    utm_params = {
        "utm_source": "UTM Source",
        "utm_medium": "UTM Medium",
        "utm_campaign": "UTM Campaign",
        "utm_content": "UTM Content",
        "utm_term": "UTM Term",
    }

    print("\n  Создаём UTM-переменные:")
    for param, var_name in utm_params.items():
        var = api.create_variable_from_template(
            CONTAINER_ID, qp_template,
            name=var_name,
            param_values={"paramName": param},
        )
        print(f"    ✓ {var_name} (параметр: {param})")

    # Дополнительно — другие полезные query-параметры
    extra_params = {
        "gclid": "Google Click ID",
        "yclid": "Yandex Click ID",
        "fbclid": "Facebook Click ID",
    }

    print("\n  Создаём переменные рекламных Click ID:")
    for param, var_name in extra_params.items():
        var = api.create_variable_from_template(
            CONTAINER_ID, qp_template,
            name=var_name,
            param_values={"paramName": param},
        )
        print(f"    ✓ {var_name} (параметр: {param})")

    # ============================================================
    # 2. localStorage Variable — шаблон + примеры переменных
    # ============================================================
    print("\n" + "=" * 60)
    print("СОЗДАНИЕ ШАБЛОНА: localStorage Variable")
    print("=" * 60)

    ls_template = api.create_local_storage_template(CONTAINER_ID)
    print(f"  Шаблон создан: {ls_template['name']}")
    print(f"  templateId: {ls_template['templateId']}")

    # Примеры переменных из localStorage
    ls_vars = {
        "quiz_result": "LS - Quiz Result",
        "cart_id": "LS - Cart ID",
        "user_segment": "LS - User Segment",
    }

    print("\n  Создаём localStorage-переменные:")
    for key, var_name in ls_vars.items():
        var = api.create_variable_from_template(
            CONTAINER_ID, ls_template,
            name=var_name,
            param_values={"keyName": key},
        )
        print(f"    ✓ {var_name} (ключ: {key})")

    # ============================================================
    # 3. Публикация контейнера
    # ============================================================
    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)
    print("  Шаблоны и переменные созданы.")
    print("  Для применения на сайте опубликуйте контейнер:")
    print('  api.publish(CONTAINER_ID, name="Добавлены шаблоны переменных")')

    # Раскомментируйте для публикации:
    # api.publish(CONTAINER_ID, name="Шаблоны переменных Tier 1")


if __name__ == "__main__":
    main()
