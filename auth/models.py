# auth/models.py
# Modelos de usuario y roles

# Ejemplo de modelo de usuario (puedes adaptar a tu ORM preferido)
class User:
    def __init__(self, id, email, password_hash, role):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.role = role
