# notificaciones/auditoria.py
# Funciones para registrar acciones de usuario en la tabla de auditoría

from database import get_db_connection

def registrar_auditoria(usuario_id, email, accion, parametros=None, resultado=None, ip=None, user_agent=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO auditoria (usuario_id, email, accion, parametros, resultado, ip, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (usuario_id, email, accion, parametros, resultado, ip, user_agent)
    )
    conn.commit()
    conn.close()

def registrar_auditoria_edicion_convocatoria(oferta_id, usuario_id, email, campo, valor_anterior, valor_nuevo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO auditoria_edicion_convocatorias
        (oferta_id, usuario_id, email, campo, valor_anterior, valor_nuevo)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            oferta_id,
            usuario_id,
            email,
            campo,
            str(valor_anterior) if valor_anterior is not None else None,
            str(valor_nuevo) if valor_nuevo is not None else None,
        )
    )
    conn.commit()
    conn.close()
