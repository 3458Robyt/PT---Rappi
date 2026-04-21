from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
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

COLOR_BG = "#090d0b"
COLOR_PANEL = "#111816"
COLOR_PANEL_2 = "#17211e"
COLOR_LINE = "#13d987"
COLOR_BLUE = "#7dd3fc"
COLOR_AMBER = "#f59e0b"
COLOR_RED = "#fb7185"
COLOR_TEXT = "#eef7f1"
COLOR_MUTED = "#9fb2a8"
COLOR_BORDER = "#25332f"


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


def format_compact(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:.0f}"


def format_pct(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}%"


def localize_direction(value: str) -> str:
    return {"increase": "Subida", "decrease": "Bajada"}.get(value, value)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;600;700&family=Fira+Sans:wght@400;500;600;700&display=swap');

        :root {{
            --bg: {COLOR_BG};
            --panel: {COLOR_PANEL};
            --panel-2: {COLOR_PANEL_2};
            --line: {COLOR_LINE};
            --blue: {COLOR_BLUE};
            --amber: {COLOR_AMBER};
            --red: {COLOR_RED};
            --text: {COLOR_TEXT};
            --muted: {COLOR_MUTED};
            --border: {COLOR_BORDER};
        }}

        .stApp {{
            background:
                radial-gradient(circle at 18% -8%, rgba(19, 217, 135, .18), transparent 30rem),
                radial-gradient(circle at 88% 10%, rgba(125, 211, 252, .13), transparent 28rem),
                var(--bg);
            color: var(--text);
            font-family: 'Fira Sans', system-ui, sans-serif;
        }}

        .main .block-container {{
            max-width: 1480px;
            padding: 1.5rem 2rem 3rem;
        }}

        h1, h2, h3, h4 {{
            color: var(--text);
            letter-spacing: 0;
        }}

        h1 {{
            font-family: 'Fira Code', ui-monospace, monospace;
            font-size: clamp(2rem, 4vw, 4.4rem);
            line-height: 1;
            margin-bottom: .4rem;
        }}

        p, label, span, div {{
            letter-spacing: 0;
        }}

        section[data-testid="stSidebar"] {{
            background: #0d1411;
            border-right: 1px solid var(--border);
        }}

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p {{
            color: var(--text);
        }}

        .hero {{
            border: 1px solid rgba(19, 217, 135, .22);
            background: linear-gradient(135deg, rgba(17, 24, 22, .98), rgba(23, 33, 30, .90));
            border-radius: 8px;
            padding: 1.35rem 1.45rem;
            margin-bottom: 1.1rem;
        }}

        .eyebrow {{
            color: var(--line);
            font-family: 'Fira Code', ui-monospace, monospace;
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .hero-subtitle {{
            color: var(--muted);
            max-width: 880px;
            font-size: 1rem;
            margin: .3rem 0 0;
        }}

        .meta-row {{
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            margin-top: 1rem;
        }}

        .meta-pill {{
            color: var(--text);
            background: rgba(255, 255, 255, .055);
            border: 1px solid rgba(255, 255, 255, .095);
            border-radius: 999px;
            padding: .42rem .7rem;
            font-size: .86rem;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .75rem;
            margin: .65rem 0 1rem;
        }}

        .metric-card {{
            min-height: 118px;
            background: linear-gradient(180deg, rgba(23, 33, 30, .98), rgba(13, 20, 17, .98));
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: .9rem .95rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, .25);
        }}

        .metric-label {{
            color: var(--muted);
            font-size: .76rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .metric-value {{
            color: var(--text);
            font-family: 'Fira Code', ui-monospace, monospace;
            font-size: clamp(1.45rem, 2vw, 2.05rem);
            font-weight: 700;
            margin-top: .38rem;
            white-space: nowrap;
        }}

        .metric-detail {{
            color: var(--muted);
            font-size: .82rem;
            margin-top: .45rem;
        }}

        .metric-detail strong {{
            color: var(--line);
            font-weight: 700;
        }}

        .section-kicker {{
            color: var(--muted);
            font-size: .9rem;
            margin-top: -.45rem;
            margin-bottom: .7rem;
        }}

        .insight-strip {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .75rem;
            margin: .35rem 0 1rem;
        }}

        .insight {{
            border-left: 3px solid var(--line);
            background: rgba(255, 255, 255, .035);
            padding: .7rem .85rem;
            border-radius: 8px;
            color: var(--muted);
            min-height: 80px;
        }}

        .insight strong {{
            color: var(--text);
            display: block;
            margin-bottom: .22rem;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: .4rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            background: rgba(255, 255, 255, .045);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            padding: .55rem .9rem;
        }}

        .stTabs [aria-selected="true"] {{
            border-color: rgba(19, 217, 135, .75);
            color: var(--line);
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }}

        div[data-testid="stChatMessage"] {{
            background: rgba(255, 255, 255, .045);
            border: 1px solid var(--border);
            border-radius: 8px;
        }}

        .stDownloadButton button,
        .stForm button {{
            min-height: 44px;
            border-radius: 8px;
            border: 1px solid rgba(19, 217, 135, .45);
            background: rgba(19, 217, 135, .14);
            color: var(--text);
            font-weight: 700;
        }}

        @media (max-width: 1100px) {{
            .metric-grid,
            .insight-strip {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 700px) {{
            .main .block-container {{
                padding: 1rem .85rem 2rem;
            }}
            .metric-grid,
            .insight-strip {{
                grid-template-columns: 1fr;
            }}
            .metric-card {{
                min-height: 96px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_template() -> go.layout.Template:
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=COLOR_PANEL,
            font={"family": "Fira Sans, system-ui, sans-serif", "color": COLOR_TEXT},
            xaxis={
                "gridcolor": "rgba(159,178,168,.16)",
                "zerolinecolor": "rgba(159,178,168,.2)",
                "linecolor": COLOR_BORDER,
                "tickfont": {"color": COLOR_MUTED},
            },
            yaxis={
                "gridcolor": "rgba(159,178,168,.16)",
                "zerolinecolor": "rgba(159,178,168,.2)",
                "linecolor": COLOR_BORDER,
                "tickfont": {"color": COLOR_MUTED},
            },
            legend={"font": {"color": COLOR_TEXT}},
        )
    )


def render_metric(label: str, value: str, detail: str, accent: str = COLOR_LINE) -> str:
    return f"""
    <div class="metric-card" style="border-top: 3px solid {accent}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-detail">{detail}</div>
    </div>
    """


def render_hero(frame: pd.DataFrame, duplicate_points: int, aggregation: str) -> None:
    start = frame["timestamp"].min().strftime("%Y-%m-%d %H:%M")
    end = frame["timestamp"].max().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <section class="hero">
            <div class="eyebrow">Rappi operations analytics</div>
            <h1>Centro de Control de Disponibilidad</h1>
            <p class="hero-subtitle">
                Vista historica de disponibilidad visible de tiendas, eventos de cambio y preguntas semanticas
                sobre el mismo rango filtrado.
            </p>
            <div class="meta-row">
                <span class="meta-pill">Rango visible: {start} - {end}</span>
                <span class="meta-pill">Agregacion: {aggregation}</span>
                <span class="meta-pill">Puntos deduplicados: {format_number(len(frame))}</span>
                <span class="meta-pill">Timestamps con solape: {format_number(duplicate_points)}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def add_chart_layout(fig: go.Figure, height: int, title: str) -> go.Figure:
    fig.update_layout(
        template=plot_template(),
        paper_bgcolor=COLOR_PANEL,
        plot_bgcolor=COLOR_PANEL,
        font={"family": "Fira Sans, system-ui, sans-serif", "color": COLOR_TEXT},
        height=height,
        title={"text": title, "font": {"size": 18, "color": COLOR_TEXT}, "x": 0.01},
        margin=dict(l=18, r=18, t=58, b=24),
        hovermode="x unified",
        legend={
            "bgcolor": "rgba(9,13,11,.72)",
            "bordercolor": COLOR_BORDER,
            "borderwidth": 1,
            "font": {"color": COLOR_TEXT},
        },
    )
    fig.update_xaxes(
        gridcolor="rgba(159,178,168,.16)",
        zerolinecolor="rgba(159,178,168,.2)",
        linecolor=COLOR_BORDER,
        tickfont={"color": COLOR_MUTED},
        title_font={"color": COLOR_MUTED},
    )
    fig.update_yaxes(
        gridcolor="rgba(159,178,168,.16)",
        zerolinecolor="rgba(159,178,168,.2)",
        linecolor=COLOR_BORDER,
        tickfont={"color": COLOR_MUTED},
        title_font={"color": COLOR_MUTED},
    )
    return fig


def build_timeline_chart(
    plot_frame: pd.DataFrame,
    events: pd.DataFrame,
    threshold: float,
    aggregation: str,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_frame["timestamp"],
            y=plot_frame["visible_stores"],
            mode="lines",
            name="Visible stores",
            line={"color": COLOR_LINE, "width": 2.4},
            fill="tozeroy",
            fillcolor="rgba(19,217,135,.13)",
            hovertemplate="%{x}<br>%{y:,.0f} visible stores<extra></extra>",
        )
    )

    rolling = plot_frame.copy()
    rolling["rolling_median"] = rolling["visible_stores"].rolling(12, min_periods=1).median()
    fig.add_trace(
        go.Scatter(
            x=rolling["timestamp"],
            y=rolling["rolling_median"],
            mode="lines",
            name="Mediana movil",
            line={"color": COLOR_BLUE, "width": 1.7, "dash": "dot"},
            hovertemplate="%{x}<br>%{y:,.0f} mediana movil<extra></extra>",
        )
    )

    fig.add_hline(
        y=threshold,
        line_color=COLOR_AMBER,
        line_dash="dash",
        annotation_text=f"Umbral bajo: {format_compact(threshold)}",
        annotation_font_color=COLOR_AMBER,
    )

    if not events.empty:
        marker_frame = events.head(12)
        fig.add_trace(
            go.Scatter(
                x=marker_frame["timestamp"],
                y=marker_frame["visible_stores"],
                mode="markers",
                name="Eventos fuertes",
                marker={
                    "color": marker_frame["direction"].map({"increase": COLOR_BLUE, "decrease": COLOR_RED}),
                    "size": 9,
                    "symbol": "diamond",
                    "line": {"color": "#ffffff", "width": 1},
                },
                customdata=marker_frame[["change", "direction"]],
                hovertemplate="%{x}<br>%{y:,.0f} visible stores<br>Cambio: %{customdata[0]:,.0f}<extra></extra>",
            )
        )

    fig = add_chart_layout(fig, 500, f"Historico de disponibilidad visible ({aggregation})")
    fig.update_yaxes(title="Visible stores")
    fig.update_xaxes(title="Timestamp")
    return fig


def build_daily_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily["date"],
            y=daily["median_visible_stores"],
            name="Mediana diaria",
            marker={"color": COLOR_LINE},
            hovertemplate="%{x}<br>Mediana %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["min_visible_stores"],
            name="Minimo",
            mode="lines+markers",
            line={"color": COLOR_RED, "width": 1.4},
            hovertemplate="%{x}<br>Min %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["max_visible_stores"],
            name="Maximo",
            mode="lines+markers",
            line={"color": COLOR_BLUE, "width": 1.4},
            hovertemplate="%{x}<br>Max %{y:,.0f}<extra></extra>",
        )
    )
    fig = add_chart_layout(fig, 390, "Resumen diario: mediana, minimo y maximo")
    fig.update_yaxes(title="Visible stores")
    fig.update_xaxes(title="Fecha")
    return fig


def build_hourly_heatmap(frame: pd.DataFrame) -> go.Figure:
    hourly = frame.copy()
    hourly["date"] = hourly["timestamp"].dt.date.astype(str)
    hourly["hour"] = hourly["timestamp"].dt.hour
    pivot = hourly.pivot_table(
        index="date",
        columns="hour",
        values="visible_stores",
        aggfunc="median",
    ).sort_index()

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[f"{hour:02d}:00" for hour in pivot.columns],
            y=pivot.index,
            colorscale=[
                [0, "#7f1d1d"],
                [0.45, COLOR_AMBER],
                [1, COLOR_LINE],
            ],
            colorbar={"title": "Mediana"},
            hovertemplate="Fecha %{y}<br>Hora %{x}<br>Mediana %{z:,.0f}<extra></extra>",
        )
    )
    fig = add_chart_layout(fig, 390, "Mapa historico por dia y hora")
    fig.update_xaxes(title="Hora del dia")
    fig.update_yaxes(title="Fecha")
    return fig


def build_distribution_chart(frame: pd.DataFrame, threshold: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=frame["visible_stores"],
            nbinsx=42,
            marker={"color": COLOR_BLUE, "line": {"color": COLOR_BG, "width": 1}},
            name="Frecuencia",
            hovertemplate="%{x:,.0f} visible stores<br>%{y} puntos<extra></extra>",
        )
    )
    fig.add_vline(
        x=threshold,
        line_color=COLOR_AMBER,
        line_dash="dash",
        annotation_text="umbral bajo",
        annotation_font_color=COLOR_AMBER,
    )
    fig = add_chart_layout(fig, 330, "Distribucion de disponibilidad visible")
    fig.update_xaxes(title="Visible stores")
    fig.update_yaxes(title="Puntos")
    return fig


def prepare_events(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
    events = detect_events(frame, frequency="1min", limit=limit)
    if events.empty:
        return events
    display = events.copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display["direction"] = display["direction"].map(localize_direction)
    display["visible_stores"] = display["visible_stores"].round(0).astype("int64")
    display["previous_value"] = display["previous_value"].round(0).astype("int64")
    display["change"] = display["change"].round(0).astype("int64")
    display["abs_change"] = display["abs_change"].round(0).astype("int64")
    return display.rename(
        columns={
            "timestamp": "timestamp",
            "visible_stores": "visible_stores",
            "previous_value": "previous_value",
            "change": "change",
            "abs_change": "abs_change",
            "direction": "direction",
        }
    )


st.set_page_config(
    page_title="Rappi Availability Dashboard",
    page_icon="R",
    layout="wide",
)
apply_theme()

data = load_dashboard_data()
if data.empty:
    st.error("No se encontraron datos. Verifica que la carpeta Archivo (1) tenga CSV exportados.")
    st.stop()

min_time = data["timestamp"].min()
max_time = data["timestamp"].max()

with st.sidebar:
    st.markdown("## Filtros de disponibilidad")
    st.caption("Todos los graficos, tablas y respuestas usan estos filtros.")
    date_range = st.date_input(
        "Rango de fechas",
        value=(min_time.date(), max_time.date()),
        min_value=min_time.date(),
        max_value=max_time.date(),
    )
    hour_range = st.slider("Horas del dia", min_value=0, max_value=23, value=(0, 23), step=1)
    aggregation = st.selectbox("Granularidad de serie", ["1min", "5min", "15min", "1h", "10s raw"], index=1)
    threshold_pct = st.slider("Umbral bajo vs mediana", min_value=30, max_value=95, value=70, step=5)
    event_limit = st.slider("Eventos fuertes", min_value=5, max_value=30, value=15, step=1)
    table_rows = st.slider("Filas en tablas", min_value=10, max_value=100, value=30, step=10)
    show_llm_polish = st.toggle("Pulir respuestas con OpenAI", value=False)
    st.divider()
    st.download_button(
        "Descargar dataset completo",
        data=csv_bytes(data),
        file_name="rappi_availability_full.csv",
        mime="text/csv",
        use_container_width=True,
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered = filter_by_time(data, start=start, end=end)
else:
    filtered = data

filtered = filtered[
    filtered["timestamp"].dt.hour.between(hour_range[0], hour_range[1])
].reset_index(drop=True)

if filtered.empty:
    st.warning("El rango seleccionado no contiene puntos. Ajusta fechas u horas para continuar.")
    st.stop()

kpis = compute_kpis(filtered)
threshold = float(kpis["median_value"]) * (threshold_pct / 100)
low_points = filtered[filtered["visible_stores"] <= threshold].copy()

frequency_map = {"10s raw": None, "1min": "1min", "5min": "5min", "15min": "15min", "1h": "1h"}
plot_frame = filtered[["timestamp", "visible_stores"]].copy()
if frequency_map[aggregation]:
    plot_frame = resample_series(filtered, frequency=frequency_map[aggregation])

events_raw = detect_events(filtered, frequency="1min", limit=event_limit)
events_display = prepare_events(filtered, event_limit)
daily = daily_summary(filtered)

first_value = float(filtered.iloc[0]["visible_stores"])
last_value = float(filtered.iloc[-1]["visible_stores"])
net_change = last_value - first_value
net_change_pct = (net_change / first_value * 100) if first_value else 0.0
best_day = daily.sort_values("median_visible_stores", ascending=False).iloc[0]
worst_day = daily.sort_values("median_visible_stores", ascending=True).iloc[0]

render_hero(filtered, int(kpis["duplicate_points"]), aggregation)

st.markdown(
    f"""
    <div class="metric-grid">
        {render_metric("Puntos historicos", format_number(kpis["points"]), "timestamps despues de filtros")}
        {render_metric("Ultimo valor", format_compact(kpis["current_value"]), f"<strong>{format_pct(net_change_pct)}</strong> vs inicio del rango")}
        {render_metric("Mediana visible", format_compact(kpis["median_value"]), f"base para umbral bajo: {format_compact(threshold)}", COLOR_BLUE)}
        {render_metric("Punto minimo", format_compact(kpis["minimum_value"]), f"{pd.Timestamp(kpis['minimum_timestamp']).strftime('%Y-%m-%d %H:%M:%S')}", COLOR_RED)}
        {render_metric("Punto maximo", format_compact(kpis["maximum_value"]), f"{pd.Timestamp(kpis['maximum_timestamp']).strftime('%Y-%m-%d %H:%M:%S')}", COLOR_AMBER)}
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="insight-strip">
        <div class="insight"><strong>Mejor dia por mediana</strong>{best_day['date']} con {format_compact(best_day['median_visible_stores'])} visible stores.</div>
        <div class="insight"><strong>Dia mas debil por mediana</strong>{worst_day['date']} con {format_compact(worst_day['median_visible_stores'])} visible stores.</div>
        <div class="insight"><strong>Puntos bajo umbral</strong>{format_number(len(low_points))} puntos quedaron en o debajo de {threshold_pct}% de la mediana filtrada.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Historico de disponibilidad")
st.markdown('<p class="section-kicker">Linea principal con mediana movil, umbral bajo y marcadores de eventos fuertes.</p>', unsafe_allow_html=True)
st.plotly_chart(
    build_timeline_chart(plot_frame, events_raw, threshold, aggregation),
    use_container_width=True,
)

left, right = st.columns([1.08, 1])
with left:
    st.plotly_chart(build_daily_chart(daily), use_container_width=True)
with right:
    st.plotly_chart(build_hourly_heatmap(filtered), use_container_width=True)

lower_left, lower_right = st.columns([.92, 1.08])
with lower_left:
    st.plotly_chart(build_distribution_chart(filtered, threshold), use_container_width=True)
with lower_right:
    st.subheader("Eventos de mayor variacion")
    st.markdown('<p class="section-kicker">Ranking de cambios minuto a minuto por magnitud absoluta.</p>', unsafe_allow_html=True)
    if events_display.empty:
        st.info("No hay suficientes puntos para detectar eventos en este rango.")
    else:
        st.dataframe(
            events_display[["timestamp", "direction", "previous_value", "visible_stores", "change", "abs_change"]],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Descargar eventos",
            data=csv_bytes(events_display),
            file_name="rappi_availability_events.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()
tab_daily, tab_low, tab_raw, tab_chat = st.tabs(
    ["Tabla diaria", "Baja disponibilidad", "Datos historicos", "Chat semantico"]
)

with tab_daily:
    st.subheader("Tabla historica diaria")
    st.markdown('<p class="section-kicker">Mediana, promedio, minimo y maximo por fecha para comparar comportamiento historico.</p>', unsafe_allow_html=True)
    daily_display = daily.copy()
    st.dataframe(daily_display, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar resumen diario",
        data=csv_bytes(daily_display),
        file_name="rappi_availability_daily_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )

with tab_low:
    st.subheader("Puntos de baja disponibilidad")
    st.markdown(
        f'<p class="section-kicker">Primeras {table_rows} observaciones en o debajo del umbral configurado.</p>',
        unsafe_allow_html=True,
    )
    low_display = low_points.sort_values("visible_stores").head(table_rows).copy()
    if low_display.empty:
        st.info("No hay puntos por debajo del umbral seleccionado.")
    else:
        low_display["timestamp"] = low_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(
            low_display[["timestamp", "visible_stores", "metric", "observations", "source_files"]],
            use_container_width=True,
            hide_index=True,
        )

with tab_raw:
    st.subheader("Muestra de datos historicos filtrados")
    st.markdown('<p class="section-kicker">Tabla auditable para revisar la serie que alimenta los graficos.</p>', unsafe_allow_html=True)
    raw_display = filtered.tail(table_rows).copy()
    raw_display["timestamp"] = raw_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(
        raw_display[["timestamp", "visible_stores", "metric", "observations", "source_files"]],
        use_container_width=True,
        hide_index=True,
    )

with tab_chat:
    st.subheader("Chatbot semantico")
    st.markdown(
        '<p class="section-kicker">Responde sobre el mismo subconjunto filtrado que ves en el dashboard.</p>',
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Puedo responder sobre minimos, maximos, tendencias, eventos y resumen diario.",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    with st.form("availability_question", clear_on_submit=True):
        prompt = st.text_input("Pregunta sobre la disponibilidad", placeholder="Ej: ¿Que dia tuvo mejor mediana?")
        submitted = st.form_submit_button("Preguntar")

    if submitted and prompt.strip():
        st.session_state.messages.append({"role": "user", "content": prompt})
        response = answer_question(prompt, filtered, use_llm=show_llm_polish)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
