# Deploy Railway Skill

Usa este skill para preparar despliegue en Railway.

Objetivo:
Asegurar que el backend FastAPI pueda ejecutarse correctamente en Railway.

Reglas:
- Usar variables de entorno.
- Verificar requirements.txt.
- Verificar Procfile.
- Usar puerto dinámico con variable PORT.
- Preparar conexión a PostgreSQL mediante DATABASE_URL.
- No incluir secretos en el repositorio.

Archivos relevantes:
- requirements.txt
- Procfile
- app/main.py
- .env.example

Comando sugerido:
uvicorn app.main:app --host 0.0.0.0 --port $PORT