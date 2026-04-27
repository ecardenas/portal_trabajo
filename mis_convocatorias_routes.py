from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from database import get_connection
from auth.utils import get_current_user

router = APIRouter()

MAX_PRIORITIZADAS = 20

@router.get("/mis-convocatorias", tags=["Mis Convocatorias"])
def listar_mis_convocatorias(user=Depends(get_current_user)):
    """Devuelve la lista de id_oferta priorizadas por el usuario autenticado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_oferta, fecha_agregado FROM mis_convocatorias WHERE usuario_id = ? ORDER BY fecha_agregado DESC
    """, (user["id"],))
    rows = cursor.fetchall()
    conn.close()
    return [{"id_oferta": row[0], "fecha_agregado": row[1]} for row in rows]

@router.post("/mis-convocatorias/{id_oferta}", tags=["Mis Convocatorias"])
def agregar_mis_convocatorias(id_oferta: str, user=Depends(get_current_user)):
    """Agrega una convocatoria a la lista priorizada del usuario (máx 20)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Verificar límite
    cursor.execute("SELECT COUNT(*) FROM mis_convocatorias WHERE usuario_id = ?", (user["id"],))
    count = cursor.fetchone()[0]
    if count >= MAX_PRIORITIZADAS:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Solo puede priorizar hasta {MAX_PRIORITIZADAS} convocatorias.")
    # Insertar si no existe
    try:
        cursor.execute("""
            INSERT INTO mis_convocatorias (usuario_id, id_oferta) VALUES (?, ?)
        """, (user["id"], id_oferta))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail="Ya está en su lista priorizada o error de datos.")
    conn.close()
    return {"msg": "Convocatoria agregada a su lista priorizada."}

@router.delete("/mis-convocatorias/{id_oferta}", tags=["Mis Convocatorias"])
def quitar_mis_convocatorias(id_oferta: str, user=Depends(get_current_user)):
    """Quita una convocatoria de la lista priorizada del usuario."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM mis_convocatorias WHERE usuario_id = ? AND id_oferta = ?
    """, (user["id"], id_oferta))
    conn.commit()
    conn.close()
    return {"msg": "Convocatoria quitada de su lista priorizada."}
