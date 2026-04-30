# FastAPI Backend Skill

Usa este skill cuando el usuario pida crear, modificar o revisar endpoints FastAPI.

Objetivo:
Construir endpoints RESTful para autenticación, convocatorias, usuarios, postulaciones y notificaciones.

Reglas:
- Usar APIRouter.
- Separar router, service y repository.
- Usar Pydantic para request/response.
- Usar manejo de errores HTTPException.
- No colocar SQL directamente en el endpoint.
- Validar filtros de búsqueda.
- Preparar endpoints compatibles con frontend HTML/JS.

Estructura esperada:
- app/main.py
- app/auth/router.py
- app/auth/service.py
- app/convocatorias/router.py
- app/convocatorias/service.py
- app/notifications/router.py
- app/database.py

Cuando generes código:
1. Explica qué archivo modificar.
2. Entrega el código completo del archivo.
3. Indica cómo probarlo con uvicorn.