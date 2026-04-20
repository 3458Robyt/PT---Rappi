from __future__ import annotations

import os
import unicodedata

import pandas as pd

from rappi_availability.metrics import compute_kpis, daily_summary, detect_events


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
    if any(word in text for word in ["dia", "diario", "fecha"]):
        return "daily"
    return "unknown"


def answer_question(question: str, frame: pd.DataFrame, use_llm: bool = False) -> str:
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
    else:
        answer = (
            "Puedo responder sobre mínimos, máximos, promedios, tendencias, "
            "eventos fuertes y resumen diario de la disponibilidad visible."
        )

    return _polish_with_openai(question, answer, use_llm=use_llm)


def _polish_with_openai(question: str, answer: str, use_llm: bool) -> str:
    if not use_llm or not os.getenv("OPENAI_API_KEY"):
        return answer

    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Responde en español, de forma breve, solo con los datos provistos. "
                        "No agregues cifras nuevas."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Pregunta: {question}\nRespuesta base verificada: {answer}",
                },
            ],
        )
        polished = response.output_text.strip()
        return polished or answer
    except Exception:
        return answer
