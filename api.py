"""
API REST para consultar ofertas de empleo SERVIR
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import sqlite3
from datetime import datetime

app = FastAPI(
    title="API Empleos SERVIR",
    description="API para consultar ofertas laborales del portal SERVIR",
    version="1.0.0"
)

# Permitir CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_FILE = "empleos_servir.db"

def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    return dict(row) if row else None

@app.get("/")
def root():
    return {
        "mensaje": "API Empleos SERVIR",
        "version": "1.0.0",
        "endpoints": {
            "ofertas": "/ofertas",
            "estadisticas": "/estadisticas",
            "buscar": "/buscar",
            "oferta_detalle": "/ofertas/{id}"
        }
    }

@app.get("/estadisticas")
def obtener_estadisticas():
    """Obtiene estadísticas generales de las ofertas"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM ofertas WHERE activo = 1")
    stats["ofertas_activas"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ofertas")
    stats["ofertas_total"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(remuneracion) FROM ofertas WHERE activo = 1 AND remuneracion > 0")
    result = cursor.fetchone()[0]
    stats["remuneracion_promedio"] = round(result, 2) if result else 0
    
    cursor.execute("SELECT MAX(remuneracion) FROM ofertas WHERE activo = 1")
    stats["remuneracion_maxima"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(remuneracion) FROM ofertas WHERE activo = 1 AND remuneracion > 0")
    stats["remuneracion_minima"] = cursor.fetchone()[0]
    
    # Top 5 entidades con más ofertas
    cursor.execute("""
        SELECT entidad, COUNT(*) as cantidad 
        FROM ofertas WHERE activo = 1 
        GROUP BY entidad 
        ORDER BY cantidad DESC 
        LIMIT 5
    """)
    stats["top_entidades"] = [{"entidad": row[0], "cantidad": row[1]} for row in cursor.fetchall()]
    
    # Top 5 ubicaciones
    cursor.execute("""
        SELECT ubicacion, COUNT(*) as cantidad 
        FROM ofertas WHERE activo = 1 
        GROUP BY ubicacion 
        ORDER BY cantidad DESC 
        LIMIT 5
    """)
    stats["top_ubicaciones"] = [{"ubicacion": row[0], "cantidad": row[1]} for row in cursor.fetchall()]
    
    conn.close()
    return stats

@app.get("/ofertas")
def listar_ofertas(
    pagina: int = Query(1, ge=1, description="Número de página"),
    limite: int = Query(20, ge=1, le=100, description="Registros por página"),
    activo: bool = Query(True, description="Solo ofertas activas"),
    ordenar_por: str = Query("remuneracion", description="Campo para ordenar"),
    orden: str = Query("desc", description="asc o desc")
):
    """Lista ofertas con paginación"""
    conn = get_connection()
    cursor = conn.cursor()
    
    offset = (pagina - 1) * limite
    
    # Validar campo de ordenamiento
    campos_validos = ["remuneracion", "fecha_fin", "fecha_scraping", "puesto", "entidad"]
    if ordenar_por not in campos_validos:
        ordenar_por = "remuneracion"
    
    orden = "DESC" if orden.lower() == "desc" else "ASC"
    
    # Contar total
    where_clause = "WHERE activo = 1" if activo else ""
    cursor.execute(f"SELECT COUNT(*) FROM ofertas {where_clause}")
    total = cursor.fetchone()[0]
    
    # Obtener ofertas
    cursor.execute(f"""
        SELECT id, id_oferta, puesto, entidad, ubicacion, remuneracion, 
               vacantes, fecha_inicio, fecha_fin, link_postulacion,
               numero_convocatoria, fecha_scraping
        FROM ofertas 
        {where_clause}
        ORDER BY {ordenar_por} {orden} NULLS LAST
        LIMIT ? OFFSET ?
    """, (limite, offset))
    
    ofertas = [row_to_dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "paginas_total": (total + limite - 1) // limite,
        "ofertas": ofertas
    }

@app.get("/ofertas/{oferta_id}")
def obtener_oferta(oferta_id: int):
    """Obtiene detalle completo de una oferta por ID interno"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ofertas WHERE id = ?", (oferta_id,))
    oferta = cursor.fetchone()
    
    conn.close()
    
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    
    return row_to_dict(oferta)

@app.get("/buscar")
def buscar_ofertas(
    q: Optional[str] = Query(None, description="Búsqueda en puesto, entidad o ubicación"),
    ubicacion: Optional[str] = Query(None, description="Filtrar por ubicación"),
    entidad: Optional[str] = Query(None, description="Filtrar por entidad"),
    remuneracion_min: Optional[float] = Query(None, description="Remuneración mínima"),
    remuneracion_max: Optional[float] = Query(None, description="Remuneración máxima"),
    vigente: Optional[bool] = Query(None, description="Solo ofertas vigentes"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100)
):
    """Búsqueda avanzada de ofertas"""
    conn = get_connection()
    cursor = conn.cursor()
    
    conditions = ["activo = 1"]
    params = []
    
    if q:
        conditions.append("(puesto LIKE ? OR entidad LIKE ? OR ubicacion LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    
    if ubicacion:
        conditions.append("ubicacion LIKE ?")
        params.append(f"%{ubicacion}%")
    
    if entidad:
        conditions.append("entidad LIKE ?")
        params.append(f"%{entidad}%")
    
    if remuneracion_min is not None:
        conditions.append("remuneracion >= ?")
        params.append(remuneracion_min)
    
    if remuneracion_max is not None:
        conditions.append("remuneracion <= ?")
        params.append(remuneracion_max)
    
    if vigente:
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')")
    
    where_clause = " AND ".join(conditions)
    
    # Contar total
    cursor.execute(f"SELECT COUNT(*) FROM ofertas WHERE {where_clause}", params)
    total = cursor.fetchone()[0]
    
    # Obtener ofertas
    offset = (pagina - 1) * limite
    cursor.execute(f"""
        SELECT id, id_oferta, puesto, entidad, ubicacion, remuneracion, 
               vacantes, fecha_inicio, fecha_fin, link_postulacion,
               numero_convocatoria
        FROM ofertas 
        WHERE {where_clause}
        ORDER BY remuneracion DESC NULLS LAST
        LIMIT ? OFFSET ?
    """, params + [limite, offset])
    
    ofertas = [row_to_dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "filtros_aplicados": {
            "q": q,
            "ubicacion": ubicacion,
            "entidad": entidad,
            "remuneracion_min": remuneracion_min,
            "remuneracion_max": remuneracion_max,
            "vigente": vigente
        },
        "ofertas": ofertas
    }

@app.get("/ubicaciones")
def listar_ubicaciones():
    """Lista todas las ubicaciones disponibles"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ubicacion, COUNT(*) as cantidad 
        FROM ofertas WHERE activo = 1 AND ubicacion IS NOT NULL
        GROUP BY ubicacion 
        ORDER BY cantidad DESC
    """)
    
    ubicaciones = [{"ubicacion": row[0], "cantidad": row[1]} for row in cursor.fetchall()]
    
    conn.close()
    return ubicaciones

@app.get("/entidades")
def listar_entidades():
    """Lista todas las entidades disponibles"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT entidad, COUNT(*) as cantidad 
        FROM ofertas WHERE activo = 1 AND entidad IS NOT NULL
        GROUP BY entidad 
        ORDER BY cantidad DESC
    """)
    
    entidades = [{"entidad": row[0], "cantidad": row[1]} for row in cursor.fetchall()]
    
    conn.close()
    return entidades

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)