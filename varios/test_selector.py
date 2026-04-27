from playwright.sync_api import sync_playwright

URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)

    # Click en primer "Ver más"
    cards = page.locator(".cuadro-vacantes").all()
    if cards:
        btn = cards[0].locator("button.btn-primary").first
        if btn.count() > 0:
            btn.click()
            page.wait_for_timeout(4000)

            # Probar selectores
            for sel in ["span.sub-titulo-2", ".sub-titulo-2", ".cuadro-seccion-lat span"]:
                el = page.locator(sel).first
                if el.count() > 0:
                    print(f"✅ '{sel}' → '{el.inner_text().strip()}'")
                else:
                    print(f"❌ '{sel}' → NO encontrado")

    browser.close()