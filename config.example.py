"""
Пример конфигурации.

Скопируй в config.py и заполни своими данными:
    cp config.example.py config.py

Данные берутся из DevTools браузера:
1. Открой https://metrika.yandex.ru → Тег Менеджер
2. DevTools (F12) → Network → любой запрос к api/metrika
3. Скопируй нужные значения
"""

# Cookie Session_id из браузера
SESSION_ID = "3:1769918318.5.2..."

# Header x-csrf-token
CSRF_TOKEN = "8980da54d11975764818941ad58f1588"

# Header x-uid (ID пользователя Яндекса)
UID = "1153393446"

# ID контейнера (из URL: /ytm/overview?id=XXXXX)
CONTAINER_ID = "70978"
