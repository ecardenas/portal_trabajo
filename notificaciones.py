"""
Módulo de notificaciones por Telegram
"""
import os
import requests
from typing import List, Dict, Optional

# Configuración desde variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Configuración de filtros para notificaciones
FILTROS_NOTIFICACION = {
    "remuneracion_minima": float(os.getenv("NOTIF_SUELDO_MIN", "0")),
    "ubicaciones": os.getenv("NOTIF_UBICACIONES", "").split(",") if os.getenv("NOTIF_UBICACIONES") else [],
    "excluir_palabras": os.getenv("NOTIF_EXCLUIR", "").split(",") if os.getenv("NOTIF_EXCLUIR") else [],
}

def enviar_mensaje_telegram(mensaje: str) -> bool:
    """Envía un mensaje a Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram no configurado (falta TOKEN o CHAT_ID)")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Mensaje enviado a Telegram")
            return True
        else:
            print(f"❌ Error Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False

def filtrar_ofertas_notificacion(ofertas: List[Dict]) -> List[Dict]:
    """Filtra ofertas según los criterios de notificación"""
    filtradas = []
    
    for oferta in ofertas:
        # Filtro por remuneración mínima
        remuneracion = oferta.get("remuneracion") or 0
        if FILTROS_NOTIFICACION["remuneracion_minima"] > 0:
            if remuneracion < FILTROS_NOTIFICACION["remuneracion_minima"]:
                continue
        
        # Filtro por ubicación
        ubicaciones = FILTROS_NOTIFICACION["ubicaciones"]
        if ubicaciones and ubicaciones[0]:  # Si hay ubicaciones configuradas
            ubicacion_oferta = (oferta.get("ubicacion") or "").upper()
            if not any(ub.strip().upper() in ubicacion_oferta for ub in ubicaciones):
                continue
        
        # Filtro de exclusión por palabras
        excluir = FILTROS_NOTIFICACION["excluir_palabras"]
        if excluir and excluir[0]:
            puesto = (oferta.get("puesto") or "").upper()
            if any(palabra.strip().upper() in puesto for palabra in excluir):
                continue
        
        filtradas.append(oferta)
    
    return filtradas

def formatear_oferta(oferta: Dict, numero: int) -> str:
    """Formatea una oferta para el mensaje de Telegram"""
    puesto = oferta.get("puesto", "Sin título")[:50]
    entidad = oferta.get("entidad", "Sin entidad")[:40]
    ubicacion = oferta.get("ubicacion", "No especificada")
    remuneracion = oferta.get("remuneracion")
    link = oferta.get("link_postulacion", "")
    fecha_fin = oferta.get("fecha_fin", "")
    
    sueldo_str = f"S/{remuneracion:,.0f}" if remuneracion else "No especificado"
    
    texto = f"""
{numero}️⃣ <b>{puesto}</b>
   🏢 {entidad}
   📍 {ubicacion}
   💰 {sueldo_str}
   📅 Hasta: {fecha_fin}"""
    
    if link:
        texto += f"\n   🔗 <a href='{link}'>Postular aquí</a>"
    
    return texto

def notificar_nuevas_ofertas(ofertas_nuevas: List[Dict]) -> bool:
    """Envía notificación de nuevas ofertas a Telegram"""
    if not ofertas_nuevas:
        print("📭 No hay ofertas nuevas para notificar")
        return True
    
    # Filtrar según criterios
    ofertas_filtradas = filtrar_ofertas_notificacion(ofertas_nuevas)
    
    if not ofertas_filtradas:
        print(f"📭 {len(ofertas_nuevas)} ofertas nuevas, pero ninguna cumple los filtros")
        return True
    
    # Limitar a 10 ofertas por mensaje
    ofertas_a_enviar = ofertas_filtradas[:10]
    
    # Construir mensaje
    mensaje = f"🆕 <b>{len(ofertas_filtradas)} NUEVAS OFERTAS ENCONTRADAS</b>\n"
    
    if len(ofertas_filtradas) > 10:
        mensaje += f"<i>(Mostrando las 10 mejores de {len(ofertas_filtradas)})</i>\n"
    
    # Ordenar por remuneración (mayor primero)
    ofertas_a_enviar.sort(key=lambda x: x.get("remuneracion") or 0, reverse=True)
    
    for i, oferta in enumerate(ofertas_a_enviar, 1):
        mensaje += formatear_oferta(oferta, i)
    
    mensaje += f"\n\n⏰ {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    return enviar_mensaje_telegram(mensaje)

def enviar_resumen_scraping(stats: Dict) -> bool:
    """Envía resumen del scraping"""
    mensaje = f"""📊 <b>RESUMEN SCRAPING SERVIR</b>

✅ Nuevos: {stats.get('nuevos', 0)}
🔄 Actualizados: {stats.get('actualizados', 0)}
⏸️ Sin cambios: {stats.get('sin_cambios', 0)}
❌ Errores: {stats.get('errores', 0)}

📦 Total procesados: {stats.get('total', 0)}
⏰ {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    return enviar_mensaje_telegram(mensaje)

# Test de conexión
def test_telegram():
    """Prueba la conexión con Telegram"""
    return enviar_mensaje_telegram("🤖 Bot de Alertas SERVIR conectado correctamente!")

if __name__ == "__main__":
    print("🧪 Probando conexión Telegram...")
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        test_telegram()
    else:
        print("❌ Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
        print(f"   TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
        print(f"   CHAT_ID: {'✅' if TELEGRAM_CHAT_ID else '❌'}")