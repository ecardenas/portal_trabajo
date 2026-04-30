# Scraper de Convocatorias Skill

Usa este skill para tareas de scraping de convocatorias laborales.

Objetivo:
Recolectar convocatorias desde fuentes públicas, normalizar datos y guardarlos en base de datos.

Reglas:
- Usar requests para obtener HTML o JSON.
- Separar extracción, transformación y carga.
- Normalizar campos mínimos:
  - entidad
  - puesto
  - modalidad
  - ubicación
  - fecha_inicio
  - fecha_fin
  - enlace
  - fuente
  - estado
- Evitar duplicados usando fuente + enlace o código de convocatoria.
- Registrar errores sin detener todo el proceso.
- No saturar servidores externos.
- Preparar funciones reutilizables para ejecución programada.

Cuando generes código:
1. Crear función scrape_fuente().
2. Crear función normalize_item().
3. Crear función save_items().
4. Incluir logs básicos.