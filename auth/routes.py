
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, constr
from auth.utils import hash_password, verify_password, generate_jwt, get_current_user
from fastapi import Depends
router = APIRouter()
from database import get_db_connection
from notificaciones.auditoria import registrar_auditoria

@router.get("/auth/me")
def get_me(user=Depends(get_current_user)):
    return {"user": user}

class UserRegister(BaseModel):
    username: constr(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/auth/register")
def register(user: UserRegister, request=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        registrar_auditoria(None, user.email, "registro_fallido", resultado="Usuario ya registrado")
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")

    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        registrar_auditoria(None, user.email, "registro_fallido", resultado="Email ya registrado")
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    password_hash = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (user.username, user.email, password_hash, "user")
    )
    usuario_id = cursor.lastrowid
    conn.commit()
    conn.close()
    # Auditoría
    registrar_auditoria(usuario_id, user.email, "registro_exitoso")
    return {"msg": "Usuario registrado correctamente"}

@router.post("/auth/login")
def login(user: UserLogin, request=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash, role FROM users WHERE email = ?", (user.email,))
    row = cursor.fetchone()
    conn.close()
    if not row or not verify_password(user.password, row[3]):
        registrar_auditoria(None, user.email, "login_fallido", resultado="Credenciales incorrectas")
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = generate_jwt({"id": row[0], "username": row[1], "email": row[2], "role": row[4]})
    registrar_auditoria(row[0], row[2], "login_exitoso")
    return {"access_token": token, "token_type": "bearer"}

# OAuth endpoints (placeholders)
@router.get("/auth/oauth/google")
def oauth_google():
    return {"msg": "OAuth Google no implementado aún"}

@router.get("/auth/oauth/outlook")
def oauth_outlook():
    return {"msg": "OAuth Outlook no implementado aún"}
