

from fastapi import APIRouter, Request, Depends, HTTPException
from notificaciones.auditoria import registrar_auditoria
from auth.utils import get_current_user
from auth.utils import require_admin
from pydantic import BaseModel
from typing import Optional
import sqlite3

router = APIRouter()

@router.get("/convocatorias/public")
def get_convocatorias_public(request: Request):
    # Aquí iría la lógica real de consulta
    parametros = dict(request.query_params)
    registrar_auditoria(None, None, "consulta_publica_convocatorias", parametros=str(parametros), ip=request.client.host, user_agent=request.headers.get('user-agent'))
    return {"msg": "Consulta pública registrada", "parametros": parametros}

@router.get("/convocatorias/privado")
def get_convocatorias_privado(request: Request, user=Depends(get_current_user)):
    parametros = dict(request.query_params)
    registrar_auditoria(user.get('id'), user.get('email'), "consulta_privada_convocatorias", parametros=str(parametros), ip=request.client.host, user_agent=request.headers.get('user-agent'))
    return {"msg": "Consulta privada registrada", "usuario": user, "parametros": parametros}

@router.post("/convocatorias/marcar")
def marcar_convocatoria():  # Removed empty function
    raise NotImplementedError("Esta función no está implementada.")

class ConvocatoriaEdit(BaseModel):
    remuneracion: Optional[float] = None
    link_postulacion: Optional[str] = None
    fecha_fin: Optional[str] = None

@router.put("/convocatorias/{id}")
def editar_convocatoria(id: int, datos: ConvocatoriaEdit, request: Request, user=Depends(require_admin)):
    DATABASE_FILE = "empleos_servir.db"
    conn = None
    cambios = []
    campos = []
    valores = []

    if datos.remuneracion is not None and datos.remuneracion < 0:
        raise HTTPException(status_code=400, detail="La remuneración no puede ser negativa")

    if datos.link_postulacion is not None and len(datos.link_postulacion.strip()) == 0:
        raise HTTPException(status_code=400, detail="El link de postulación no puede estar vacío")

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, remuneracion, link_postulacion, fecha_fin FROM ofertas WHERE id = ?", (id,))
    oferta_actual = cursor.fetchone()
    if not oferta_actual:
        conn.close()
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada")

    if datos.remuneracion is not None:
        nuevo_valor = float(datos.remuneracion)
        if oferta_actual["remuneracion"] != nuevo_valor:
            campos.append("remuneracion = ?")
            valores.append(nuevo_valor)
            cambios.append(("remuneracion", oferta_actual["remuneracion"], nuevo_valor))

    if datos.link_postulacion is not None:
        nuevo_valor = datos.link_postulacion.strip()
        if oferta_actual["link_postulacion"] != nuevo_valor:
            campos.append("link_postulacion = ?")
            valores.append(nuevo_valor)
            cambios.append(("link_postulacion", oferta_actual["link_postulacion"], nuevo_valor))

    if datos.fecha_fin is not None:
        nuevo_valor = datos.fecha_fin.strip()
        if len(nuevo_valor) == 0:
            conn.close()
            raise HTTPException(status_code=400, detail="La fecha fin no puede estar vacía")
        if oferta_actual["fecha_fin"] != nuevo_valor:
            campos.append("fecha_fin = ?")
            valores.append(nuevo_valor)
            cambios.append(("fecha_fin", oferta_actual["fecha_fin"], nuevo_valor))

    if not cambios:
        conn.close()
        raise HTTPException(status_code=400, detail="No hay cambios para guardar")

    campos.append("editado = 1")
    campos.append("fecha_actualizacion = CURRENT_TIMESTAMP")
    valores.append(id)
    cursor.execute(f"UPDATE ofertas SET {', '.join(campos)} WHERE id = ?", valores)

    for campo, anterior, nuevo in cambios:
        cursor.execute(
            """
            INSERT INTO auditoria_edicion_convocatorias
            (oferta_id, usuario_id, email, campo, valor_anterior, valor_nuevo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                id,
                user.get("id"),
                user.get("email"),
                campo,
                str(anterior) if anterior is not None else None,
                str(nuevo) if nuevo is not None else None,
            ),
        )

    conn.commit()
    conn.close()

    registrar_auditoria(
        user.get("id"),
        user.get("email"),
        "edicion_convocatoria",
        parametros=f"id={id} cambios={[(c[0], c[1], c[2]) for c in cambios]}",
        resultado="ok",
        ip=request.client.host if request and request.client else None,
        user_agent=request.headers.get('user-agent') if request else None,
    )

    return {
        "msg": "Convocatoria actualizada correctamente",
        "campos_editados": [c[0] for c in cambios],
    }
