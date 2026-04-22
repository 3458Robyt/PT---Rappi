# Rappi Availability Risk Tower Presentation

## Slide 1 - Problema

La disponibilidad de tiendas afecta experiencia de usuario y operacion. El objetivo fue convertir un export historico en una torre de control que explique riesgo operativo, incidentes y recuperacion.

## Slide 2 - Entendimiento de datos

El dataset no es un log por tienda; es una serie temporal agregada. Hay 201 CSV, una metrica (`synthetic_monitoring_visible_stores`) y timestamps cada 10 segundos entre el 1 y el 11 de febrero de 2026.

## Slide 3 - Preparacion

Normalice el formato wide a una tabla long con `timestamp`, `visible_stores`, `metric`, `observations` y `source_files`. Tambien deduplique timestamps repetidos por ventanas de exportacion solapadas.

## Slide 4 - Risk Tower

La interfaz cambia de dashboard tradicional a Control Tower: SLI operativo, error budget, burn rate, MTTR, MTBF, runway temporal con franjas de incidentes y tablas auditables.

## Slide 5 - Chatbot semantico y Gemini

El chatbot clasifica preguntas sobre minimos, maximos, resumen, tendencia, diario, eventos, SLO, error budget, incidentes y recuperacion. Las respuestas salen de funciones analiticas locales sobre el rango filtrado; Gemini solo pule la redaccion si se activa.

## Slide 6 - Uso de AI

Use Codex/GPT como agente de desarrollo: analisis del brief, inspeccion del dataset, plan, pruebas, rediseño completo y material de presentacion. Gemini puede pulir respuestas y briefing, pero no es necesario para que el sistema funcione.

## Slide 7 - Tradeoffs

Elegí Dash para romper la apariencia generica de Streamlit sin inflar el stack: Python, Pandas y Plotly siguen siendo el nucleo. La decision clave fue no inventar datos por tienda: el SLO es un objetivo operativo derivado de tiendas visibles, no un SLA real de Rappi.

## Slide 8 - Demo flow

1. Abrir app local en `http://127.0.0.1:8050`.
2. Mostrar el SLI operativo y el error budget.
3. Explicar el umbral saludable y el objetivo SLO.
4. Revisar el runway temporal con franjas de incidentes.
5. Entrar al ranking de incidentes y el heatmap dia-hora.
6. Preguntar: "¿Cuál fue el peor incidente?"
7. Preguntar: "¿Cómo está el error budget?"
8. Cerrar con tests y estructura de codigo.
