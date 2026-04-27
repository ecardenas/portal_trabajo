"""
API REST para consultar ofertas de empleo SERVIR
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import Optional, List
import sqlite3
from datetime import datetime

app = FastAPI(
    title="API Empleos SERVIR",
    description="API para consultar ofertas laborales del portal SERVIR",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="web"), name="static")

# Permitir CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Entrypoint principal de la API


from auth.routes import router as auth_router
from convocatorias import routes as convocatorias_routes
from notificaciones import scheduler
from database import init_database
from mis_convocatorias_routes import router as mis_convocatorias_router

# Inicializar la base de datos (crear tablas si no existen)
init_database()

# Aquí se integrará el framework web (Flask, FastAPI, etc.)
# y se registrarán los blueprints/routers de cada módulo


# Registrar routers
app.include_router(auth_router)
app.include_router(mis_convocatorias_router)
DATABASE_FILE = "empleos_servir.db"

def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    return dict(row) if row else None

@app.get("/")
def root():
    return RedirectResponse(url="/app")

@app.get("/app")
def app_web():
    return RedirectResponse(url="/static/index.html")

@app.get("/estadisticas")
def obtener_estadisticas(solo_30: bool = Query(False, description="Solo ofertas que vencen en los próximos 30 días")):
    """Obtiene estadísticas generales de las ofertas. Si solo_30=True, solo cuenta ofertas que vencen en los próximos 30 días."""
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    if solo_30:
        cursor.execute("""
            SELECT COUNT(*) FROM ofertas 
            WHERE date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')
              AND date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+30 days')
        """)
        stats["ofertas_vigentes"] = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM ofertas 
            WHERE date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')
              AND date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+30 days')
        """)
        stats["ofertas_total"] = cursor.fetchone()[0]
        cursor.execute("""
            SELECT AVG(remuneracion) FROM ofertas 
            WHERE remuneracion > 0
              AND date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')
              AND date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+30 days')
        """)
        result = cursor.fetchone()[0]
        stats["remuneracion_promedio"] = round(result, 2) if result else 0
        cursor.execute("""
            SELECT MAX(remuneracion) FROM ofertas 
            WHERE date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')
              AND date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+30 days')
        """)
        stats["remuneracion_maxima"] = cursor.fetchone()[0]
    else:
        cursor.execute("""SELECT COUNT(*) FROM ofertas 
            WHERE date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')""")
        stats["ofertas_vigentes"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ofertas")
        stats["ofertas_total"] = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(remuneracion) FROM ofertas WHERE remuneracion > 0")
        result = cursor.fetchone()[0]
        stats["remuneracion_promedio"] = round(result, 2) if result else 0
        cursor.execute("SELECT MAX(remuneracion) FROM ofertas")
        stats["remuneracion_maxima"] = cursor.fetchone()[0]
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
               numero_convocatoria, activo, fecha_scraping
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
    q: Optional[str] = Query(None, description="Búsqueda por puesto o formación"),
    carrera: Optional[str] = Query(None, description="Filtrar por carrera o formación"),
    especializacion: Optional[str] = Query(None, description="Filtrar por especialización"),
    ubicacion: Optional[str] = Query(None, description="Filtrar por ubicación"),
    entidad: Optional[str] = Query(None, description="Filtrar por entidad"),
    remuneracion: Optional[float] = Query(None, description="Valor de remuneración"),
    remuneracion_op: Optional[str] = Query("gte", description="Operador: gte, lte, eq"),
    estado: Optional[str] = Query("todos", description="todos, vigentes, cerradas"),
    ordenar_por: str = Query("fecha_inicio", description="Campo para ordenar"),
    orden: str = Query("desc", description="asc o desc"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
    solo_30: bool = Query(False, description="Solo ofertas que vencen en los próximos 30 días"),
    situacion: Optional[str] = Query(None, description="vence-pronto, vence-semana, mis, todos")
):
    """Búsqueda avanzada de ofertas"""
    import unicodedata
    def normalize(s):
        if not s:
            return s
        return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')
    conn = get_connection()
    cursor = conn.cursor()
    conditions = []
    params = []
    if solo_30:
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')")
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+30 days')")
    else:
        if estado == "vigentes":
            conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')")
        elif estado == "cerradas":
            conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) < date('now')")

    # Filtro de situación (etiquetas)
    if situacion == "vence-pronto":
        # Vence en los próximos 3 días (incluye hoy)
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')")
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+3 days')")
    elif situacion == "vence-semana":
        # Vence en los próximos 7 días (incluye hoy)
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) >= date('now')")
        conditions.append("date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2)) <= date('now', '+7 days')")
    elif situacion == "mis":
        # Placeholder: solo mis postulaciones (requiere autenticación y lógica adicional)
        # Aquí podrías filtrar por usuario autenticado si tienes esa relación en la BD
        pass
    # Filtro q: buscar en puesto o formacion, omitiendo tildes
    if q:
        nq = normalize(q)
        conditions.append("(LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(puesto,'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u'),'Á','A'),'É','E'),'Í','I'),'Ó','O'),'Ú','U')) LIKE ? OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(formacion,'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u'),'Á','A'),'É','E'),'Í','I'),'Ó','O'),'Ú','U')) LIKE ?)")
        params.append(f"%{nq.lower()}%")
        params.append(f"%{nq.lower()}%")
    if carrera:
        conditions.append("formacion LIKE ?")
        params.append(f"%{carrera}%")
    if especializacion:
        conditions.append("especializacion LIKE ?")
        params.append(f"%{especializacion}%")
    if ubicacion:
        nu = normalize(ubicacion)
        conditions.append("LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ubicacion,'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u'),'Á','A'),'É','E'),'Í','I'),'Ó','O'),'Ú','U')) LIKE ?")
        params.append(f"%{nu.lower()}%")
    if entidad:
        conditions.append("entidad LIKE ?")
        params.append(f"%{entidad}%")
    if remuneracion is not None:
        op_map = {"gte": ">=", "lte": "<=", "eq": "="}
        sql_op = op_map.get(remuneracion_op, ">=")
        conditions.append(f"remuneracion {sql_op} ?")
        params.append(remuneracion)
    if not conditions:
        conditions.append("1 = 1")
    where_clause = " AND ".join(conditions)
    # Contar total
    cursor.execute(f"SELECT COUNT(*) FROM ofertas WHERE {where_clause}", params)
    total = cursor.fetchone()[0]
    # Mapeo seguro de ordenamiento (evita SQL injection y permite ordenar fechas dd/mm/yyyy)
    order_map = {
        "puesto": "puesto",
        "entidad": "entidad",
        "ubicacion": "ubicacion",
        "remuneracion": "remuneracion",
        "fecha_inicio": "date(substr(fecha_inicio, 7, 4) || '-' || substr(fecha_inicio, 4, 2) || '-' || substr(fecha_inicio, 1, 2))",
        "fecha_fin": "date(substr(fecha_fin, 7, 4) || '-' || substr(fecha_fin, 4, 2) || '-' || substr(fecha_fin, 1, 2))",
        "fecha_scraping": "fecha_scraping"
    }
    order_sql = order_map.get(ordenar_por, order_map["fecha_inicio"])
    order_dir = "DESC" if orden.lower() == "desc" else "ASC"
    # Obtener ofertas
    offset = (pagina - 1) * limite
    cursor.execute(f"""
        SELECT id, id_oferta, puesto, entidad, ubicacion, remuneracion, 
               vacantes, fecha_inicio, fecha_fin, link_postulacion,
               numero_convocatoria, activo
        FROM ofertas 
        WHERE {where_clause}
        ORDER BY {order_sql} {order_dir} NULLS LAST
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
            "carrera": carrera,
            "especializacion": especializacion,
            "ubicacion": ubicacion,
            "entidad": entidad,
            "remuneracion": remuneracion,
            "remuneracion_op": remuneracion_op,
            "estado": estado,
            "ordenar_por": ordenar_por,
            "orden": order_dir.lower(),
            "solo_30": solo_30
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