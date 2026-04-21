# Rappi Availability AI Dashboard

Aplicacion local para la prueba tecnica AI Interns 2026 de Rappi. Convierte los CSV exportados de disponibilidad en un dashboard operativo y un chatbot semantico que responde sobre el mismo rango filtrado en pantalla.

## Que construye

- Dashboard de serie temporal para `synthetic_monitoring_visible_stores`.
- Filtros por fecha, agregacion visual y cantidad de eventos.
- KPIs de puntos, ultimo valor, mediana, minimo y maximo.
- Grafico historico con mediana movil, umbral bajo y marcadores de eventos.
- Resumen diario, mapa por dia/hora, distribucion, tabla de cambios fuertes, tabla de baja disponibilidad y muestra de datos historicos.
- Chatbot en espanol para minimos, maximos, tendencia, resumen diario y eventos.
- Pulido opcional de respuestas con Gemini cuando existe `GEMINI_API_KEY`, `GOOGLE_API_KEY` o una clave temporal en el sidebar.

## Datos

El insumo real esta en `Archivo (1)`. Es una exportacion wide: una fila por CSV y columnas de timestamp cada 10 segundos. El script de preparacion normaliza esos archivos a `data/processed/availability_long.csv` y deduplica ventanas exportadas con solapes.

Nota importante: los archivos contienen una metrica agregada de tiendas visibles. No traen IDs de tiendas individuales, por eso la app no inventa historiales tienda por tienda.

## Correr localmente

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/build_dataset.py --input "Archivo (1)" --output data/processed/availability_long.csv
.\.venv\Scripts\streamlit run app.py
```

La app queda disponible normalmente en:

```txt
http://127.0.0.1:8501
```

## Activar Gemini

La app no guarda claves en el codigo. Para activar el pulido de respuestas con Gemini, usa una de estas opciones:

```powershell
$env:GEMINI_API_KEY="tu_clave"
.\.venv\Scripts\streamlit run app.py
```

Tambien puedes pegar la clave temporalmente en el campo `Gemini API key` del sidebar durante la demo.

## Verificacion

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m py_compile app.py src/rappi_availability/load_data.py src/rappi_availability/metrics.py src/rappi_availability/semantic_chat.py scripts/build_dataset.py
```

## Preguntas sugeridas para demo

```txt
¿Cuál fue el peor momento de disponibilidad?
Dame la tendencia general.
¿Qué día tuvo mejor mediana?
¿Cuáles fueron los cambios más fuertes?
```

## Uso de AI

- Codex/GPT se uso para leer el brief, inspeccionar el formato real de los CSV, crear el plan de desarrollo y construir la solucion con TDD.
- El chatbot usa reglas semanticas deterministicas para que la demo funcione sin secretos y se mantenga grounded en los datos filtrados.
- Gemini queda como capa opcional de redaccion: si se activa, solo pule una respuesta numerica ya calculada localmente.

## Estructura

```txt
app.py
scripts/build_dataset.py
src/rappi_availability/load_data.py
src/rappi_availability/metrics.py
src/rappi_availability/semantic_chat.py
tests/
presentation/rappi-ai-dashboard.md
```
