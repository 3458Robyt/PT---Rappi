# Rappi Availability Risk Tower

Aplicación local para la prueba técnica **AI Interns 2026 de Rappi**. Convierte datos históricos de tiendas visibles en una torre de control de riesgo operativo: identifica ventanas saludables, incidentes, consumo de SLO, error budget y recuperación.

![Vista desktop](docs/assets/risk-tower-desktop.png)

## Uso de IA y Equipo de Agentes

Este proyecto fue construido con un flujo de desarrollo asistido por IA. La idea no fue usar IA solo como “chatbot”, sino como parte del proceso completo de diseño, análisis, implementación, pruebas, documentación y despliegue.

### Herramientas de IA usadas

- **Codex**: se usó como agente principal de desarrollo. Su rol fue leer el brief, analizar el código, proponer arquitectura, implementar cambios, depurar errores, escribir pruebas, preparar documentación y coordinar el despliegue.
- **Equipo de agentes especializados**: el desarrollo se trabajó como una orquestación de agentes con responsabilidades distintas: planificación, UI/UX, análisis de datos, debugging sistemático, testing, documentación, GitHub y Vercel. Esto permitió avanzar como si existiera un pequeño equipo de software trabajando en paralelo bajo una misma dirección técnica.
- **Gemini Flash**: se integró dentro de la aplicación para redactar el briefing ejecutivo y responder preguntas en lenguaje natural sobre el rango filtrado.
- **Herramientas de GitHub y Vercel asistidas por IA**: se usaron para preparar el repositorio, revisar el estado de deployments, configurar variables de entorno y publicar la demo.

### Cómo se usaron

Codex fue usado como copiloto técnico y orquestador. Primero ayudó a entender el documento de la prueba y convertirlo en un plan de desarrollo. Después apoyó la transformación de una aplicación tipo dashboard a una experiencia más diferenciada: una torre de control de riesgo operativo.

Los agentes especializados se usaron para dividir el trabajo en frentes concretos:

- **Análisis del problema**: traducir datos de disponibilidad en métricas operativas defendibles.
- **Diseño de interfaz**: rediseñar la experiencia visual para que no pareciera un dashboard genérico.
- **Ingeniería de datos**: estructurar el dataset procesado y calcular KPIs reproducibles.
- **Calidad**: crear pruebas unitarias para métricas, incidentes, SLO, chat y despliegue.
- **Documentación**: convertir el README en una pieza de evaluación, no solo en instrucciones de instalación.
- **Deploy**: publicar la aplicación en Vercel y conectar el deployment con GitHub.

Gemini se usó de forma controlada dentro del producto. La app primero calcula las métricas localmente con Pandas y después Gemini solo mejora la redacción. Esto evita que el modelo invente cifras, fechas o conclusiones que no estén respaldadas por los datos.

### Por qué se tomaron estas decisiones

Se eligió este enfoque porque el reto evalúa tanto la solución técnica como el criterio para usar IA. Por eso, la IA no reemplaza los cálculos críticos: los indicadores de riesgo, incidentes, SLO, error budget y recuperación son determinísticos y auditables.

La IA se usa donde aporta más valor:

- acelerar exploración, diseño e implementación;
- mejorar claridad visual y narrativa;
- redactar explicaciones ejecutivas;
- asistir el proceso de pruebas, documentación y despliegue;
- facilitar preguntas en lenguaje natural sin perder trazabilidad.

La decisión principal fue mantener una separación clara: **Pandas calcula, Plotly visualiza, Dash interactúa y Gemini comunica**. Codex y los agentes apoyan el proceso de construcción, pero la aplicación final sigue siendo verificable por código, pruebas y datos.

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
- **Codex y agentes de IA**: soporte al proceso de análisis, diseño, implementación, pruebas, documentación y despliegue.
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
https://pt-rappi.vercel.app/
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
5. Qué herramientas de IA se usaron, cómo se usaron y por qué se tomaron esas decisiones.
6. Cómo verificar que la solución funciona.
