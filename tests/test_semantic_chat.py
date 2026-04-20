import pandas as pd

from rappi_availability.semantic_chat import answer_question, classify_intent


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
