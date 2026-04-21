# Rappi AI-Powered Dashboard Presentation

## Slide 1 - Problema

La disponibilidad de tiendas afecta experiencia de usuario y operacion. El objetivo fue convertir un export historico en una superficie local para monitorear, explicar y preguntar.

## Slide 2 - Entendimiento de datos

El dataset no es un log por tienda; es una serie temporal agregada. Hay 201 CSV, una metrica (`synthetic_monitoring_visible_stores`) y timestamps cada 10 segundos entre el 1 y el 11 de febrero de 2026.

## Slide 3 - Preparacion

Normalice el formato wide a una tabla long con `timestamp`, `visible_stores`, `metric`, `observations` y `source_files`. Tambien deduplique timestamps repetidos por ventanas de exportacion solapadas.

## Slide 4 - Dashboard

El dashboard prioriza lectura operativa: KPIs, serie temporal, resumen diario, eventos fuertes y filtros. La app muestra outliers y ceros porque son parte de la calidad real del dato.

## Slide 5 - Chatbot semantico

El chatbot clasifica preguntas en intents: minimo, maximo, resumen, tendencia, diario y eventos. Las respuestas salen de funciones analiticas locales sobre el rango filtrado, asi que el chat y los graficos siempre hablan del mismo subconjunto.

## Slide 6 - Uso de AI

Use Codex/GPT como agente de desarrollo: analisis del brief, inspeccion del dataset, plan, pruebas, implementacion y material de presentacion. Gemini puede pulir respuestas, pero no es necesario para que el sistema funcione.

## Slide 7 - Tradeoffs

Elegí Streamlit para maximizar funcionalidad local en 1.5 horas. La decision clave fue no inventar datos por tienda: la solucion explica la metrica agregada que realmente existe y mantiene trazabilidad desde el CSV al dashboard.

## Slide 8 - Demo flow

1. Abrir app local.
2. Mostrar rango, deduplicacion y KPIs.
3. Cambiar agregacion visual.
4. Revisar cambios mas fuertes.
5. Preguntar: "¿Cuál fue el peor momento?"
6. Preguntar: "¿Qué día tuvo mejor mediana?"
7. Cerrar con tests y estructura de codigo.
