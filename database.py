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
            
            -- Metadata
            fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP,
            activo BOOLEAN DEFAULT 1,
            hash_contenido TEXT
        )
    """)
    
    # Tabla de historial de scraping
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
        f"{registro.get('remuneracion', '')}"
        f"{registro.get('link_postulacion', '')}"
    )
    return hashlib.md5(contenido.encode()).hexdigest()

def insertar_o_actualizar_oferta(registro: Dict) -> tuple:
    """
    Inserta una nueva oferta o actualiza si ya existe.
    USA SOLO id_oferta como llave única.
    Retorna (accion, id) donde accion es 'nuevo', 'actualizado', o 'sin_cambios'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    id_oferta = registro.get("id_oferta")
    
    # Si no tiene id_oferta, no podemos identificar unívocamente, insertar siempre
    if not id_oferta:
        # Insertar sin id_oferta (registro básico sin detalle)
        cursor.execute("""
            INSERT INTO ofertas (
                numero_convocatoria, entidad, puesto, ubicacion, remuneracion,
                vacantes, fecha_inicio, fecha_fin, link_postulacion,
                experiencia, formacion, especializacion, conocimiento,
                competencias, requerimiento_completo, hash_contenido
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            registro.get("numero_convocatoria", ""),
            registro.get("entidad", ""),
            registro.get("puesto", ""),
            registro.get("ubicacion"),
            registro.get("remuneracion"),
            registro.get("vacantes"),
            registro.get("fecha_inicio"),
            registro.get("fecha_fin"),
            registro.get("link_postulacion"),
            registro.get("experiencia"),
            registro.get("formacion"),
            registro.get("especializacion"),
            registro.get("conocimiento"),
            registro.get("competencias"),
            registro.get("requerimiento_completo"),
            generar_hash(registro)
        ))
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return ("nuevo", nuevo_id)
    
    # Buscar por id_oferta
    cursor.execute("SELECT id, hash_contenido FROM ofertas WHERE id_oferta = ?", (id_oferta,))
    existente = cursor.fetchone()
    
    nuevo_hash = generar_hash(registro)
    
    if existente:
        # Ya existe, verificar si hay cambios
        if existente["hash_contenido"] == nuevo_hash:
            conn.close()
            return ("sin_cambios", existente["id"])
        
        # Actualizar registro existente
        cursor.execute("""
            UPDATE ofertas SET
                numero_convocatoria = ?,
                entidad = ?,
                puesto = ?,
                ubicacion = ?,
                remuneracion = ?,
                vacantes = ?,
                fecha_inicio = ?,
                fecha_fin = ?,
                link_postulacion = ?,
                experiencia = ?,
                formacion = ?,
                especializacion = ?,
                conocimiento = ?,
                competencias = ?,
                requerimiento_completo = ?,
                fecha_actualizacion = ?,
                hash_contenido = ?,
                activo = 1
            WHERE id = ?
        """, (
            registro.get("numero_convocatoria", ""),
            registro.get("entidad", ""),
            registro.get("puesto", ""),
            registro.get("ubicacion"),
            registro.get("remuneracion"),
            registro.get("vacantes"),
            registro.get("fecha_inicio"),
            registro.get("fecha_fin"),
            registro.get("link_postulacion"),
            registro.get("experiencia"),
            registro.get("formacion"),
            registro.get("especializacion"),
            registro.get("conocimiento"),
            registro.get("competencias"),
            registro.get("requerimiento_completo"),
            datetime.now().isoformat(),
            nuevo_hash,
            existente["id"]
        ))
        conn.commit()
        conn.close()
        return ("actualizado", existente["id"])
    
    else:
        # Insertar nuevo registro con id_oferta
        cursor.execute("""
            INSERT INTO ofertas (
                id_oferta, numero_convocatoria, entidad, puesto, ubicacion, remuneracion,
                vacantes, fecha_inicio, fecha_fin, link_postulacion,
                experiencia, formacion, especializacion, conocimiento,
                competencias, requerimiento_completo, hash_contenido
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_oferta,
            registro.get("numero_convocatoria", ""),
            registro.get("entidad", ""),
            registro.get("puesto", ""),
            registro.get("ubicacion"),
            registro.get("remuneracion"),
            registro.get("vacantes"),
            registro.get("fecha_inicio"),
            registro.get("fecha_fin"),
            registro.get("link_postulacion"),
            registro.get("experiencia"),
            registro.get("formacion"),
            registro.get("especializacion"),
            registro.get("conocimiento"),
            registro.get("competencias"),
            registro.get("requerimiento_completo"),
            nuevo_hash
        ))
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return ("nuevo", nuevo_id)

def marcar_ofertas_inactivas(ids_activos: List[int]):
    """Marca como inactivas las ofertas que ya no aparecen en el portal"""
    if not ids_activos:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(ids_activos))
    cursor.execute(f"""
        UPDATE ofertas SET activo = 0 
        WHERE id NOT IN ({placeholders}) AND activo = 1
    """, ids_activos)
    conn.commit()
    conn.close()

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

if __name__ == "__main__":
    init_database()
    print(obtener_estadisticas())