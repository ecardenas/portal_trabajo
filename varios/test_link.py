"""Script para investigar cómo se pasa el ID de la oferta"""
from playwright.sync_api import sync_playwright

URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Capturar requests
        requests_capturados = []
        def handle_request(request):
            if "detalle" in request.url or request.method == "POST":
                requests_capturados.append({
                    "url": request.url,
                    "method": request.method,
                    "post_data": request.post_data,
                })
        
        page.on("request", handle_request)
        
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        # Encontrar primera tarjeta y su botón
        cards = page.locator(".cuadro-vacantes").all()
        if cards:
            card = cards[0]
            
            # Obtener info del botón antes de hacer clic
            btn = card.locator("button.btn-primary").first
            if btn.count() > 0:
                btn_id = btn.get_attribute("id")
                btn_name = btn.get_attribute("name")
                btn_onclick = btn.get_attribute("onclick")
                
                print(f"Botón ID: {btn_id}")
                print(f"Botón Name: {btn_name}")
                print(f"Botón onclick: {btn_onclick}")
                
                # También buscar inputs ocultos en el formulario
                form = page.locator("form").first
                if form.count() > 0:
                    hidden_inputs = form.locator("input[type='hidden']").all()
                    print(f"\nInputs ocultos en el form ({len(hidden_inputs)}):")
                    for inp in hidden_inputs[:10]:  # solo primeros 10
                        name = inp.get_attribute("name")
                        value = inp.get_attribute("value")
                        if value and len(value) < 100:
                            print(f"  {name} = {value}")
                
                # Hacer clic
                print("\n--- Haciendo clic en Ver más ---")
                btn.click()
                page.wait_for_timeout(3000)
                
                print(f"\nURL actual: {page.url}")
                
                # Ver requests capturados
                print(f"\nRequests capturados ({len(requests_capturados)}):")
                for req in requests_capturados:
                    print(f"  {req['method']} {req['url'][:80]}")
                    if req['post_data']:
                        # Buscar parámetros interesantes
                        post = req['post_data']
                        if "idOfertaLaboral" in post or "idOferta" in post:
                            print(f"    POST DATA: {post[:500]}")
                
                # Buscar el botón "Volver a la lista"
                print("\n--- Buscando botón Volver ---")
                volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                if volver_btn.count() > 0:
                    print("Encontrado botón 'Volver a la lista'")
                    volver_btn.click()
                    page.wait_for_timeout(2000)
                    print(f"URL después de volver: {page.url}")
        
        browser.close()

if __name__ == "__main__":
    main()
