from playwright.sync_api import sync_playwright
import pandas as pd
import re
from datetime import datetime
import sys
import traceback
import os

# Modo headless desde variable de entorno
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Intentar importar la base de datos
try:
    from database import (
        init_database,
        insertar_o_actualizar_oferta,
        obtener_estadisticas,
        registrar_log_scraping,
        id_oferta_en_bd,
        existe_por_campos_tarjeta,
        diagnosticar_falso_nuevo,
        registrar_control_scraping,
        obtener_ultimo_control_scraping,
    )
    BD_DISPONIBLE = True
    print("✅ Módulo de base de datos cargado correctamente")
except ImportError as e:
    print(f"⚠️ Base de datos no disponible: {e}")
    print("   Continuando sin persistencia en BD...")
    BD_DISPONIBLE = False

# Intentar importar notificaciones
try:
    from notificaciones import notificar_nuevas_ofertas, enviar_resumen_scraping
    NOTIFICACIONES_DISPONIBLES = True
    print("✅ Módulo de notificaciones cargado")
except ImportError as e:
    print(f"⚠️ Notificaciones no disponibles: {e}")
    NOTIFICACIONES_DISPONIBLES = False

URL = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"
OUTPUT = f"empleos_servir_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
GENERAR_EXCEL = os.getenv("GENERAR_EXCEL", "false").lower() == "true"

# ============================================================
# MODOS DE SCRAPING
#   incremental (default): entra al detalle de cada registro,
#     si el ID ya existe en BD → detiene la corrida (los más
#     recientes están primero, así que todo lo siguiente ya existe)
#   full: entra al detalle de TODOS los registros, guarda/actualiza
#     todo. Lento pero completo.
#   rapido: NO entra al detalle. Usa llave compuesta de campos
#     de tarjeta (puesto+entidad+ubicacion+remuneracion+vacantes+
#     convocatoria+fecha_inicio+fecha_fin). Si ya existe → skip.
#     Si es nuevo → entra al detalle para obtener id_oferta y datos.
#     Ideal para carga inicial rápida.
# ============================================================
SCRAPER_MODE = os.getenv("SCRAPER_MODE", "incremental").lower()
max_paginas = 150  # None = TODAS las páginas
# ============================================================

print(f"\n{'='*60}")
print(f"🔧 CONFIGURACIÓN:")
print(f"   - Modo: {SCRAPER_MODE.upper()}")
print(f"   - Máx páginas: {max_paginas if max_paginas else 'SIN LÍMITE'}")
print(f"{'='*60}\n")

def limpiar(txt):
    if not txt:
        return ""
    return re.sub(r"\s+", " ", txt).strip()

def extraer_remuneracion_num(texto):
    """Extrae el valor numérico de la remuneración"""
    if not texto:
        return None
    limpio = re.sub(r"[sS]/\.?", "", texto)
    limpio = re.sub(r",", "", limpio)
    limpio = limpio.strip()
    
    match = re.search(r"(\d+(?:\.\d{2})?)", limpio)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None


def extraer_detalle_oferta(page):
    """Extrae información adicional de la página de detalle"""
    detalle = {}
    try:
        texto_pagina = page.locator("body").inner_text()
        
        def extraer(etiqueta):
            patron = rf"{re.escape(etiqueta)}\s*:?\s*([^\n]+)"
            m = re.search(patron, texto_pagina, re.IGNORECASE)
            return limpiar(m.group(1)) if m else ""
        
        # Extraer ID único de la oferta desde el panel lateral
        # Está en: span.sub-titulo-2 → "N° 779150"
        try:
            id_el = page.locator(".cuadro-seccion-lat span").first
            if id_el.count() > 0:
                id_texto = id_el.inner_text().strip()
                print(f"       🔬 DEBUG id_texto: '{id_texto}'")
                m = re.search(r"(\d{5,7})", id_texto)
                if m:
                    detalle["id_oferta"] = m.group(1)
        except:
            pass
        
        # Extraer link de postulación
        try:
            link_el = page.locator("a[href*='http']").filter(has_text=re.compile(r"http", re.IGNORECASE)).first
            if link_el.count() > 0:
                detalle["link_postulacion"] = link_el.get_attribute("href")
            else:
                patron_link = r"DETALLE\s*:?\s*(https?://[^\s]+)"
                m = re.search(patron_link, texto_pagina, re.IGNORECASE)
                if m:
                    detalle["link_postulacion"] = m.group(1)
        except:
            pass
        
        detalle["experiencia"] = extraer("EXPERIENCIA")
        detalle["formacion"] = extraer("FORMACIÓN ACADÉMICA - PERFIL")
        detalle["especializacion"] = extraer("ESPECIALIZACIÓN")
        detalle["conocimiento"] = extraer("CONOCIMIENTO")
        detalle["competencias"] = extraer("COMPETENCIAS")
        
        patron_req = r"REQUERIMIENTO\s*:?\s*(.*?)(?=DETALLE|CANTIDAD DE VACANTES|$)"
        m = re.search(patron_req, texto_pagina, re.IGNORECASE | re.DOTALL)
        if m:
            detalle["requerimiento_completo"] = limpiar(m.group(1))[:1000]
        
    except Exception as e:
        print(f"      ❌ Error extrayendo detalle: {e}")
    
    return detalle

def main():
    print("🚀 Iniciando scraper...")
    print(f"   Modo headless: {HEADLESS}")
    
    # Inicializar base de datos si está disponible
    if BD_DISPONIBLE:
        try:
            init_database()
            print("✅ Base de datos inicializada")
        except Exception as e:
            print(f"⚠️ Error inicializando BD: {e}")
    

    fecha_inicio = datetime.now().isoformat()
    ids_procesados = []
    stats = {"nuevos": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0, "falsos_nuevos": 0}
    data = []

    # --- FLUJO INCREMENTAL: obtener fecha límite ---
    fecha_limite_incremental = None
    if SCRAPER_MODE == "incremental" and BD_DISPONIBLE:
        ultimo_control = obtener_ultimo_control_scraping("incremental")
        if ultimo_control and ultimo_control.get("fecha_inicio_max"):
            try:
                # fecha_inicio_max está en formato texto, convertir a datetime
                fecha_max = datetime.strptime(ultimo_control["fecha_inicio_max"], "%d/%m/%Y")
                from datetime import timedelta
                fecha_limite_incremental = fecha_max - timedelta(days=1)
                print(f"   ⏳ Modo incremental: fecha límite de scraping = {fecha_limite_incremental.strftime('%d/%m/%Y')}")
            except Exception as e:
                print(f"   ⚠️ Error interpretando fecha_inicio_max del control: {e}")


    print(f"\n{'='*60}")
    print(f"🚀 SCRAPER SERVIR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    try:
        print("\n📡 Iniciando navegador...")
        with sync_playwright() as p:
            print("   ✅ Playwright iniciado")
            
            browser = p.chromium.launch(headless=HEADLESS)
            print("   ✅ Navegador lanzado")
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Configurar timeouts más largos
            page.set_default_timeout(180000)  # 3 minutos
            
            print(f"   🌐 Navegando a {URL[:50]}...")
            
            # Intentar cargar con reintentos
            max_intentos = 3
            for intento in range(max_intentos):
                try:
                    page.goto(URL, wait_until="networkidle", timeout=180000)  # 3 minutos
                    print("   ✅ Página cargada")
                    break
                except Exception as e:
                    print(f"   ⚠️ Intento {intento + 1}/{max_intentos} falló: {e}")
                    if intento < max_intentos - 1:
                        print("   🔄 Reintentando en 10 segundos...")
                        page.wait_for_timeout(10000)
                    else:
                        raise Exception(f"No se pudo cargar la página después de {max_intentos} intentos")
            
            page.wait_for_timeout(5000)  # Esperar un poco más

            pagina_actual = 1

            while True:
                print(f"\n📄 Página {pagina_actual}...")

                # Esperar a que las tarjetas carguen
                try:
                    page.wait_for_selector(".cuadro-vacantes", timeout=30000)
                except:
                    print("   ⚠️ No se encontraron tarjetas, esperando más...")
                    page.wait_for_timeout(5000)

                cards = page.locator(".cuadro-vacantes").all()
                num_cards = len(cards)
                print(f"   📦 Encontradas {num_cards} ofertas")

                if num_cards == 0:
                    print("   ⚠️ No hay ofertas en esta página")
                    break

                registros_pagina = []
                for i, card in enumerate(cards):
                    try:
                        puesto_el = card.locator(".titulo-vacante label").first
                        puesto = limpiar(puesto_el.inner_text()) if puesto_el.count() > 0 else ""
                        
                        entidad_el = card.locator(".nombre-entidad b").first
                        entidad = limpiar(entidad_el.inner_text()) if entidad_el.count() > 0 else ""
                        
                        texto_card = card.inner_text()
                        
                        def extraer_campo(texto, etiqueta):
                            patron = rf"{re.escape(etiqueta)}\s*:?\s*([^\n]+)"
                            m = re.search(patron, texto, re.IGNORECASE)
                            return limpiar(m.group(1)) if m else ""
                        
                        remuneracion_texto = extraer_campo(texto_card, "Remuneración")
                        
                        registros_pagina.append({
                            "idx": i,
                            "puesto": puesto,
                            "entidad": entidad,
                            "ubicacion": extraer_campo(texto_card, "Ubicación"),
                            "remuneracion": extraer_remuneracion_num(remuneracion_texto),
                            "vacantes": extraer_campo(texto_card, "Cantidad de Vacantes"),
                            "numero_convocatoria": extraer_campo(texto_card, "Número de Convocatoria"),
                            "fecha_inicio": extraer_campo(texto_card, "Fecha Inicio de Publicación"),
                            "fecha_fin": extraer_campo(texto_card, "Fecha Fin de Publicación"),
                        })
                    except Exception as e:
                        print(f"   ❌ Error tarjeta {i}: {e}")
                        stats["errores"] += 1

                # Procesar cada registro según modo
                stop_scraping = False
                for reg in registros_pagina:
                    # --- FLUJO INCREMENTAL: detener si se alcanza la fecha límite ---
                    if SCRAPER_MODE == "incremental" and fecha_limite_incremental:
                        fecha_inicio_reg = reg.get("fecha_inicio")
                        try:
                            fecha_inicio_dt = datetime.strptime(fecha_inicio_reg, "%d/%m/%Y")
                            if fecha_inicio_dt <= fecha_limite_incremental:
                                print(f"       ⏹️  [INCREMENTAL] Fecha de inicio {fecha_inicio_reg} alcanzó o pasó la fecha límite {fecha_limite_incremental.strftime('%d/%m/%Y')} → deteniendo corrida")
                                stop_scraping = True
                                break
                        except Exception as e:
                            print(f"       ⚠️  [INCREMENTAL] Error interpretando fecha_inicio '{fecha_inicio_reg}': {e}")

                    idx = reg["idx"]
                    del reg["idx"]

                    # ── MODO RÁPIDO ──────────────────────────────────────────
                    # 1) Buscar por campos de tarjeta
                    # 2) 0 resultados → entrar al detalle, INSERT/UPDATE por id_oferta
                    # 3) 1 resultado  → skip (ya existe)
                    # 4) >1 resultados → log de alerta, skip
                    if SCRAPER_MODE == "rapido" and BD_DISPONIBLE:
                        coincidencias = existe_por_campos_tarjeta(reg)  # debe retornar lista/count
                        if coincidencias == 1:
                            stats["sin_cambios"] += 1
                            print(f"    ⏭️  [RAPIDO] 1 coincidencia exacta → skip: {reg['puesto'][:40]}")
                            continue
                        elif coincidencias > 1:
                            stats["sin_cambios"] += 1
                            print(f"    ⚠️  [RAPIDO] {coincidencias} coincidencias para: {reg['puesto'][:40]} - {reg['entidad'][:30]} → REVISAR DUPLICADOS en BD")
                            continue
                        # 0 coincidencias → entra al detalle
                        print(f"    🆕 [RAPIDO] Sin coincidencia en tarjeta → entrando al detalle...")

                    # ── ENTRAR AL DETALLE (rápido/full/incremental) ──────────
                    try:
                        cards = page.locator(".cuadro-vacantes").all()
                        if idx < len(cards):
                            btn = cards[idx].locator("button.btn-primary").first
                            if btn.count() > 0:
                                print(f"    🔍 [{SCRAPER_MODE.upper()}] Detalle {idx+1}/{num_cards}: {reg['puesto'][:35]} - {reg['entidad'][:30]}")
                                btn.click()
                                page.wait_for_timeout(4000)

                                detalle = extraer_detalle_oferta(page)
                                id_oferta = detalle.get("id_oferta")
                                if id_oferta:
                                    print(f"       🆔 ID Oferta: {id_oferta}")

                                reg.update(detalle)  # ← PRIMERO actualizar reg

                                # VALIDACIÓN: sin id_oferta no se guarda
                                if not reg.get("id_oferta"):
                                    print(f"       ⛔ NO se capturó id_oferta → SALTANDO registro")
                                    stats["errores"] += 1
                                    volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                                    if volver_btn.count() > 0:
                                        volver_btn.click()
                                        page.wait_for_timeout(4000)
                                    else:
                                        page.go_back()
                                        page.wait_for_timeout(4000)
                                    continue

                                # ── MODO INCREMENTAL: si id_oferta ya existe → detener ──
                                if SCRAPER_MODE == "incremental" and BD_DISPONIBLE:
                                    if id_oferta_en_bd(reg["id_oferta"]):
                                        print(f"       ⏹️  [INCREMENTAL] id_oferta {reg['id_oferta']} ya existe → deteniendo corrida")
                                        volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                                        if volver_btn.count() > 0:
                                            volver_btn.click()
                                        else:
                                            page.go_back()
                                        page.wait_for_timeout(4000)
                                        stop_scraping = True
                                        break

                                if detalle.get("link_postulacion"):
                                    print(f"       🔗 Link: {detalle['link_postulacion'][:50]}...")

                                volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                                if volver_btn.count() > 0:
                                    volver_btn.click()
                                    page.wait_for_timeout(4000)
                                else:
                                    page.go_back()
                                    page.wait_for_timeout(4000)
                    except Exception as e:
                        print(f"      ⚠️ Error en detalle: {e}")
                        stats["errores"] += 1
                        data.append(reg)
                        continue

                    # ── GUARDAR EN BD (INSERT/UPDATE basado en id_oferta) ────
                    if BD_DISPONIBLE:
                        resultado, id_bd = insertar_o_actualizar_oferta(reg)
                        id_oferta = reg.get("id_oferta", "sin-id")

                        if resultado == "nuevo":
                            stats["nuevos"] += 1
                            reg["_es_nuevo"] = True
                            ids_procesados.append(id_bd)
                            if SCRAPER_MODE == "rapido":
                                print(f"       ✅ INSERTADO — tarjeta nueva + id_oferta {id_oferta} no existía en BD (id_bd={id_bd})")
                            else:
                                print(f"       ✅ INSERTADO (id_oferta={id_oferta}, id_bd={id_bd})")

                        elif resultado == "actualizado":
                            stats["actualizados"] += 1
                            reg["_es_nuevo"] = False
                            ids_procesados.append(id_bd)
                            if SCRAPER_MODE == "rapido":
                                print(f"       🔄 ACTUALIZADO — tarjeta cambió pero id_oferta {id_oferta} ya existía en BD (id_bd={id_bd})")
                            else:
                                print(f"       🔄 ACTUALIZADO (id_oferta={id_oferta}, id_bd={id_bd})")

                        elif resultado == "sin_cambios":
                            stats["sin_cambios"] += 1
                            reg["_es_nuevo"] = False
                            ids_procesados.append(id_bd)
                            if SCRAPER_MODE == "rapido":
                                print(f"       ⏭️  SIN CAMBIOS — id_oferta {id_oferta} existe y datos iguales (id_bd={id_bd})")
                            else:
                                print(f"       ⏭️  SIN CAMBIOS (id_oferta={id_oferta}, id_bd={id_bd})")

                    # ...existing code...

                if stop_scraping:
                    print("\n⏹️ Corrida incremental finalizada: todos los nuevos registros guardados")
                    break


                # Siguiente página
                # En modo incremental, no considerar el límite de páginas
                if SCRAPER_MODE != "incremental" and max_paginas and pagina_actual >= max_paginas:
                    print(f"\n⏹️ Límite de {max_paginas} páginas alcanzado")
                    break

                try:
                    botones_sig = page.get_by_text("Sig.", exact=True).all()
                    if len(botones_sig) > 1:
                        btn = botones_sig[1]
                    elif len(botones_sig) == 1:
                        btn = botones_sig[0]
                    else:
                        print("\n✅ No hay más páginas")
                        break
                    
                    if btn.is_disabled():
                        print("\n✅ Última página alcanzada")
                        break
                        
                    print(f"   ➡️ Pasando a página {pagina_actual + 1}...")
                    btn.click()
                    page.wait_for_timeout(4000)
                    pagina_actual += 1
                except Exception as e:
                    print(f"\n⚠️ Fin de paginación: {e}")
                    break

            print("\n🔒 Cerrando navegador...")
            browser.close()


        # Registrar log de scraping
        if BD_DISPONIBLE:
            registrar_log_scraping(
                fecha_inicio, 
                stats["nuevos"], 
                stats["actualizados"], 
                len(ids_procesados),
                "exitoso"
            )

            # Registrar control incremental (si corresponde)
            if SCRAPER_MODE == "incremental":
                # Calcular fechas mín y máx de inicio de los registros procesados
                fechas_inicio = [r.get("fecha_inicio") for r in data if r.get("fecha_inicio")]
                fechas_inicio_dt = []
                for f in fechas_inicio:
                    try:
                        fechas_inicio_dt.append(datetime.strptime(f, "%d/%m/%Y"))
                    except:
                        pass
                if fechas_inicio_dt:
                    fecha_min = min(fechas_inicio_dt).strftime("%d/%m/%Y")
                    fecha_max = max(fechas_inicio_dt).strftime("%d/%m/%Y")
                else:
                    fecha_min = fecha_max = None
                registrar_control_scraping(
                    modo="incremental",
                    registros_extraidos=stats["nuevos"] + stats["actualizados"],
                    fecha_inicio_min=fecha_min,
                    fecha_inicio_max=fecha_max
                )

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        print("\n📋 Traceback completo:")
        traceback.print_exc()
        
        if BD_DISPONIBLE:
            try:
                registrar_log_scraping(fecha_inicio, 0, 0, 0, "error", str(e))
            except:
                pass
        
        # Aún así intentar generar Excel con lo que se haya recopilado
        if data:
            print(f"\n💾 Intentando guardar {len(data)} registros recopilados...")

    # Generar Excel
    if GENERAR_EXCEL:
        print(f"\n📊 Generando Excel con {len(data)} registros...")
        df = pd.DataFrame(data)
        
        if not df.empty:
            try:
                if "vacantes" in df.columns:
                    df["vacantes"] = df["vacantes"].astype(str).str.extract(r"(\d+)", expand=False)
                    df["vacantes"] = pd.to_numeric(df["vacantes"], errors="coerce")
                
                if "fecha_fin" in df.columns:
                    fecha_fin_dt = pd.to_datetime(df["fecha_fin"], format="%d/%m/%Y", errors="coerce")
                    hoy = pd.Timestamp(datetime.now().date())
                    df["dias_restantes"] = (fecha_fin_dt - hoy).dt.days
                    df["vigente"] = df["dias_restantes"] >= 0
                
                df = df.sort_values(["remuneracion", "dias_restantes"], ascending=[False, True], na_position="last")
            except Exception as e:
                print(f"⚠️ Error procesando DataFrame: {e}")

        try:
            with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Ofertas", index=False)
            print(f"✅ Excel guardado: {OUTPUT}")
        except Exception as e:
            print(f"❌ Error guardando Excel: {e}")
    else:
        print("\n📊 Generación de Excel desactivada (GENERAR_EXCEL=false)")

    # Resumen final
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN DEL SCRAPING")
    print(f"{'='*60}")
    print(f"   ✅ Nuevos:        {stats['nuevos']}")
    print(f"   🔄 Actualizados:  {stats['actualizados']}")
    print(f"   ⏸️  Sin cambios:   {stats['sin_cambios']}")
    if stats['falsos_nuevos'] > 0:
        print(f"   🔎 Falsos nuevos: {stats['falsos_nuevos']} (tarjeta no coincidió pero id_oferta ya existía)")
    print(f"   ❌ Errores:       {stats['errores']}")
    print(f"   📦 Total:         {len(data)}")
    if GENERAR_EXCEL:
        print(f"\n   📁 Excel: {OUTPUT}")
    
    if BD_DISPONIBLE:
        print(f"   🗄️  BD: empleos_servir.db")
        try:
            db_stats = obtener_estadisticas()
            print(f"\n📈 BASE DE DATOS:")
            print(f"   Ofertas activas: {db_stats['ofertas_activas']}")
            print(f"   Ofertas total:   {db_stats['ofertas_total']}")
            if db_stats.get('remuneracion_promedio'):
                print(f"   Sueldo promedio: S/{db_stats['remuneracion_promedio']:,.0f}")
        except Exception as e:
            print(f"   ⚠️ Error obteniendo stats: {e}")
    
    # Notificar ofertas nuevas por Telegram
    if NOTIFICACIONES_DISPONIBLES and stats["nuevos"] > 0:
        print("\n📱 Enviando notificaciones...")
        ofertas_nuevas = [r for r in data if r.get("_es_nuevo", False)]
        if ofertas_nuevas:
            notificar_nuevas_ofertas(ofertas_nuevas)
        
        # Enviar resumen
        enviar_resumen_scraping({
            "nuevos": stats["nuevos"],
            "actualizados": stats["actualizados"],
            "sin_cambios": stats["sin_cambios"],
            "errores": stats["errores"],
            "total": len(data)
        })

    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏁 INICIANDO SCRIPT scraper.py")
    print("="*60)
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Scraping cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        traceback.print_exc()
    finally:
        print("\n🏁 Script finalizado")
        # Solo pedir input si NO estamos en modo headless (entorno interactivo)
        if not HEADLESS:
            input("Presiona Enter para cerrar...")