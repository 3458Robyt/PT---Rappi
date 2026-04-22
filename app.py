from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rappi_availability.load_data import load_all_availability_data
from rappi_availability.metrics import (
    daily_summary,
    detect_events,
    filter_by_time,
    resample_series,
)
from rappi_availability.risk_model import compute_risk_model
from rappi_availability.semantic_chat import answer_question, build_ai_briefing


DATA_DIR = Path("Archivo (1)")
PROCESSED_PATH = Path("data/processed/availability_long.csv")

COLOR_BG = "#07100c"
COLOR_PANEL = "#0d1712"
COLOR_PANEL_2 = "#111f18"
COLOR_TEXT = "#f2fbf5"
COLOR_MUTED = "#96a99e"
COLOR_BORDER = "#24362e"
COLOR_GREEN = "#15d67b"
COLOR_BLUE = "#64c7f2"
COLOR_AMBER = "#f5b84b"
COLOR_RED = "#ff5d6c"
COLOR_PURPLE = "#9b8cff"

TABLE_STYLE = {
    "overflowX": "auto",
    "border": f"1px solid {COLOR_BORDER}",
    "borderRadius": "8px",
}
TABLE_HEADER_STYLE = {
    "backgroundColor": COLOR_PANEL_2,
    "color": COLOR_TEXT,
    "border": f"1px solid {COLOR_BORDER}",
    "fontWeight": "800",
}
TABLE_CELL_STYLE = {
    "backgroundColor": "#09130f",
    "color": COLOR_TEXT,
    "border": f"1px solid {COLOR_BORDER}",
    "fontFamily": "Inter, system-ui, sans-serif",
    "fontSize": "13px",
    "minWidth": "110px",
    "maxWidth": "260px",
    "whiteSpace": "normal",
    "height": "auto",
}


@lru_cache(maxsize=1)
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


def format_pct(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.1f}%"


def format_minutes(value: object) -> str:
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        minutes = 0.0
    if minutes >= 60:
        return f"{minutes / 60:.1f}h"
    return f"{minutes:.0f}m"


def timestamp_text(value: object, fallback: str = "sin ventana") -> str:
    if value is None or pd.isna(value):
        return fallback
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M")


def filter_frame(data: pd.DataFrame, start_date: str, end_date: str, hour_range: list[int]) -> pd.DataFrame:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered = filter_by_time(data, start=start, end=end)
    return filtered[
        filtered["timestamp"].dt.hour.between(int(hour_range[0]), int(hour_range[1]))
    ].reset_index(drop=True)


def chart_layout(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.02, "font": {"size": 17, "color": COLOR_TEXT}},
        height=height,
        paper_bgcolor=COLOR_PANEL,
        plot_bgcolor=COLOR_PANEL,
        font={"family": "Inter, Fira Sans, system-ui, sans-serif", "color": COLOR_TEXT},
        margin={"l": 24, "r": 24, "t": 58, "b": 34},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "y": 1.08,
            "x": 0.02,
            "font": {"color": COLOR_MUTED},
        },
    )
    fig.update_xaxes(
        gridcolor="rgba(150,169,158,.14)",
        linecolor=COLOR_BORDER,
        tickfont={"color": COLOR_MUTED},
        title_font={"color": COLOR_MUTED},
    )
    fig.update_yaxes(
        gridcolor="rgba(150,169,158,.14)",
        linecolor=COLOR_BORDER,
        tickfont={"color": COLOR_MUTED},
        title_font={"color": COLOR_MUTED},
    )
    return fig


def make_timeline_figure(plot_frame: pd.DataFrame, incidents: pd.DataFrame, threshold: float, aggregation: str) -> go.Figure:
    fig = go.Figure()
    if plot_frame.empty:
        return chart_layout(fig, "Runway temporal de disponibilidad", 470)

    for _, incident in incidents.iterrows():
        fig.add_vrect(
            x0=incident["start"],
            x1=incident["end"] + pd.Timedelta(minutes=1),
            fillcolor="rgba(255,93,108,.16)",
            line_width=0,
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=plot_frame["timestamp"],
            y=plot_frame["visible_stores"],
            mode="lines",
            name="Visible stores",
            line={"color": COLOR_GREEN, "width": 2.6},
            fill="tozeroy",
            fillcolor="rgba(21,214,123,.10)",
            hovertemplate="%{x}<br>%{y:,.0f} visible stores<extra></extra>",
        )
    )

    rolling = plot_frame.copy()
    rolling["moving_median"] = rolling["visible_stores"].rolling(12, min_periods=1).median()
    fig.add_trace(
        go.Scatter(
            x=rolling["timestamp"],
            y=rolling["moving_median"],
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
        annotation_text=f"Umbral saludable: {format_compact(threshold)}",
        annotation_font_color=COLOR_AMBER,
    )
    fig = chart_layout(fig, f"Runway temporal de disponibilidad ({aggregation})", 470)
    fig.update_yaxes(title="Visible stores")
    fig.update_xaxes(title="Timestamp")
    return fig


def make_budget_figure(summary: dict[str, object]) -> go.Figure:
    remaining = float(summary["error_budget_remaining_pct"])
    used = float(summary["error_budget_used_pct"])
    bar_color = COLOR_GREEN if remaining >= 50 else COLOR_AMBER if remaining > 0 else COLOR_RED
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=remaining,
            number={"suffix": "%", "font": {"color": COLOR_TEXT, "size": 34}},
            title={"text": f"Budget restante<br><span style='font-size:12px;color:{COLOR_MUTED}'>usado {used:.1f}%</span>"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": COLOR_MUTED},
                "bar": {"color": bar_color, "thickness": 0.32},
                "bgcolor": "rgba(255,255,255,.05)",
                "borderwidth": 1,
                "bordercolor": COLOR_BORDER,
                "steps": [
                    {"range": [0, 20], "color": "rgba(255,93,108,.28)"},
                    {"range": [20, 50], "color": "rgba(245,184,75,.22)"},
                    {"range": [50, 100], "color": "rgba(21,214,123,.18)"},
                ],
            },
        )
    )
    return chart_layout(fig, "Error budget operativo", 290)


def make_incident_rank_figure(incidents: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if incidents.empty:
        return chart_layout(fig, "Incidentes por duracion", 330)

    ranked = incidents.sort_values(["duration_minutes", "depth_pct"], ascending=[True, True]).tail(10)
    labels = ranked.apply(
        lambda row: f"#{int(row['incident_id'])} · {pd.Timestamp(row['start']).strftime('%m-%d %H:%M')}",
        axis=1,
    )
    fig.add_trace(
        go.Bar(
            x=ranked["duration_minutes"],
            y=labels,
            orientation="h",
            marker={
                "color": ranked["depth_pct"],
                "colorscale": [[0, COLOR_AMBER], [1, COLOR_RED]],
                "line": {"color": COLOR_BORDER, "width": 1},
                "colorbar": {"title": "Profundidad %"},
            },
            customdata=ranked[["min_visible_stores", "severity"]],
            hovertemplate=(
                "Duracion %{x} min<br>Minimo %{customdata[0]:,.0f}"
                "<br>Severidad %{customdata[1]}<extra></extra>"
            ),
        )
    )
    fig = chart_layout(fig, "Incidentes por duracion", 330)
    fig.update_xaxes(title="Minutos bajo umbral")
    fig.update_yaxes(title="")
    return fig


def make_heatmap_figure(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if frame.empty:
        return chart_layout(fig, "Mapa dia-hora", 330)

    hourly = frame.copy()
    hourly["date"] = hourly["timestamp"].dt.date.astype(str)
    hourly["hour"] = hourly["timestamp"].dt.hour
    pivot = hourly.pivot_table(
        index="date",
        columns="hour",
        values="visible_stores",
        aggfunc="median",
    ).sort_index()

    fig.add_trace(
        go.Heatmap(
            z=pivot.values,
            x=[f"{hour:02d}:00" for hour in pivot.columns],
            y=pivot.index,
            colorscale=[[0, COLOR_RED], [0.45, COLOR_AMBER], [1, COLOR_GREEN]],
            colorbar={"title": "Mediana", "tickfont": {"color": COLOR_MUTED}},
            hovertemplate="Fecha %{y}<br>Hora %{x}<br>Mediana %{z:,.0f}<extra></extra>",
        )
    )
    fig = chart_layout(fig, "Mapa dia-hora", 330)
    fig.update_xaxes(title="Hora")
    fig.update_yaxes(title="Dia")
    return fig


def make_distribution_figure(series: pd.DataFrame, threshold: float, summary: dict[str, object]) -> go.Figure:
    fig = go.Figure()
    if series.empty:
        return chart_layout(fig, "Distribucion P10/P50/P90", 330)

    fig.add_trace(
        go.Histogram(
            x=series["visible_stores"],
            nbinsx=44,
            marker={"color": COLOR_PURPLE, "line": {"color": COLOR_PANEL, "width": 1}},
            name="Frecuencia",
            hovertemplate="%{x:,.0f} visible stores<br>%{y} minutos<extra></extra>",
        )
    )
    fig.add_vline(x=threshold, line_color=COLOR_AMBER, line_dash="dash", annotation_text="umbral")
    fig.add_vline(x=summary["p10_visible_stores"], line_color=COLOR_RED, line_dash="dot", annotation_text="P10")
    fig.add_vline(x=summary["p50_visible_stores"], line_color=COLOR_BLUE, line_dash="dot", annotation_text="P50")
    fig.add_vline(x=summary["p90_visible_stores"], line_color=COLOR_GREEN, line_dash="dot", annotation_text="P90")
    fig = chart_layout(fig, "Distribucion P10/P50/P90", 330)
    fig.update_xaxes(title="Visible stores")
    fig.update_yaxes(title="Minutos")
    return fig


def metric_cell(label: str, value: str, detail: str, tone: str = "green") -> html.Div:
    return html.Div(
        [
            html.Div(label, className="metric-label"),
            html.Div(value, className="metric-value"),
            html.Div(detail, className="metric-detail"),
        ],
        className=f"metric-cell tone-{tone}",
    )


def format_incident_table(incidents: pd.DataFrame) -> list[dict[str, object]]:
    if incidents.empty:
        return []
    display = incidents.copy()
    for column in ["start", "end", "recovery_timestamp"]:
        display[column] = display[column].map(lambda value: timestamp_text(value, "sin recuperar"))
    return display[
        [
            "incident_id",
            "severity",
            "start",
            "end",
            "duration_minutes",
            "min_visible_stores",
            "median_visible_stores",
            "depth_pct",
            "recovery_velocity_per_min",
        ]
    ].to_dict("records")


def format_raw_table(frame: pd.DataFrame, rows: int = 40) -> list[dict[str, object]]:
    if frame.empty:
        return []
    display = frame.tail(rows).copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return display[["timestamp", "visible_stores", "metric", "observations", "source_files"]].to_dict("records")


def make_hero(summary: dict[str, object], filtered: pd.DataFrame, healthy_pct: int, slo_pct: int) -> html.Div:
    start = filtered["timestamp"].min()
    end = filtered["timestamp"].max()
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Rappi Availability Risk Tower", className="product-mark"),
                    html.H1("Control de riesgo operativo"),
                    html.P(
                        "SLI derivado de tiendas visibles: identifica episodios bajo umbral, consumo de error budget y recuperacion.",
                        className="hero-copy",
                    ),
                ],
                className="hero-title",
            ),
            html.Div(
                [
                    html.Div(summary["status"], className=f"status-pill status-{str(summary['status']).lower().replace(' ', '-')}"),
                    html.Div(f"{timestamp_text(start)} - {timestamp_text(end)}", className="meta-line"),
                    html.Div(f"Umbral {healthy_pct}% de mediana · SLO {slo_pct}%", className="meta-line"),
                ],
                className="hero-status",
            ),
        ],
        className="mission-header",
    )


def create_app() -> Dash:
    data = load_dashboard_data()
    if data.empty:
        min_date = max_date = pd.Timestamp.today().date()
    else:
        min_date = data["timestamp"].min().date()
        max_date = data["timestamp"].max().date()

    app = Dash(__name__, title="Rappi Availability Risk Tower")
    app.layout = html.Div(
        [
            dcc.Store(id="boot-marker", data="risk-tower"),
            html.Div(
                [
                    html.A("Saltar al runway", href="#runway", className="skip-link"),
                    html.A("Saltar al briefing", href="#ai-briefing", className="skip-link"),
                    html.A("Saltar a tablas", href="#tables", className="skip-link"),
                ],
                className="skip-region",
            ),
            html.Main(
                [
                    html.Aside(
                        [
                            html.Div("Mission Controls", className="rail-title"),
                            html.Label("Rango de fechas"),
                            dcc.DatePickerRange(
                                id="date-range",
                                min_date_allowed=min_date,
                                max_date_allowed=max_date,
                                start_date=min_date,
                                end_date=max_date,
                                display_format="YYYY-MM-DD",
                                className="date-picker",
                            ),
                            html.Label("Horas del dia"),
                            dcc.RangeSlider(
                                id="hour-range",
                                min=0,
                                max=23,
                                value=[0, 23],
                                marks={0: "00", 6: "06", 12: "12", 18: "18", 23: "23"},
                                allowCross=False,
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Label("Granularidad visual"),
                            dcc.Dropdown(
                                id="aggregation",
                                value="5min",
                                clearable=False,
                                options=[
                                    {"label": "1 minuto", "value": "1min"},
                                    {"label": "5 minutos", "value": "5min"},
                                    {"label": "15 minutos", "value": "15min"},
                                    {"label": "1 hora", "value": "1h"},
                                    {"label": "Raw", "value": "raw"},
                                ],
                            ),
                            html.Label("Umbral saludable"),
                            dcc.Slider(
                                id="healthy-threshold",
                                min=40,
                                max=95,
                                step=5,
                                value=70,
                                marks={40: "40%", 70: "70%", 95: "95%"},
                            ),
                            html.Label("Objetivo SLO"),
                            dcc.Slider(
                                id="slo-target",
                                min=85,
                                max=99,
                                step=1,
                                value=95,
                                marks={85: "85%", 95: "95%", 99: "99%"},
                            ),
                            html.Div("Gemini", className="rail-title rail-title-secondary"),
                            dcc.Input(
                                id="gemini-key",
                                type="password",
                                placeholder="Gemini API key temporal",
                                className="text-input",
                                value=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
                            ),
                            dcc.Checklist(
                                id="gemini-polish",
                                options=[{"label": "Pulir briefing y chat con Gemini", "value": "on"}],
                                value=[],
                                className="checklist",
                            ),
                        ],
                        className="control-rail",
                    ),
                    html.Section(
                        [
                            html.Div(id="hero-status"),
                            html.Div(id="risk-metrics", className="risk-strip"),
                            html.Div(
                                [
                                    html.Div(
                                        dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
                                        id="runway",
                                        className="runway-panel",
                                    ),
                                    html.Div(
                                        [
                                            dcc.Graph(id="budget-chart", config={"displayModeBar": False}),
                                            html.Div(id="ai-briefing", className="briefing-text"),
                                        ],
                                        className="briefing-panel",
                                    ),
                                ],
                                className="command-grid",
                            ),
                            html.Div(
                                [
                                    html.Div(dcc.Graph(id="incident-rank-chart", config={"displayModeBar": False}), className="panel"),
                                    html.Div(dcc.Graph(id="heatmap-chart", config={"displayModeBar": False}), className="panel"),
                                    html.Div(dcc.Graph(id="distribution-chart", config={"displayModeBar": False}), className="panel panel-wide"),
                                ],
                                className="drill-grid",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H2("Incident log"),
                                            dash_table.DataTable(
                                                id="incident-table",
                                                columns=[
                                                    {"name": "ID", "id": "incident_id"},
                                                    {"name": "Severidad", "id": "severity"},
                                                    {"name": "Inicio", "id": "start"},
                                                    {"name": "Fin", "id": "end"},
                                                    {"name": "Duracion min", "id": "duration_minutes"},
                                                    {"name": "Min visible", "id": "min_visible_stores"},
                                                    {"name": "Mediana", "id": "median_visible_stores"},
                                                    {"name": "Profundidad %", "id": "depth_pct"},
                                                    {"name": "Recuperacion/min", "id": "recovery_velocity_per_min"},
                                                ],
                                                data=[],
                                                page_size=10,
                                                export_format="csv",
                                                style_as_list_view=True,
                                                style_table=TABLE_STYLE,
                                                style_header=TABLE_HEADER_STYLE,
                                                style_cell=TABLE_CELL_STYLE,
                                            ),
                                        ],
                                        className="table-panel",
                                    ),
                                    html.Div(
                                        [
                                            html.H2("Auditoria de puntos recientes"),
                                            dash_table.DataTable(
                                                id="raw-table",
                                                columns=[
                                                    {"name": "Timestamp", "id": "timestamp"},
                                                    {"name": "Visible stores", "id": "visible_stores"},
                                                    {"name": "Metric", "id": "metric"},
                                                    {"name": "Observations", "id": "observations"},
                                                    {"name": "Source files", "id": "source_files"},
                                                ],
                                                data=[],
                                                page_size=10,
                                                export_format="csv",
                                                style_as_list_view=True,
                                                style_table=TABLE_STYLE,
                                                style_header=TABLE_HEADER_STYLE,
                                                style_cell=TABLE_CELL_STYLE,
                                            ),
                                        ],
                                        className="table-panel",
                                    ),
                                ],
                                id="tables",
                                className="tables-grid",
                            ),
                        ],
                        className="main-workspace",
                    ),
                    html.Aside(
                        [
                            html.Div("AI Analyst", className="rail-title"),
                            html.P(
                                "Pregunta sobre SLO, incidentes, budget, MTTR, recuperacion o cualquier punto del rango filtrado.",
                                className="side-copy",
                            ),
                            dcc.Textarea(
                                id="chat-question",
                                placeholder="Ej: ¿Cuál fue el peor incidente y cuánto budget consumió?",
                                className="question-box",
                            ),
                            html.Button("Preguntar", id="ask-button", className="primary-button", n_clicks=0),
                            html.Div(id="chat-answer", className="chat-answer"),
                        ],
                        className="ai-rail",
                    ),
                ],
                className="tower-shell",
            ),
        ]
    )

    @app.callback(
        Output("hero-status", "children"),
        Output("risk-metrics", "children"),
        Output("timeline-chart", "figure"),
        Output("budget-chart", "figure"),
        Output("incident-rank-chart", "figure"),
        Output("heatmap-chart", "figure"),
        Output("distribution-chart", "figure"),
        Output("incident-table", "data"),
        Output("raw-table", "data"),
        Output("ai-briefing", "children"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        Input("hour-range", "value"),
        Input("aggregation", "value"),
        Input("healthy-threshold", "value"),
        Input("slo-target", "value"),
        Input("gemini-polish", "value"),
        State("gemini-key", "value"),
    )
    def update_dashboard(
        start_date: str,
        end_date: str,
        hour_range: list[int],
        aggregation: str,
        healthy_pct: int,
        slo_pct: int,
        gemini_polish: list[str],
        gemini_key: str,
    ):
        if not start_date or not end_date:
            raise PreventUpdate

        filtered = filter_frame(data, start_date, end_date, hour_range)
        if filtered.empty:
            empty_fig = chart_layout(go.Figure(), "Sin datos en el rango", 330)
            return (
                html.Div("Sin datos para los filtros seleccionados", className="mission-header"),
                [],
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                [],
                "No hay datos en el rango seleccionado.",
            )

        risk = compute_risk_model(filtered, healthy_ratio=healthy_pct / 100, slo_target=slo_pct / 100)
        summary = risk["summary"]
        minute_series = risk["minute_series"]
        incidents = risk["incidents"]

        plot_frame = filtered[["timestamp", "visible_stores"]].copy()
        if aggregation != "raw":
            plot_frame = resample_series(filtered, aggregation)

        metrics = [
            metric_cell("Operational SLI", format_pct(summary["operational_sli_pct"]), f"SLO objetivo {format_pct(summary['slo_target_pct'])}", "green"),
            metric_cell("Error budget", format_pct(summary["error_budget_remaining_pct"]), f"burn {summary['budget_burn_rate']:.2f}x", "amber" if summary["error_budget_remaining_pct"] > 0 else "red"),
            metric_cell("Minutos bajo umbral", format_number(summary["low_minutes"]), f"umbral {format_compact(summary['threshold_value'])}", "red"),
            metric_cell("Incidentes", format_number(summary["incident_count"]), f"MTTR {format_minutes(summary['mttr_minutes'])} · MTBF {format_minutes(summary['mtbf_minutes'])}", "blue"),
            metric_cell("Estabilidad P10/P90", format_compact(summary["p10_p90_spread"]), f"P10 {format_compact(summary['p10_visible_stores'])} · P90 {format_compact(summary['p90_visible_stores'])}", "purple"),
            metric_cell("Recuperacion", format_compact(summary["recovery_velocity_per_min"]), "visible stores por minuto", "green"),
        ]

        use_gemini = "on" in (gemini_polish or []) and bool(gemini_key)
        briefing = build_ai_briefing(filtered, use_llm=use_gemini, gemini_api_key=gemini_key)

        return (
            make_hero(summary, filtered, healthy_pct, slo_pct),
            metrics,
            make_timeline_figure(plot_frame, incidents, float(summary["threshold_value"]), aggregation),
            make_budget_figure(summary),
            make_incident_rank_figure(incidents),
            make_heatmap_figure(filtered),
            make_distribution_figure(minute_series, float(summary["threshold_value"]), summary),
            format_incident_table(incidents),
            format_raw_table(filtered),
            briefing,
        )

    @app.callback(
        Output("chat-answer", "children"),
        Input("ask-button", "n_clicks"),
        State("chat-question", "value"),
        State("date-range", "start_date"),
        State("date-range", "end_date"),
        State("hour-range", "value"),
        State("gemini-polish", "value"),
        State("gemini-key", "value"),
        prevent_initial_call=True,
    )
    def answer_chat(
        n_clicks: int,
        question: str,
        start_date: str,
        end_date: str,
        hour_range: list[int],
        gemini_polish: list[str],
        gemini_key: str,
    ):
        if not n_clicks or not question or not question.strip():
            raise PreventUpdate
        filtered = filter_frame(data, start_date, end_date, hour_range)
        use_gemini = "on" in (gemini_polish or []) and bool(gemini_key)
        answer = answer_question(question, filtered, use_llm=use_gemini, gemini_api_key=gemini_key)
        return html.Div(
            [
                html.Div("Respuesta", className="answer-label"),
                html.P(answer),
            ]
        )

    return app


app = create_app()
server = app.server


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8050"))
    app.run(host="127.0.0.1", port=port, debug=False)
