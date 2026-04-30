# Instrucciones generales del proyecto

Este proyecto es una plataforma web de convocatorias laborales.

Stack:
- Backend: FastAPI, Uvicorn, Python
- Frontend: HTML, CSS y JavaScript vanilla
- Base de datos: PostgreSQL
- Despliegue: Railway
- Módulos: autenticación, convocatorias, scraping, notificaciones y auditoría

Reglas generales:
- Usar estructura modular.
- Separar rutas, servicios, modelos y acceso a datos.
- No mezclar lógica de negocio dentro de los endpoints.
- Validar entradas con Pydantic.
- Usar variables de entorno para credenciales.
- No hardcodear tokens, contraseñas ni URLs sensibles.
- Documentar endpoints importantes.
- Mantener compatibilidad con despliegue en Railway.