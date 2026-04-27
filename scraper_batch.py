"""
SCRAPER_MODE = "batch"
Scraper optimizado para procesar cada página (máx 10 registros) y realizar una sola operación masiva de inserción/actualización en la base de datos por página.
- No modifica la lógica ni métodos actuales.
- Usa un método batch_insertar_actualizar_ofertas_batch en database.py (debes crearlo).
- Solo registra logs cuando hay errores.
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import re
from datetime import datetime
import sys
import traceback
import os

# Importar métodos existentes y el nuevo batch
from database import (
    init_database,
    batch_insertar_actualizar_ofertas_batch,  # NUEVO MÉTODO
)

HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"


def limpiar(txt):
    if not txt:
        return ""
    return re.sub(r"\s+", " ", txt).strip()


def extraer_detalle_oferta(page):
    detalle = {}
    try:
        texto_pagina = page.locator("body").inner_text()
        # ...puedes reutilizar la lógica de tu scraper actual...
        # Aquí solo un ejemplo mínimo:
        try:
            id_el = page.locator(".cuadro-seccion-lat span").first
            if id_el.count() > 0:
                id_texto = id_el.inner_text().strip()
                m = re.search(r"(\d{5,7})", id_texto)
                if m:
                    detalle["id_oferta"] = m.group(1)
        except:
            pass
        # Link de postulación (lógica recomendada)
        try:
            span_detalle = page.locator('span.detalle-sp')
            if span_detalle.count() > 0:
                a_tag = span_detalle.locator('a').first
                if a_tag.count() > 0:
                    link_text = a_tag.inner_text().strip()
                    if link_text:
                        detalle["link_postulacion"] = link_text
                    else:
                        href = a_tag.get_attribute('href')
                        if href:
                            detalle["link_postulacion"] = href
        except Exception as e:
            print(f"      ❌ Error extrayendo link_postulacion: {e}")
    except Exception as e:
        print(f"      ❌ Error extrayendo detalle: {e}")
    return detalle


def main():
    print("\n=== SCRAPER BATCH MODE ===\n")
    try:
        init_database()
    except Exception as e:
        print(f"❌ Error inicializando BD: {e}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        pagina_actual = 1
        while True:
            print(f"\n📄 Página {pagina_actual}...")
            try:
                page.wait_for_selector(".cuadro-vacantes", timeout=30000)
            except:
                print("   ⚠️ No se encontraron tarjetas, esperando más...")
                page.wait_for_timeout(5000)

            cards = page.locator(".cuadro-vacantes").all()
            num_cards = len(cards)
            print(f"   📦 Encontradas {num_cards} ofertas")
            if num_cards == 0:
                print("No hay más ofertas.")
                break

            registros_batch = []
            for idx, card in enumerate(cards):
                try:
                    # --- Extraer datos de la tarjeta (igual que scraper.py) ---
                    puesto_el = card.locator(".titulo-vacante label").first
                    puesto = limpiar(puesto_el.inner_text()) if puesto_el.count() > 0 else ""

                    entidad_el = card.locator(".nombre-entidad b").first
                    entidad = limpiar(entidad_el.inner_text()) if entidad_el.count() > 0 else ""

                    texto_card = card.inner_text()

                    def extraer_campo(texto, etiqueta):
                        patron = rf"{re.escape(etiqueta)}\\s*:?\\s*([^\n]+)"
                        m = re.search(patron, texto, re.IGNORECASE)
                        return limpiar(m.group(1)) if m else ""

                    remuneracion_texto = extraer_campo(texto_card, "Remuneración")

                    reg = {
                        "idx": idx,
                        "puesto": puesto,
                        "entidad": entidad,
                        "ubicacion": extraer_campo(texto_card, "Ubicación"),
                        "remuneracion": extraer_campo(texto_card, "Remuneración"),
                        "vacantes": extraer_campo(texto_card, "Cantidad de Vacantes"),
                        "numero_convocatoria": extraer_campo(texto_card, "Número de Convocatoria"),
                        "fecha_inicio": extraer_campo(texto_card, "Fecha Inicio de Publicación"),
                        "fecha_fin": extraer_campo(texto_card, "Fecha Fin de Publicación"),
                    }

                    # --- Entrar al detalle y complementar ---
                    btn = card.locator("button.btn-primary").first
                    if btn.count() > 0:
                        btn.click()
                        page.wait_for_timeout(4000)
                        detalle = extraer_detalle_oferta(page)
                        reg.update(detalle)
                        volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                        if volver_btn.count() > 0:
                            volver_btn.click()
                            page.wait_for_timeout(4000)
                        else:
                            page.go_back()
                            page.wait_for_timeout(4000)
                except Exception as e:
                    print(f"⚠️ Error en tarjeta/detalle: {e}")
                registros_batch.append(reg)

            # --- BATCH DB ---
            try:
                resultados = batch_insertar_actualizar_ofertas_batch(registros_batch)
                # Solo loguear errores
                for reg, (resultado, id_bd) in zip(registros_batch, resultados):
                    if resultado == "error":
                        print(f"❌ Error en registro: {reg}")
            except Exception as e:
                print(f"❌ Error en batch DB: {e}")

            # Siguiente página
            siguiente_btn = page.get_by_text("Siguiente", exact=False).first
            if siguiente_btn.count() > 0:
                siguiente_btn.click()
                page.wait_for_timeout(4000)
                pagina_actual += 1
            else:
                print("Fin de paginación.")
                break
        browser.close()

if __name__ == "__main__":
    main()
