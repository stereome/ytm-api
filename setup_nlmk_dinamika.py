"""
Настройка передачи событий nlmk.shop → Динамика через ЯТМ (контейнер 108580).

Создаёт в контейнере НЛМК:
  1. Тег "Динамика — init" (posthog-js init + autocapture + pageview) на триггере «Просмотр страницы»
  2. Тег "Динамика — ecommerce (EEC)" — ловит EEC-пуши dataLayer и шлёт posthog.capture
     на триггере custom_event (event == "EEC")

Идемпотентность: если тег с таким именем уже есть — пропускает.
НЕ публикует автоматически. Публикация — отдельный шаг (--publish) после preview-проверки.

Команды:
    python setup_nlmk_dinamika.py            # inspect (read-only)
    python setup_nlmk_dinamika.py --create   # создать теги/триггеры (черновик)
    python setup_nlmk_dinamika.py --preview  # preview-ссылка для проверки на live-сайте
    python setup_nlmk_dinamika.py --publish  # опубликовать (ВЛИЯЕТ НА БОЕВОЙ САЙТ)
"""
import sys
import config
from ytm_api import YandexTagManagerAPI
from ytm_api.models import TemplateParameter

CONTAINER_ID = "108580"
SITE_URL = "https://nlmk.shop"

# Проект "nlmk.shop-reconstructed" в Динамике (org НЛМК, team/project 22 — золотой, боевой).
# Токен team 22. Прежний team 21 (nlmk.shop-ytm) удалён 2026-07-01 как deprecated-артефакт.
# НЕ возвращать сюда токен team 21: контейнер 108580 живой, и --update-init/--update-ecommerce/
# --publish перезапишут боевые теги — сбор перенаправится в несуществующий проект, данные пропадут.
DINAMIKA_TOKEN = "phc_LRzOKBAEQzKiZq3JhqWal9DLMpKe2R847gKOfCNHWXm"
DINAMIKA_HOST = "https://demo.dinamikapro.ru"

TAG_INIT = "Динамика — init"
TAG_ECOMMERCE = "Динамика — ecommerce (EEC)"
TRIGGER_PAGEVIEW = "Динамика — Все страницы"
TRIGGER_EEC = "Динамика — DataLayer EEC"

# --- Тег 1: posthog-js init + autocapture + pageview ---
INIT_HTML = """<script>
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug getPageViewId captureTraceFeedback captureTraceMetric".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
posthog.init('__TOKEN__',{api_host:'__HOST__',autocapture:true,capture_pageview:true,capture_pageleave:true,persistence:'localStorage+cookie'});
/* Identity: связываем сессию с аккаунтом НЛМК по куке userid (== user_id в их данных/заказах) */
(function(){try{var m=document.cookie.match(/(?:^|; )userid=([^;]+)/);if(m&&m[1]){posthog.identify(decodeURIComponent(m[1]));}}catch(e){}})();
</script>""".replace("__TOKEN__", DINAMIKA_TOKEN).replace("__HOST__", DINAMIKA_HOST)

# --- Тег 2: EEC dataLayer → posthog.capture (читает dataLayer напрямую, надёжнее object-переменных) ---
ECOMMERCE_HTML = """<script>
(function(){
  if (typeof posthog === 'undefined' || !posthog.capture) { return; }
  var dl = window.dataLayer || [];
  var last = null;
  for (var i = dl.length - 1; i >= 0; i--) {
    if (dl[i] && dl[i].event === 'EEC') { last = dl[i]; break; }
  }
  if (!last || last.__ph_sent) { return; }
  last.__ph_sent = true;
  var action = last.eventAction || '';
  var ec = last.ecommerce || {};
  var map = {
    promoView:'promo_view', promoClick:'promo_click',
    impressions:'product_impressions', detail:'product_view',
    productClick:'product_click', click:'product_click',
    add:'add_to_cart', addToCart:'add_to_cart',
    remove:'remove_from_cart', removeFromCart:'remove_from_cart',
    checkout:'checkout', checkout_option:'checkout_option',
    purchase:'purchase'
  };
  var evt = map[action] || ('eec_' + (action || 'event'));
  // защитное извлечение плоских полей выручки (EEC Universal и GA4-стиль)
  var props = { eec_action: action, eec_label: last.eventLabel || null, ecommerce: ec, ph_source: 'ytm' };
  try {
    var pur = ec.purchase || ec.checkout || {};
    var af = pur.actionField || {};
    var rev = af.revenue != null ? af.revenue : (ec.value != null ? ec.value : af.value);
    if (rev != null && rev !== '') { var n = parseFloat(String(rev).replace(',', '.')); if (!isNaN(n)) props.revenue = n; }
    var txn = af.id || ec.transaction_id || pur.id;
    if (txn) props.transaction_id = String(txn);
    var cur = ec.currency || af.currency; if (cur) props.currency = String(cur);
    var items = pur.products || ec.items || ec.products;
    if (items && items.length != null) props.items_count = items.length;
  } catch (e) {}
  posthog.capture(evt, props);
})();
</script>"""


def get_api():
    return YandexTagManagerAPI(
        session_id=config.SESSION_ID,
        csrf_token=config.CSRF_TOKEN,
        uid=config.UID,
    )


def inspect(api):
    print("=" * 64)
    print(f"Контейнер {CONTAINER_ID} — текущее состояние (read-only)")
    print("=" * 64)
    tags = api.get_tags(CONTAINER_ID)
    print(f"\nТЕГИ ({len(tags)}):")
    for t in tags:
        print(f"  [{t.tag_id}] {t.name} | template={t.template_id} | status={t.status}")
    triggers = api.get_triggers(CONTAINER_ID)
    print(f"\nТРИГГЕРЫ ({len(triggers)}):")
    for tr in triggers:
        print(f"  [{tr.trigger_id}] {tr.name} | template={tr.template_id}")
    return tags, triggers


def create(api):
    inspect(api)
    # Идемпотентность: в контейнере >50 тегов, дефолтный список обрезается —
    # ищем именно наши теги Динамики через search.
    existing = api.get_tags(CONTAINER_ID, search="Динамика", limit=50)
    tag_names = {t.name for t in existing}
    print(f"\nНайдено существующих тегов 'Динамика': {len(existing)}")

    print("\n" + "=" * 64)
    print("Создание тегов/триггеров Динамики (черновик)")
    print("=" * 64)

    # --- Тег 1: init на триггере page_view ---
    if TAG_INIT in tag_names:
        print(f"[SKIP] '{TAG_INIT}' уже существует")
    else:
        tag1, tr1 = api.create_html_tag_with_trigger(
            container_id=CONTAINER_ID,
            tag_name=TAG_INIT,
            html_code=INIT_HTML,
            trigger_name=TRIGGER_PAGEVIEW,
            trigger_template="page_view",
        )
        print(f"[OK] Тег '{tag1.name}' [{tag1.tag_id}] на триггере '{tr1.name}' [{tr1.trigger_id}]")

    # --- Тег 2: ecommerce на триггере custom_event(EEC) ---
    if TAG_ECOMMERCE in tag_names:
        print(f"[SKIP] '{TAG_ECOMMERCE}' уже существует")
    else:
        eec_trigger = api.create_trigger(
            container_id=CONTAINER_ID,
            name=TRIGGER_EEC,
            template_id="custom_event",
            parameters=[TemplateParameter(type="TextInput", parameter_id="1", value="EEC")],
        )
        tag2 = api.create_tag(
            container_id=CONTAINER_ID,
            name=TAG_ECOMMERCE,
            html_code=ECOMMERCE_HTML,
            trigger_ids=[eec_trigger.trigger_id],
        )
        print(f"[OK] Тег '{tag2.name}' [{tag2.tag_id}] на триггере '{eec_trigger.name}' [{eec_trigger.trigger_id}]")

    # --- changelog ---
    print("\n--- Изменения для публикации (changelog draft) ---")
    try:
        cl = api.get_changelog(CONTAINER_ID)
        v2 = cl.get("version2", {}) or {}
        print("  tags changed:", len(v2.get("tags", [])))
        print("  triggers changed:", len(v2.get("triggers", [])))
    except Exception as e:
        print("  changelog:", e)
    print("\nГотово (НЕ опубликовано). Следующий шаг: --preview, затем --publish.")


def preview(api):
    url = api.preview(CONTAINER_ID, site_url=SITE_URL)
    print("PREVIEW URL:")
    print(url)
    print("\nОткрой эту ссылку (или прогони через browse-site --spy-events),")
    print("чтобы проверить, что события уходят на", DINAMIKA_HOST, "без публикации.")


def update_init(api):
    """Обновить HTML init-тега (например, после добавления identify по куке userid)."""
    tags = api.get_tags(CONTAINER_ID, search="Динамика", limit=50)
    tag = next((t for t in tags if t.name == TAG_INIT), None)
    if not tag:
        print(f"[ERR] тег '{TAG_INIT}' не найден")
        return
    api.update_tag(container_id=CONTAINER_ID, tag_id=tag.tag_id, html_code=INIT_HTML)
    print(f"[OK] обновлён HTML тега '{TAG_INIT}' [{tag.tag_id}]")


def update_ecommerce(api):
    """Обновить HTML ecommerce-тега (например, после добавления извлечения revenue)."""
    tags = api.get_tags(CONTAINER_ID, search="Динамика", limit=50)
    tag = next((t for t in tags if t.name == TAG_ECOMMERCE), None)
    if not tag:
        print(f"[ERR] тег '{TAG_ECOMMERCE}' не найден")
        return
    api.update_tag(container_id=CONTAINER_ID, tag_id=tag.tag_id, html_code=ECOMMERCE_HTML)
    print(f"[OK] обновлён HTML тега '{TAG_ECOMMERCE}' [{tag.tag_id}]")


def publish(api):
    api.publish(
        container_id=CONTAINER_ID,
        name="Динамика — сбор событий",
        description="posthog-js init + autocapture + pageview; EEC dataLayer → Динамика (team 22)",
    )
    print("[OK] Контейнер 108580 ОПУБЛИКОВАН. Изменения активны на nlmk.shop.")


if __name__ == "__main__":
    api = get_api()
    arg = sys.argv[1] if len(sys.argv) > 1 else "--inspect"
    if arg == "--create":
        create(api)
    elif arg == "--update-ecommerce":
        update_ecommerce(api)
    elif arg == "--update-init":
        update_init(api)
    elif arg == "--preview":
        preview(api)
    elif arg == "--publish":
        publish(api)
    else:
        inspect(api)
