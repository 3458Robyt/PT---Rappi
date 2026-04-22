import json

import pandas as pd

from rappi_availability import semantic_chat
from rappi_availability.semantic_chat import answer_question, build_ai_briefing, classify_intent


def sample_frame():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-02-01 08:00:00",
                    "2026-02-01 08:01:00",
                    "2026-02-01 08:02:00",
                    "2026-02-02 08:00:00",
                ]
            ),
            "visible_stores": [100.0, 50.0, 150.0, 200.0],
            "metric": ["synthetic_monitoring_visible_stores"] * 4,
            "observations": [1, 1, 1, 1],
        }
    )


def test_classify_intent_understands_spanish_minimum_question():
    assert classify_intent("¿Cuál fue el peor momento de disponibilidad?") == "minimum"


def test_answer_minimum_question_mentions_value_and_timestamp():
    answer = answer_question("¿Cuál fue el mínimo?", sample_frame())

    assert "50" in answer
    assert "2026-02-01 08:01:00" in answer


def test_answer_trend_question_mentions_start_and_end_values():
    answer = answer_question("Dame la tendencia general", sample_frame())

    assert "100" in answer
    assert "200" in answer


def test_unknown_question_returns_capabilities():
    answer = answer_question("Explícame el color del logo", sample_frame())

    assert "Puedo responder" in answer


def test_daily_question_takes_precedence_over_generic_best_word():
    answer = answer_question("¿Qué día tuvo mejor mediana?", sample_frame())

    assert "mejor día" in answer
    assert "2026-02-02" in answer


def test_classify_intent_understands_slo_and_risk_question():
    assert classify_intent("¿Cómo está el SLO y el error budget?") == "risk"


def test_answer_risk_question_mentions_sli_budget_and_incidents():
    answer = answer_question("¿Cómo está el riesgo operativo?", sample_frame())

    assert "SLI operativo" in answer
    assert "error budget" in answer
    assert "incidente" in answer


def test_build_ai_briefing_works_without_gemini_key():
    briefing = build_ai_briefing(sample_frame(), use_llm=False)

    assert "SLI operativo" in briefing
    assert "MTTR" in briefing
    assert "umbral saludable" in briefing


def test_gemini_api_key_ignores_documentation_placeholder(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "replace_me")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert semantic_chat._gemini_api_key() is None


def test_answer_uses_gemini_to_polish_when_enabled(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Respuesta pulida por Gemini."}]
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(semantic_chat, "urlopen", fake_urlopen, raising=False)

    answer = semantic_chat.answer_question("¿Cuál fue el mínimo?", sample_frame(), use_llm=True)

    assert answer == "Respuesta pulida por Gemini."
    assert "gemini-flash-latest:generateContent" in captured["url"]
    assert captured["headers"]["X-goog-api-key"] == "test-key"
    assert "Respuesta base verificada" in captured["body"]["contents"][0]["parts"][0]["text"]
    assert captured["timeout"] == 20


def test_answer_accepts_explicit_gemini_key_without_environment(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Pulido con clave temporal."}]
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        return FakeResponse()

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(semantic_chat, "urlopen", fake_urlopen, raising=False)

    answer = semantic_chat.answer_question(
        "¿Cuál fue el mínimo?",
        sample_frame(),
        use_llm=True,
        gemini_api_key="temporary-key",
    )

    assert answer == "Pulido con clave temporal."
    assert captured["headers"]["X-goog-api-key"] == "temporary-key"
