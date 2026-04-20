from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rappi_availability.load_data import load_all_availability_data
from rappi_availability.metrics import (
    compute_kpis,
    daily_summary,
    detect_events,
    filter_by_time,
    resample_series,
)
from rappi_availability.semantic_chat import answer_question


DATA_DIR = Path("Archivo (1)")
PROCESSED_PATH = Path("data/processed/availability_long.csv")
ACCENT = "#00a86b"
INK = "#18211d"
MUTED = "#66756d"


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> pd.DataFrame:
    if PROCESSED_PATH.exists():
        frame = pd.read_csv(PROCESSED_PATH, parse_dates=["timestamp"])
    else:
        frame = load_all_availability_data(DATA_DIR)
    return frame.sort_values("timestamp").reset_index(drop=True)


def format_number(value: object) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def format_pct(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}%"


def style_page() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --accent: {ACCENT};
            --ink: {INK};
            --muted: {MUTED};
        }}
        .main .block-container {{
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1360px;
        }}
        h1, h2, h3 {{
            letter-spacing: 0;
            color: var(--ink);
        }}
        h1 {{
            font-size: 2.35rem;
            line-height: 1.05;
            margin-bottom: .35rem;
        }}
        [data-testid="stMetric"] {{
            border-left: 3px solid var(--accent);
            padding: .35rem 0 .35rem .85rem;
        }}
        [data-testid="stMetricLabel"] p {{
            color: var(--muted);
            font-size: .82rem;
        }}
        [data-testid="stMetricValue"] {{
            color: var(--ink);
        }}
        section[data-testid="stSidebar"] {{
            background: #f7f9f7;
            border-right: 1px solid #e4ebe6;
        }}
        div[data-testid="stChatMessage"] {{
            border-radius: 8px;
        }}
        .status-strip {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            color: var(--muted);
            font-size: .92rem;
            padding: .2rem 0 1.2rem 0;
        }}
        .status-strip strong {{
            color: var(--ink);
            font-weight: 650;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_template() -> dict:
    return {
        "layout": {
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "font": {"color": INK},
            "xaxis": {"gridcolor": "#edf2ef", "zerolinecolor": "#edf2ef"},
            "yaxis": {"gridcolor": "#edf2ef", "zerolinecolor": "#edf2ef"},
            "colorway": [ACCENT, "#1f6f8b", "#b45309"],
        }
    }


def render_status_strip(frame: pd.DataFrame, duplicate_points: int) -> None:
    start = frame["timestamp"].min().strftime("%Y-%m-%d %H:%M")
    end = frame["timestamp"].max().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <div class="status-strip">
            <span><strong>Rango:</strong> {start} - {end}</span>
            <span><strong>Frecuencia raw:</strong> 10 segundos</span>
            <span><strong>Puntos deduplicados:</strong> {format_number(len(frame))}</span>
            <span><strong>Timestamps con solape:</strong> {format_number(duplicate_points)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Rappi Availability AI Dashboard",
    page_icon="R",
    layout="wide",
)
style_page()

st.title("Rappi Availability AI Dashboard")
st.caption("Disponibilidad visible de tiendas, eventos críticos y preguntas en lenguaje natural.")

data = load_dashboard_data()
if data.empty:
    st.error("No se encontraron datos. Verifica que la carpeta Archivo (1) tenga CSV exportados.")
    st.stop()

min_time = data["timestamp"].min()
max_time = data["timestamp"].max()

with st.sidebar:
    st.header("Filtros")
    date_range = st.date_input(
        "Rango de fechas",
        value=(min_time.date(), max_time.date()),
        min_value=min_time.date(),
        max_value=max_time.date(),
    )
    aggregation = st.selectbox("Agregación visual", ["10s raw", "1min", "5min", "15min", "1h"], index=2)
    event_limit = st.slider("Eventos a mostrar", min_value=5, max_value=20, value=10, step=1)
    show_llm_polish = st.toggle("Pulir respuestas con OpenAI", value=False)
    st.divider()
    st.caption("El chatbot responde sobre el mismo rango filtrado que ves en los gráficos.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered = filter_by_time(data, start=start, end=end)
else:
    filtered = data

if filtered.empty:
    st.warning("El rango seleccionado no contiene puntos. Ajusta las fechas para continuar.")
    st.stop()

kpis = compute_kpis(filtered)
render_status_strip(filtered, int(kpis["duplicate_points"]))

first_value = float(filtered.iloc[0]["visible_stores"])
last_value = float(filtered.iloc[-1]["visible_stores"])
net_change = last_value - first_value
net_change_pct = (net_change / first_value * 100) if first_value else 0.0

metric_columns = st.columns(5)
metric_columns[0].metric("Puntos", format_number(kpis["points"]))
metric_columns[1].metric("Último valor", format_number(kpis["current_value"]), format_pct(net_change_pct))
metric_columns[2].metric("Mediana", format_number(kpis["median_value"]))
metric_columns[3].metric("Mínimo", format_number(kpis["minimum_value"]))
metric_columns[4].metric("Máximo", format_number(kpis["maximum_value"]))

frequency_map = {"10s raw": None, "1min": "1min", "5min": "5min", "15min": "15min", "1h": "1h"}
plot_frame = filtered[["timestamp", "visible_stores"]].copy()
if frequency_map[aggregation]:
    plot_frame = resample_series(filtered, frequency=frequency_map[aggregation])

line = go.Figure()
line.add_trace(
    go.Scatter(
        x=plot_frame["timestamp"],
        y=plot_frame["visible_stores"],
        mode="lines",
        line={"color": ACCENT, "width": 2.2},
        name="Visible stores",
        hovertemplate="%{x}<br>%{y:,.0f} visible stores<extra></extra>",
    )
)
line.update_layout(
    template=plot_template(),
    height=430,
    margin=dict(l=18, r=18, t=48, b=18),
    title=f"Visible stores en el tiempo ({aggregation})",
    xaxis_title="Timestamp",
    yaxis_title="Visible stores",
)
st.plotly_chart(line, use_container_width=True)

left, right = st.columns([1.05, 1])
with left:
    st.subheader("Resumen diario")
    daily = daily_summary(filtered)
    bar = px.bar(
        daily,
        x="date",
        y="median_visible_stores",
        title="Mediana diaria de visible stores",
        labels={"date": "Fecha", "median_visible_stores": "Mediana"},
        color_discrete_sequence=[ACCENT],
        template=plot_template(),
    )
    bar.update_layout(height=360, margin=dict(l=18, r=18, t=48, b=18))
    st.plotly_chart(bar, use_container_width=True)

with right:
    st.subheader("Cambios más fuertes")
    events = detect_events(filtered, frequency="1min", limit=event_limit)
    if events.empty:
        st.info("No hay suficientes puntos para detectar eventos en este rango.")
    else:
        display_events = events[
            ["timestamp", "visible_stores", "previous_value", "change", "direction"]
        ].copy()
        display_events["timestamp"] = display_events["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(display_events, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Chatbot semántico")
st.caption("Prueba: ¿cuál fue el peor momento?, dame la tendencia general, ¿qué día fue mejor?")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Puedo responder sobre mínimos, máximos, tendencias, eventos y resumen diario.",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Pregunta sobre la disponibilidad")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    response = answer_question(prompt, filtered, use_llm=show_llm_polish)
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
