from __future__ import annotations

import os
import unicodedata
import json
from urllib.request import Request, urlopen

import pandas as pd

from rappi_availability.metrics import compute_kpis, daily_summary, detect_events
from rappi_availability.risk_model import compute_risk_model


def _normalize(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in without_accents if not unicodedata.combining(char))
    return ascii_text.lower()


def _format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _format_timestamp(value: object) -> str:
    if value is None or pd.isna(value):
        return "sin timestamp disponible"
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def classify_intent(question: str) -> str:
    text = _normalize(question)
    if any(word in text for word in ["slo", "riesgo", "budget", "presupuesto", "mttr", "mtbf", "incidente", "recuperacion"]):
        return "risk"
    if any(word in text for word in ["dia", "diario", "fecha"]):
        return "daily"
    if any(word in text for word in ["minimo", "menor", "peor", "caida"]):
        return "minimum"
    if any(word in text for word in ["maximo", "mayor", "mejor", "pico", "alto"]):
        return "maximum"
    if any(word in text for word in ["promedio", "media", "mediana", "resumen", "kpi"]):
        return "summary"
    if any(word in text for word in ["tendencia", "evolucion", "subio", "bajo", "inicio", "final"]):
        return "trend"
    if any(word in text for word in ["anomalia", "evento", "cambio", "salto", "variacion"]):
        return "events"
    return "unknown"


def answer_question(
    question: str,
    frame: pd.DataFrame,
    use_llm: bool = False,
    gemini_api_key: str | None = None,
) -> str:
    if frame.empty:
        return "No hay datos en el filtro actual. Amplía el rango de fechas para poder analizar disponibilidad."

    intent = classify_intent(question)
    kpis = compute_kpis(frame)

    if intent == "minimum":
        answer = (
            "El punto más bajo fue "
            f"{_format_number(kpis['minimum_value'])} visible stores en "
            f"{_format_timestamp(kpis['minimum_timestamp'])}."
        )
    elif intent == "maximum":
        answer = (
            "El punto más alto fue "
            f"{_format_number(kpis['maximum_value'])} visible stores en "
            f"{_format_timestamp(kpis['maximum_timestamp'])}."
        )
    elif intent == "summary":
        answer = (
            f"En el filtro actual hay {_format_number(kpis['points'])} puntos. "
            f"Promedio: {_format_number(kpis['average_value'])}; "
            f"mediana: {_format_number(kpis['median_value'])}; "
            f"mínimo: {_format_number(kpis['minimum_value'])}; "
            f"máximo: {_format_number(kpis['maximum_value'])}."
        )
    elif intent == "trend":
        ordered = frame.sort_values("timestamp")
        first = ordered.iloc[0]
        last = ordered.iloc[-1]
        change = float(last["visible_stores"] - first["visible_stores"])
        direction = "subió" if change >= 0 else "bajó"
        answer = (
            f"La serie empezó en {_format_number(first['visible_stores'])} visible stores "
            f"el {_format_timestamp(first['timestamp'])} y terminó en "
            f"{_format_number(last['visible_stores'])} el {_format_timestamp(last['timestamp'])}. "
            f"En neto {direction} {_format_number(abs(change))}."
        )
    elif intent == "events":
        events = detect_events(frame, frequency="1min", limit=3)
        if events.empty:
            answer = "No hay suficientes puntos para detectar cambios relevantes en el filtro actual."
        else:
            parts = []
            for _, event in events.iterrows():
                parts.append(
                    f"{_format_timestamp(event['timestamp'])}: {event['direction']} "
                    f"de {_format_number(abs(event['change']))}"
                )
            answer = "Los cambios más fuertes fueron: " + "; ".join(parts) + "."
    elif intent == "daily":
        daily = daily_summary(frame)
        best = daily.sort_values("median_visible_stores", ascending=False).iloc[0]
        worst = daily.sort_values("median_visible_stores", ascending=True).iloc[0]
        answer = (
            f"Por mediana diaria, el mejor día fue {best['date']} con "
            f"{_format_number(best['median_visible_stores'])}. "
            f"El día más débil fue {worst['date']} con "
            f"{_format_number(worst['median_visible_stores'])}."
        )
    elif intent == "risk":
        answer = _build_risk_answer(frame)
    else:
        answer = (
            "Puedo responder sobre mínimos, máximos, promedios, tendencias, "
            "eventos fuertes, SLO, error budget, incidentes y resumen diario de la disponibilidad visible."
        )

    return _polish_with_gemini(question, answer, use_llm=use_llm, api_key=gemini_api_key)


def _build_risk_answer(frame: pd.DataFrame) -> str:
    risk = compute_risk_model(frame)
    summary = risk["summary"]
    return (
        f"SLI operativo: {summary['operational_sli_pct']:.1f}% frente a un objetivo "
        f"SLO de {summary['slo_target_pct']:.1f}%. "
        f"El error budget restante es {summary['error_budget_remaining_pct']:.1f}% "
        f"con burn rate {summary['budget_burn_rate']:.2f}x. "
        f"Se detectaron {summary['incident_count']} incidente(s), "
        f"{summary['low_minutes']} minutos bajo umbral y MTTR de "
        f"{summary['mttr_minutes']:.1f} minutos."
    )


def build_ai_briefing(
    frame: pd.DataFrame,
    use_llm: bool = False,
    gemini_api_key: str | None = None,
) -> str:
    if frame.empty:
        return "No hay datos en el rango seleccionado para generar un briefing operativo."

    risk = compute_risk_model(frame)
    summary = risk["summary"]
    worst_start = summary["worst_incident_start"]
    if worst_start is None:
        worst_text = "no se detectaron incidentes bajo el umbral saludable"
    else:
        worst_text = (
            f"la peor ventana inició en {_format_timestamp(worst_start)} y duró "
            f"{summary['worst_incident_duration_minutes']} minutos"
        )

    answer = (
        f"SLI operativo de {summary['operational_sli_pct']:.1f}% con "
        f"{summary['low_minutes']} minutos bajo el umbral saludable de "
        f"{_format_number(summary['threshold_value'])} visible stores. "
        f"Estado: {summary['status']}; error budget restante "
        f"{summary['error_budget_remaining_pct']:.1f}%; burn rate "
        f"{summary['budget_burn_rate']:.2f}x. "
        f"Hubo {summary['incident_count']} incidente(s), MTTR "
        f"{summary['mttr_minutes']:.1f} minutos y MTBF "
        f"{summary['mtbf_minutes']:.1f} minutos. "
        f"Detalle clave: {worst_text}."
    )
    return _polish_with_gemini(
        "Resume el riesgo operativo del rango seleccionado.",
        answer,
        use_llm=use_llm,
        api_key=gemini_api_key,
    )


def _gemini_api_key(api_key: str | None = None) -> str | None:
    if api_key:
        return api_key
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _build_gemini_prompt(question: str, answer: str) -> str:
    return (
        "Responde en español, de forma breve, ejecutiva y clara. "
        "Usa solamente la respuesta base verificada; no agregues cifras, fechas ni supuestos nuevos.\n\n"
        f"Pregunta del usuario: {question}\n"
        f"Respuesta base verificada: {answer}"
    )


def _extract_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    texts = [str(part.get("text", "")).strip() for part in parts if part.get("text")]
    return " ".join(texts).strip()


def _polish_with_gemini(
    question: str,
    answer: str,
    use_llm: bool,
    api_key: str | None = None,
) -> str:
    api_key = _gemini_api_key(api_key)
    if not use_llm or not api_key:
        return answer

    try:
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": _build_gemini_prompt(question, answer),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 180,
            },
        }
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": api_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        polished = _extract_gemini_text(payload)
        return polished or answer
    except Exception:
        return answer
