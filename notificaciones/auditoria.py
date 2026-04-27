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
