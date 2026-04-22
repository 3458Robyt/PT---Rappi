# Rappi Availability Risk Tower

Aplicación local para la prueba técnica **AI Interns 2026 de Rappi**. Convierte datos históricos de tiendas visibles en una torre de control de riesgo operativo: identifica ventanas saludables, incidentes, consumo de SLO, error budget y recuperación.

![Vista desktop](docs/assets/risk-tower-desktop.png)

## Resumen Ejecutivo

Un dashboard común responde “cuántas tiendas estaban visibles”. Esta aplicación responde preguntas operativas más útiles:

- ¿Cuándo la disponibilidad estuvo bajo un umbral saludable?
- ¿Cuántos minutos estuvieron en riesgo?
- ¿Cuántos incidentes continuos ocurrieron?
- ¿Qué ventana fue la peor?
- ¿Qué tan rápido se recuperó la operación?
- ¿El rango filtrado cumple un objetivo operativo tipo SLO?

La idea central es: **no solo mostrar disponibilidad, sino explicar riesgo, consumo de budget e impacto operativo**.

## Tecnologías

- **Python 3.11+**: servidor local, análisis y transformación.
- **Dash 4.1.0**: interfaz web interactiva con callbacks.
- **Pandas 2.2.3**: limpieza, resampling y métricas.
- **Plotly 5.24.1**: gráficos interactivos.
- **Gemini Flash**: redacción opcional del briefing y chat, siempre basada en métricas locales.
- **Pytest**: pruebas unitarias del procesamiento, riesgo, chat y layout.

Se mantiene Python porque el reto pide análisis de datos y una demo reproducible. Dash permite entregar una experiencia visual más personalizada que Streamlit sin introducir una arquitectura innecesariamente compleja.

## Datos

La app usa `data/processed/availability_long.csv`, una serie temporal con la métrica `synthetic_monitoring_visible_stores`.

Cada fila contiene:

- `timestamp`: momento observado.
- `visible_stores`: cantidad agregada de tiendas visibles.
- `metric`: nombre de la métrica.
- `observations`: cantidad de observaciones consolidadas.
- `source_files`: archivos fuente usados para construir el punto.

Los datos son **agregados**. No existen IDs de tiendas individuales, por eso la app no inventa análisis tienda por tienda.

## Flujo de Datos

```txt
CSV originales -> scripts/build_dataset.py -> availability_long.csv -> app.py
                                                       |
                                                       v
                      load_data.py -> risk_model.py -> semantic_chat.py
                                      |
                                      v
                         Dash + Plotly + tablas exportables
```

El dataset procesado ya está incluido para que el evaluador pueda ejecutar la aplicación sin reconstruir los CSV originales.

## Métricas y Justificación

- **Disponibilidad saludable**: porcentaje de minutos donde `visible_stores` supera el umbral saludable. Es la lectura principal de salud operativa.
- **Umbral saludable**: por defecto, `70%` de la mediana del rango filtrado. Se usa la mediana para adaptarse al nivel histórico real del rango.
- **Objetivo SLO**: por defecto, `95%` de minutos saludables. No es un SLA real de Rappi; es un objetivo operativo para analizar riesgo.
- **Incidente**: bloque continuo de minutos bajo el umbral. Evita confundir un punto aislado con una ventana real de degradación.
- **Error budget**: minutos no saludables permitidos por el SLO.
- **Burn rate**: cuántas veces se consumió el budget permitido. Si es mayor a `1x`, el rango consumió más de lo permitido.
- **MTTR**: tiempo medio de recuperación de incidentes.
- **MTBF**: separación media entre incidentes.
- **P10/P50/P90**: percentiles para leer estabilidad y dispersión.
- **Velocidad de recuperación**: cambio aproximado de tiendas visibles por minuto al salir de incidentes.

## Cómo Leer la Interfaz

- **Panel superior**: filtros de fecha, hora, granularidad, umbral saludable y SLO.
- **Estado del rango**: resumen ejecutivo del periodo seleccionado.
- **Métricas principales**: salud, consumo SLO, minutos bajo umbral, incidentes, estabilidad y recuperación.
- **Cómo leer esta torre**: explicación breve de conceptos clave para usuarios no técnicos.
- **Error budget**: compara minutos permitidos por el SLO contra minutos realmente consumidos.
- **Runway temporal**: serie de tiendas visibles, umbral saludable, mediana móvil y franjas de incidente.
- **Incidentes por duración**: ranking de ventanas débiles.
- **Mapa día-hora**: patrón horario de disponibilidad.
- **Distribución P10/P50/P90**: estabilidad de la serie.
- **Tablas auditables**: incidentes y puntos recientes, con exportación CSV.
- **AI Analyst**: preguntas en lenguaje natural sobre el rango filtrado.

## Gemini

Gemini **no se configura desde la interfaz**. La clave se carga internamente desde `.env` o desde variables de entorno. Esto evita exponer claves durante la demo o subir secretos al repositorio.

La aplicación funciona sin Gemini. En ese modo, el briefing y el chat responden con reglas determinísticas y métricas calculadas localmente. Si Gemini está configurado, solo mejora la redacción; no agrega cifras, fechas ni supuestos nuevos.

Configurar Gemini con `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

En `.env`, reemplazar:

```txt
GEMINI_API_KEY=replace_me
```

por una clave real.

También se puede configurar solo para la sesión:

```powershell
$env:GEMINI_API_KEY="tu_api_key"
```

Al iniciar la app, el panel superior muestra si Gemini está activo por configuración local. No hay campo para pegar claves en la UI.

## Instalación

Desde PowerShell, en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Ejecutar

```powershell
.\.venv\Scripts\python app.py
```

Abrir:

```txt
http://127.0.0.1:8050
```

## Despliegue en Vercel

La aplicación también está preparada para ejecutarse en Vercel como función Python/WSGI:

```txt
https://rappi-availability-risk-tower.vercel.app
```

La entrada cloud está en `api/index.py`, que expone el servidor Flask interno de Dash. `vercel.json` enruta todo el tráfico hacia esa función para que Dash pueda servir callbacks, assets y rutas internas.

Para habilitar Gemini en Vercel, configurar `GEMINI_API_KEY` como variable de entorno del proyecto en Vercel. La clave no debe ir en el repositorio.

## Reconstruir el Dataset

No es necesario para la demo, porque `data/processed/availability_long.csv` ya está versionado. Si se quiere reconstruir:

```powershell
.\.venv\Scripts\python scripts\build_dataset.py --input "Archivo (1)" --output data\processed\availability_long.csv
```

## Preguntas Sugeridas para la Demo

```txt
¿Cuál fue el peor incidente?
¿Cómo está el SLO y el error budget?
Resume el riesgo operativo del rango.
¿Qué día tuvo mejor mediana?
¿Cuáles fueron los cambios más fuertes?
```

## Verificación

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m py_compile app.py src\rappi_availability\*.py scripts\build_dataset.py
```

## Estructura

```txt
app.py                                  # App Dash principal
api/index.py                            # Entrada WSGI para Vercel
assets/risk_tower.css                   # Sistema visual
data/processed/availability_long.csv    # Dataset procesado para demo
scripts/build_dataset.py                # Normalización de CSV originales
src/rappi_availability/load_data.py     # Carga y limpieza
src/rappi_availability/metrics.py       # KPIs descriptivos
src/rappi_availability/risk_model.py    # SLO, incidentes y error budget
src/rappi_availability/semantic_chat.py # Chat y Gemini
tests/                                  # Pruebas unitarias
docs/assets/                            # Capturas del README
vercel.json                             # Configuración de despliegue
```

## Limitaciones

- No hay datos por tienda individual.
- El SLO es un objetivo operativo derivado, no un SLA oficial.
- El umbral saludable depende del rango filtrado para evitar comparaciones engañosas.
- Gemini es opcional y no reemplaza los cálculos locales.
- No se versionan API keys reales. `.env` está ignorado por Git.

## Resultado Esperado para el Evaluador

El evaluador puede clonar el repositorio, instalar dependencias, configurar Gemini si quiere, ejecutar la app y entender:

1. Qué datos se usan.
2. Qué métricas se calculan.
3. Qué representa cada gráfico.
4. Por qué la app se enfoca en riesgo operativo.
5. Cómo verificar que la solución funciona.
