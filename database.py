def registrar_control_scraping(modo: str, registros_extraidos: int, fecha_inicio_min: str, fecha_inicio_max: str):
    """
    Inserta un registro de control de corrida del scraper.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO control_scraping (modo, registros_extraidos, fecha_inicio_min, fecha_inicio_max)
        VALUES (?, ?, ?, ?)
        """,
        (modo, registros_extraidos, fecha_inicio_min, fecha_inicio_max)
    )
    conn.commit()
    conn.close()

def obtener_ultimo_control_scraping(modo: str = None):
    """
    Obtiene el último registro de control_scraping (opcionalmente filtrando por modo).
    Retorna un dict o None si no hay registros.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if modo:
        cursor.execute(
            """
            SELECT * FROM control_scraping WHERE modo = ? ORDER BY fecha_corrida DESC LIMIT 1
            """,
            (modo,)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM control_scraping ORDER BY fecha_corrida DESC LIMIT 1
            """
        )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
"""
Módulo de base de datos para el portal de empleos SERVIR
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import hashlib

DATABASE_FILE = "empleos_servir.db"

def get_connection():
    """Obtiene conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa las tablas de la base de datos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla principal de ofertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ofertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Identificador único del portal SERVIR (LLAVE ÚNICA)
            id_oferta TEXT UNIQUE,
            
            -- Datos de identificación
            numero_convocatoria TEXT,
            entidad TEXT,
            
            -- Datos básicos
            puesto TEXT,
            ubicacion TEXT,
            remuneracion REAL,
            vacantes TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            
            -- Datos del detalle
            link_postulacion TEXT,
            experiencia TEXT,
            formacion TEXT,
            especializacion TEXT,
            conocimiento TEXT,
            competencias TEXT,
            requerimiento_completo TEXT,
            detalle_completo INTEGER DEFAULT 0,
            
            -- Metadata
            fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP,
            activo BOOLEAN DEFAULT 1,
            hash_contenido TEXT
        )
    """)

    # Migración segura para BD existentes
    cursor.execute("PRAGMA table_info(ofertas)")
    columnas = [row[1] for row in cursor.fetchall()]
    if "detalle_completo" not in columnas:
        cursor.execute("ALTER TABLE ofertas ADD COLUMN detalle_completo INTEGER DEFAULT 0")
        # Recalcular solo la primera vez que se añade la columna
        cursor.execute(
            """
            UPDATE ofertas
            SET detalle_completo = CASE
                WHEN COALESCE(formacion, '') <> ''
                  OR COALESCE(experiencia, '') <> ''
                  OR COALESCE(link_postulacion, '') <> ''
                  OR COALESCE(requerimiento_completo, '') <> ''
                THEN 1 ELSE 0
            END
            """
        )
    
    # Tabla de historial de scraping (legacy)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraping_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_inicio TIMESTAMP,
            fecha_fin TIMESTAMP,
            registros_nuevos INTEGER,
            registros_actualizados INTEGER,
            registros_total INTEGER,
            estado TEXT,
            mensaje_error TEXT
        )
    """)

    # Tabla de control para modo incremental
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_scraping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_corrida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modo TEXT,
            registros_extraidos INTEGER,
            fecha_inicio_min TEXT,
            fecha_inicio_max TEXT
        )
    """)

    # Bitácora de cambios en ofertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitacora_cambios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oferta_id INTEGER,
            id_oferta TEXT,
            campo TEXT,
            valor_anterior TEXT,
            valor_nuevo TEXT,
            fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bitacora_oferta ON bitacora_cambios(oferta_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON bitacora_cambios(fecha_cambio)")
    
    # Índices para búsquedas rápidas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_remuneracion ON ofertas(remuneracion)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_ubicacion ON ofertas(ubicacion)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_fecha_fin ON ofertas(fecha_fin)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_activo ON ofertas(activo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_entidad ON ofertas(entidad)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_puesto ON ofertas(puesto)")
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")

def generar_hash(registro: Dict) -> str:
    """Genera un hash del contenido para detectar cambios"""
    contenido = (
        f"{registro.get('puesto', '')}"
        f"{registro.get('entidad', '')}"
        f"{registro.get('ubicacion', '')}"
        f"{registro.get('remuneracion', '')}"
        f"{registro.get('vacantes', '')}"
        f"{registro.get('numero_convocatoria', '')}"
        f"{registro.get('fecha_inicio', '')}"
        f"{registro.get('fecha_fin', '')}"
        f"{registro.get('link_postulacion', '')}"
        f"{registro.get('formacion', '')}"
        f"{registro.get('experiencia', '')}"
        f"{registro.get('especializacion', '')}"
    )
    return hashlib.md5(contenido.encode()).hexdigest()

def insertar_o_actualizar_oferta(reg):
    """
    Busca por id_oferta en BD:
      - Si existe → UPDATE
      - Si no existe → INSERT
    """
    conn = get_connection()
    cursor = conn.cursor()
    id_oferta = reg.get("id_oferta")
    
    try:
        # Buscar por id_oferta
        cursor.execute("SELECT id FROM ofertas WHERE id_oferta = ?", (id_oferta,))
        row = cursor.fetchone()
        
        if row:
            # EXISTE → UPDATE
            id_bd = row[0]
            cursor.execute("""
                UPDATE ofertas SET
                    puesto = ?, entidad = ?, ubicacion = ?, remuneracion = ?,
                    vacantes = ?, numero_convocatoria = ?, fecha_inicio = ?, fecha_fin = ?,
                    experiencia = ?, formacion = ?, especializacion = ?,
                    conocimiento = ?, competencias = ?, link_postulacion = ?,
                    requerimiento_completo = ?, fecha_actualizacion = ?
                WHERE id_oferta = ?
            """, (
                reg.get("puesto"), reg.get("entidad"), reg.get("ubicacion"),
                reg.get("remuneracion"), reg.get("vacantes"), reg.get("numero_convocatoria"),
                reg.get("fecha_inicio"), reg.get("fecha_fin"),
                reg.get("experiencia"), reg.get("formacion"), reg.get("especializacion"),
                reg.get("conocimiento"), reg.get("competencias"), reg.get("link_postulacion"),
                reg.get("requerimiento_completo"), datetime.now().isoformat(),
                id_oferta
            ))
            conn.commit()
            return "actualizado", id_bd
        else:
            # NO EXISTE → INSERT
            cursor.execute("""
                INSERT INTO ofertas (
                    id_oferta, puesto, entidad, ubicacion, remuneracion,
                    vacantes, numero_convocatoria, fecha_inicio, fecha_fin,
                    experiencia, formacion, especializacion,
                    conocimiento, competencias, link_postulacion,
                    requerimiento_completo, fecha_scraping
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_oferta, reg.get("puesto"), reg.get("entidad"), reg.get("ubicacion"),
                reg.get("remuneracion"), reg.get("vacantes"), reg.get("numero_convocatoria"),
                reg.get("fecha_inicio"), reg.get("fecha_fin"),
                reg.get("experiencia"), reg.get("formacion"), reg.get("especializacion"),
                reg.get("conocimiento"), reg.get("competencias"), reg.get("link_postulacion"),
                reg.get("requerimiento_completo"), datetime.now().isoformat()
            ))
            conn.commit()
            return "nuevo", cursor.lastrowid
    finally:
        conn.close()

def _registrar_cambios(cursor, oferta_id: int, id_oferta: str, registro_nuevo: Dict):
    """Compara el registro actual en BD con el nuevo y guarda los cambios en bitácora"""
    cursor.execute("SELECT * FROM ofertas WHERE id = ?", (oferta_id,))
    actual = cursor.fetchone()
    if not actual:
        return
    
    campos_comparar = [
        "puesto", "entidad", "ubicacion", "remuneracion", "vacantes",
        "numero_convocatoria", "fecha_inicio", "fecha_fin",
        "link_postulacion", "experiencia", "formacion",
        "especializacion", "conocimiento", "competencias"
    ]
    
    for campo in campos_comparar:
        val_actual = str(actual[campo]) if actual[campo] is not None else ""
        val_nuevo = str(registro_nuevo.get(campo, "")) if registro_nuevo.get(campo) is not None else ""
        if val_actual != val_nuevo and val_nuevo:  # Solo si hay valor nuevo y es diferente
            cursor.execute("""
                INSERT INTO bitacora_cambios (oferta_id, id_oferta, campo, valor_anterior, valor_nuevo)
                VALUES (?, ?, ?, ?, ?)
            """, (oferta_id, id_oferta or "", campo, val_actual, val_nuevo))
            print(f"       📝 Cambio: {campo}: [{val_actual[:50]}] → [{val_nuevo[:50]}]")

def marcar_ofertas_inactivas(ids_activos: List[int]):
    """Marca como inactivas las ofertas que ya no aparecen en el portal.
    Solo llamar cuando el scraper completó TODAS las páginas."""
    if not ids_activos:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(ids_activos))
    cursor.execute(f"""
        UPDATE ofertas SET activo = 0 
        WHERE id NOT IN ({placeholders}) AND activo = 1
    """, ids_activos)
    afectados = cursor.rowcount
    conn.commit()
    conn.close()
    if afectados:
        print(f"   📋 {afectados} ofertas marcadas como inactivas")

def _normalizar_texto(txt):
    """Normaliza texto para comparación: quita chars invisibles, normaliza espacios"""
    if not txt:
        return ""
    import re
    # Reemplazar non-breaking spaces y otros chars invisibles
    txt = txt.replace('\xa0', ' ').replace('\u200b', '').replace('\u200c', '').replace('\ufeff', '')
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

def _normalizar_numero(val):
    """Normaliza valor numérico para comparación"""
    if val is None:
        return 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0

def existe_por_campos_tarjeta(reg: dict) -> int:
    """
    Busca por campos de tarjeta. Retorna:
      0  → no existe
      1  → existe exactamente uno (skip seguro)
      >1 → duplicados detectados (log de alerta)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM ofertas
            WHERE puesto = ?
              AND entidad = ?
              AND ubicacion = ?
              AND remuneracion = ?
              AND vacantes = ?
              AND numero_convocatoria = ?
              AND fecha_inicio = ?
              AND fecha_fin = ?
        """, (
            reg.get("puesto", ""),
            reg.get("entidad", ""),
            reg.get("ubicacion", ""),
            reg.get("remuneracion"),
            reg.get("vacantes", ""),
            reg.get("numero_convocatoria", ""),
            reg.get("fecha_inicio", ""),
            reg.get("fecha_fin", ""),
        ))
        return cursor.fetchone()[0]
    finally:
        conn.close()

def diagnosticar_falso_nuevo(registro: Dict) -> str:
    """Busca el registro más parecido en BD y muestra qué campos difieren"""
    conn = get_connection()
    cursor = conn.cursor()
    
    puesto = _normalizar_texto(registro.get("puesto", ""))
    entidad = _normalizar_texto(registro.get("entidad", ""))
    
    # Buscar por puesto+entidad (los más estables)
    cursor.execute("""
        SELECT puesto, entidad, ubicacion, remuneracion, vacantes,
               numero_convocatoria, fecha_inicio, fecha_fin, id_oferta
        FROM ofertas
        WHERE TRIM(REPLACE(puesto, X'C2A0', ' ')) = ?
          AND TRIM(REPLACE(entidad, X'C2A0', ' ')) = ?
        LIMIT 1
    """, (puesto, entidad))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return "No se encontró registro similar por puesto+entidad"
    
    campos = ["puesto", "entidad", "ubicacion", "remuneracion", "vacantes",
              "numero_convocatoria", "fecha_inicio", "fecha_fin"]
    diffs = []
    for i, campo in enumerate(campos):
        val_bd = _normalizar_texto(str(row[i])) if row[i] is not None else ""
        val_nuevo = _normalizar_texto(str(registro.get(campo, "")))
        if campo == "remuneracion":
            val_bd_n = _normalizar_numero(row[i])
            val_nuevo_n = _normalizar_numero(registro.get(campo))
            if val_bd_n != val_nuevo_n:
                diffs.append(f"  {campo}: BD=[{row[i]}] vs TARJETA=[{registro.get(campo)}]")
        elif val_bd != val_nuevo:
            diffs.append(f"  {campo}: BD=[{row[i]!r}] vs TARJETA=[{registro.get(campo)!r}]")
    
    if not diffs:
        return f"Todos los campos coinciden (id_oferta en BD: {row[8]}). Posible diferencia de chars invisibles."
    return "Diferencias:\n" + "\n".join(diffs)

def obtener_estadisticas() -> Dict:
    """Obtiene estadísticas de la base de datos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM ofertas WHERE activo = 1")
    stats["ofertas_activas"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ofertas")
    stats["ofertas_total"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ofertas WHERE id_oferta IS NOT NULL")
    stats["con_id_oferta"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(remuneracion) FROM ofertas WHERE activo = 1 AND remuneracion > 0")
    result = cursor.fetchone()[0]
    stats["remuneracion_promedio"] = result if result else 0
    
    conn.close()
    return stats

def registrar_log_scraping(fecha_inicio, nuevos, actualizados, total, estado, error=None):
    """Registra el resultado del scraping"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scraping_log (fecha_inicio, fecha_fin, registros_nuevos, 
                                   registros_actualizados, registros_total, estado, mensaje_error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (fecha_inicio, datetime.now().isoformat(), nuevos, actualizados, total, estado, error))
    conn.commit()
    conn.close()

def id_oferta_en_bd(id_oferta: str) -> bool:
    """Verifica si un id_oferta ya existe en la base de datos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ofertas WHERE id_oferta = ?", (id_oferta,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def obtener_puesto_entidad_por_id_oferta(id_oferta: str) -> Optional[Dict]:
    """Retorna puesto y entidad del registro existente con este id_oferta, o None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT puesto, entidad FROM ofertas WHERE id_oferta = ?", (id_oferta,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"puesto": row["puesto"] or "", "entidad": row["entidad"] or ""}
    return None


def oferta_requiere_detalle(registro: Dict) -> bool:
    """Retorna True si la oferta no tiene detalle completo (compatibilidad legacy)."""
    id_oferta = registro.get("id_oferta")
    if id_oferta:
        return not id_oferta_en_bd(id_oferta)
    return True

    return int(row["detalle_completo"] or 0) == 0

if __name__ == "__main__":
    init_database()
    print(obtener_estadisticas())