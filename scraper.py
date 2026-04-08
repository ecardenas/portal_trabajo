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
        marcar_ofertas_inactivas,
        obtener_estadisticas,
        registrar_log_scraping
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

# ============================================================
# CONFIGURACIÓN DE FILTROS PARA EXTRAER DETALLE
# ============================================================
EXTRAER_DETALLE = True  # True = extraer detalle, False = solo datos básicos
CONDICIONES_DETALLE = []  # VACÍO = extrae detalle de TODOS
CONDICIONES_AND = False  # True = AND, False = OR
max_paginas = 10  # None = TODAS las páginas
# ============================================================

print(f"\n{'='*60}")
print(f"🔧 CONFIGURACIÓN:")
print(f"   - Extraer detalle: {EXTRAER_DETALLE}")
print(f"   - Condiciones: {CONDICIONES_DETALLE if CONDICIONES_DETALLE else 'TODAS'}")
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

def cumple_condicion(registro, condicion):
    """Evalúa si un registro cumple una condición"""
    campo = condicion.get("campo")
    operador = condicion.get("operador")
    valor = condicion.get("valor")
    
    valor_registro = registro.get(campo)
    if valor_registro is None:
        return False
    
    if operador == ">=":
        return valor_registro >= valor
    elif operador == ">":
        return valor_registro > valor
    elif operador == "<=":
        return valor_registro <= valor
    elif operador == "<":
        return valor_registro < valor
    elif operador == "==":
        return valor_registro == valor
    elif operador == "contiene":
        return valor.upper() in str(valor_registro).upper()
    elif operador == "no_contiene":
        return valor.upper() not in str(valor_registro).upper()
    
    return False

def debe_extraer_detalle(registro):
    """Determina si se debe extraer el detalle de un registro según las condiciones"""
    if not EXTRAER_DETALLE:
        return False
    
    if not CONDICIONES_DETALLE:
        return True
    
    if CONDICIONES_AND:
        return all(cumple_condicion(registro, c) for c in CONDICIONES_DETALLE)
    else:
        return any(cumple_condicion(registro, c) for c in CONDICIONES_DETALLE)

def extraer_detalle_oferta(page):
    """Extrae información adicional de la página de detalle"""
    detalle = {}
    try:
        texto_pagina = page.locator("body").inner_text()
        
        def extraer(etiqueta):
            patron = rf"{re.escape(etiqueta)}\s*:?\s*([^\n]+)"
            m = re.search(patron, texto_pagina, re.IGNORECASE)
            return limpiar(m.group(1)) if m else ""
        
        # Extraer ID único de la oferta (N° XXXXXX)
        try:
            patron_id = r"N[°º]\s*(\d{5,7})"
            m = re.search(patron_id, texto_pagina)
            if m:
                detalle["id_oferta"] = m.group(1)
                print(f"       🆔 ID Oferta: {m.group(1)}")
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
    stats = {"nuevos": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}
    data = []

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
            page.set_default_timeout(120000)  # 2 minutos
            
            print(f"   🌐 Navegando a {URL[:50]}...")
            
            # Intentar cargar con reintentos
            max_intentos = 3
            for intento in range(max_intentos):
                try:
                    page.goto(URL, wait_until="networkidle", timeout=120000)  # Cambiado de 60000 a 120000
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
                    page.wait_for_selector(".cuadro-vacantes", timeout=10000)
                except:
                    print("   ⚠️ No se encontraron tarjetas, esperando más...")
                    page.wait_for_timeout(3000)

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

                # Extraer detalle de cada registro que cumpla condiciones
                for reg in registros_pagina:
                    if debe_extraer_detalle(reg):
                        idx = reg["idx"]
                        try:
                            cards = page.locator(".cuadro-vacantes").all()
                            if idx < len(cards):
                                btn = cards[idx].locator("button.btn-primary").first
                                if btn.count() > 0:
                                    print(f"    📋 Extrayendo detalle: {reg['puesto'][:40]}...")
                                    btn.click()
                                    page.wait_for_timeout(2000)
                                    
                                    detalle = extraer_detalle_oferta(page)
                                    reg.update(detalle)
                                    
                                    if detalle.get("link_postulacion"):
                                        print(f"       🔗 Link: {detalle['link_postulacion'][:50]}...")
                                    
                                    volver_btn = page.get_by_text("Volver a la lista", exact=False).first
                                    if volver_btn.count() > 0:
                                        volver_btn.click()
                                        page.wait_for_timeout(2000)
                                    else:
                                        page.go_back()
                                        page.wait_for_timeout(2000)
                        except Exception as e:
                            print(f"      ⚠️ Error en detalle: {e}")
                    
                    del reg["idx"]
                    
                    # Guardar en base de datos
                    if BD_DISPONIBLE:
                        resultado, id_bd = insertar_o_actualizar_oferta(reg)  # Cambiado de 'registro' a 'reg'
                        if resultado == "nuevo":
                            stats["nuevos"] += 1
                            reg["_es_nuevo"] = True  # Cambiado de 'registro' a 'reg'
                            ids_procesados.append(id_bd)
                        elif resultado == "actualizado":
                            stats["actualizados"] += 1
                            reg["_es_nuevo"] = False  # Cambiado de 'registro' a 'reg'
                            ids_procesados.append(id_bd)
                        elif resultado == "sin_cambios":
                            stats["sin_cambios"] += 1
                            reg["_es_nuevo"] = False  # Cambiado de 'registro' a 'reg'
                            ids_procesados.append(id_bd)
                    else:
                        stats["nuevos"] += 1
                        reg["_es_nuevo"] = True  # Agregar esta línea
                        print(f"   📝 {reg['puesto'][:50]}")
                    
                    data.append(reg)

                # Siguiente página
                if max_paginas and pagina_actual >= max_paginas:
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
                    page.wait_for_timeout(2500)
                    pagina_actual += 1
                except Exception as e:
                    print(f"\n⚠️ Fin de paginación: {e}")
                    break

            print("\n🔒 Cerrando navegador...")
            browser.close()

        # Marcar ofertas inactivas
        if BD_DISPONIBLE:
            try:
                marcar_ofertas_inactivas(ids_procesados)
                registrar_log_scraping(
                    fecha_inicio, 
                    stats["nuevos"], 
                    stats["actualizados"], 
                    len(ids_procesados),
                    "exitoso"
                )
            except Exception as e:
                print(f"⚠️ Error finalizando BD: {e}")

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

    # Resumen final
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN DEL SCRAPING")
    print(f"{'='*60}")
    print(f"   ✅ Nuevos:        {stats['nuevos']}")
    print(f"   🔄 Actualizados:  {stats['actualizados']}")
    print(f"   ⏸️  Sin cambios:   {stats['sin_cambios']}")
    print(f"   ❌ Errores:       {stats['errores']}")
    print(f"   📦 Total:         {len(data)}")
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