"""Прицельная проверка: уходят ли запросы posthog-js на demo.dinamikapro.ru с preview nlmk.shop."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://nlmk.shop?_ytm_preview=56021463732834315"

async def main():
    hits = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"))
        page = await ctx.new_page()
        console_msgs = []
        page.on("console", lambda m: console_msgs.append((m.type, m.text[:200])))
        page.on("pageerror", lambda e: console_msgs.append(("pageerror", str(e)[:200])))

        def on_req(req):
            if "dinamikapro.ru" in req.url or req.method == "POST":
                hits.append(("REQ", req.method, req.url[:120]))
        page.on("request", on_req)
        page.on("requestfailed", lambda r: hits.append(("FAIL", r.failure or "?", r.url[:120])) if "dinamikapro.ru" in r.url else None)
        page.on("response", lambda r: hits.append(("RESP", r.status, r.url[:120])) if "dinamikapro.ru" in r.url else None)

        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(6000)
        # принудительный flush + явный тестовый capture
        try:
            ph = await page.evaluate("typeof window.posthog !== 'undefined' && !!window.posthog.__loaded")
            cfg = await page.evaluate("""(() => {
                if (!window.posthog || !window.posthog.config) return null;
                const c = window.posthog.config;
                return {
                    api_host: c.api_host,
                    ui_host: c.ui_host,
                    token: String(c.token||'').slice(0,12),
                    opt_out_default: c.opt_out_capturing_by_default,
                    has_opted_out: (window.posthog.has_opted_out_capturing ? window.posthog.has_opted_out_capturing() : 'n/a'),
                    autocapture: c.autocapture,
                    disable_external: c.advanced_disable_decide,
                };
            })()""")
            await page.evaluate("window.posthog && window.posthog.capture && window.posthog.capture('ytm_preview_test', {check:1})")
        except Exception as e:
            ph, cfg = f"err:{e}", None
        await page.wait_for_timeout(4000)
        # форсируем pagehide → posthog flush через sendBeacon
        try:
            await page.goto("about:blank", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(4000)
        cfgjs = "skipped"
        # ручной fetch POST со страницы nlmk.shop на ingestion — изоляция network-policy
        inpage_fetch = None
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            inpage_fetch = await page.evaluate("""async () => {
                try {
                    const r = await fetch('https://demo.dinamikapro.ru/i/v0/e/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({api_key:'phc_LRzOKBAEQzKiZq3JhqWal9DLMpKe2R847gKOfCNHWXm', event:'ytm_inpage_fetch', properties:{distinct_id:'ytm-inpage', source:'inpage-fetch'}})
                    });
                    return {ok:r.ok, status:r.status};
                } catch (e) { return {error: String(e)}; }
            }""")
        except Exception as e:
            inpage_fetch = {"outer_error": str(e)}
        await page.wait_for_timeout(2000)
        await browser.close()

    print("posthog loaded:", ph)
    print("posthog config:", cfg)
    print(f"\nЗапросы к dinamikapro.ru ({len(hits)}):")
    seen = set()
    for kind, code, url in hits:
        key = (kind, code, url)
        if key in seen:
            continue
        seen.add(key)
        print(f"  {kind} {code} {url}")
    if not hits:
        print("  (нет запросов — capture не уходит)")

    print(f"\nВсе console-сообщения ({len(console_msgs)}):")
    for t, txt in console_msgs:
        print(f"  [{t}] {txt}")

    print("\nin-page fetch POST /i/v0/e/:", inpage_fetch)

asyncio.run(main())
