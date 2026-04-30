# UX Convocatorias Skill

Usa este skill cuando el usuario pida diseñar o mejorar interfaces relacionadas a convocatorias laborales.

## Objetivo
Diseñar interfaces claras, eficientes y orientadas a la toma de decisión rápida del usuario.

El usuario debe poder:
- Encontrar convocatorias en menos de 10 segundos
- Entender si le conviene postular
- Identificar urgencia (fecha límite)
- Filtrar fácilmente

---

## Principios UX obligatorios

1. Prioridad a la búsqueda
- El buscador debe ser visible y prominente
- Debe permitir texto libre (puesto, entidad, palabra clave)

2. Filtros útiles (no decorativos)
- Entidad
- Ubicación
- Modalidad (presencial/remoto)
- Fecha límite
- Sector (público/privado)

3. Estados visuales claros
- Nuevo (últimos 3 días)
- Vence hoy
- Vence pronto (<= 7 días)
- Vigente
- Vencido

4. Escaneo rápido (scanability)
- Evitar bloques largos de texto
- Usar tarjetas o tabla estructurada
- Jerarquía visual clara:
  - Puesto (más grande)
  - Entidad
  - Ubicación
  - Fecha límite

5. Feedback inmediato
- Mostrar cantidad de resultados
- Mostrar “sin resultados” con mensaje útil
- Indicadores de carga

6. Acciones claras
- Botón "Ver detalle"
- Botón "Postular"
- Botón "Guardar"

---

## Patrones UI recomendados

- Tarjetas (cards) para resultados
- Badges para estado (color-coded)
- Filtros en sidebar o barra superior
- Paginación o scroll infinito
- Sticky header con filtros

---

## Reglas técnicas

- Usar HTML semántico
- CSS limpio, sin inline styles
- JS con fetch() para consumir API
- Manejar errores de API
- Diseño responsive obligatorio
- Evitar frameworks pesados si el proyecto usa vanilla JS

---

## Colores sugeridos (estado)

- Nuevo → azul
- Vence hoy → rojo
- Vence pronto → naranja
- Vigente → verde
- Vencido → gris

---

## Cuando generes código:

1. Entregar HTML + CSS + JS
2. Separar responsabilidades
3. Explicar brevemente la lógica
4. Optimizar para claridad visual
5. Priorizar experiencia sobre estética decorativa

---

## Anti-patrones (NO HACER)

- Formularios largos innecesarios
- Filtros ocultos
- Texto sin jerarquía visual
- Tablas saturadas sin separación
- Botones sin prioridad visual