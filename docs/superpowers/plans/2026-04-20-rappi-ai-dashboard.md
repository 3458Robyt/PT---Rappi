# Rappi AI Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app for the Rappi AI Interns 2026 technical test: a clear availability dashboard, a semantic chatbot over the shown data, source code, and a short presentation explaining AI tool usage.

**Architecture:** Use a small Python + Streamlit app so the 1.5 hour scope stays focused on insight quality instead of framework setup. Normalize the exported wide SignalFx-style CSV files into one long time-series dataset, compute dashboard metrics from that cleaned frame, and route chatbot questions to deterministic analytical intents with optional OpenAI answer polishing when an API key is available.

**Tech Stack:** Python 3.11+, Streamlit, pandas, Plotly, pytest, optional OpenAI Python SDK.

---

## Source Brief Understanding

The Word document `Prueba AI Interns 2026 (2) (2).docx` asks for:

- A local functional web app.
- A dashboard that visualizes historical store availability with charts, tables, key metrics, and filters.
- An integrated semantic chatbot that answers questions about the data shown in the dashboard.
- A repository or folder with source code.
- A presentation explaining which AI tools were used, how they were used, and why those decisions were made.
- Evaluation weights: AI usage 30%, functionality 25%, creativity and UX 20%, code quality 10%, presentation 15%.

Observed dataset facts from `Archivo (1)`:

- 201 CSV files, excluding `__MACOSX`.
- Every CSV has one row for `Plot name = NOW` and `metric (sf_metric) = synthetic_monitoring_visible_stores`.
- Columns after the first four metadata columns are timestamps every 10 seconds.
- The combined raw export has 69,128 numeric points from `2026-02-01 06:11:20` through `2026-02-11 15:00:00` America/Bogota time.
- Some export windows overlap; the ingestion layer must deduplicate repeated timestamps.
- The values contain zeros and very high spikes, so the dashboard must expose raw values, daily medians, and event tables instead of hiding data quality concerns.

## Assumptions

- The provided files are an aggregated availability time series, not per-store event logs. The app will label the metric as "visible stores" and will not invent individual store IDs.
- The app must run locally on Windows from the `Rappi PT` folder.
- OpenAI API usage is optional at runtime; the chatbot must still work without secrets for a local demo.
- The presentation can be a Markdown deck outline in the repo because the brief does not require a `.pptx`; it can be spoken from or converted to slides.

## File Structure

- Create: `requirements.txt` - locked runtime dependencies for the demo.
- Create: `pyproject.toml` - pytest path configuration and package metadata.
- Create: `src/rappi_availability/__init__.py` - package marker.
- Create: `src/rappi_availability/load_data.py` - CSV discovery, timestamp parsing, wide-to-long normalization, deduplication, processed CSV writing.
- Create: `src/rappi_availability/metrics.py` - KPI, daily summary, resampling, and event detection logic.
- Create: `src/rappi_availability/semantic_chat.py` - Spanish question intent classification, deterministic answers, optional OpenAI answer polishing.
- Create: `scripts/build_dataset.py` - command-line preprocessing entry point.
- Create: `app.py` - Streamlit dashboard and chatbot UI.
- Create: `tests/fixtures/availability_sample.csv` - small wide-format fixture matching the real export format.
- Create: `tests/test_load_data.py` - parser and loader tests.
- Create: `tests/test_metrics.py` - KPI and event tests.
- Create: `tests/test_semantic_chat.py` - chatbot routing and answer tests.
- Create: `README.md` - local setup, demo flow, AI usage explanation.
- Create: `presentation/rappi-ai-dashboard.md` - short presentation content for the VP Tech demo.
- Create: `data/processed/.gitkeep` - keeps processed output directory present.

---

### Task 1: Bootstrap Project

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `src/rappi_availability/__init__.py`
- Create: `tests/fixtures/availability_sample.csv`
- Create: `data/processed/.gitkeep`

- [ ] **Step 1: Initialize git if the folder is not already a repository**

Run:

```powershell
git status
```

Expected if the folder is not a repository: `fatal: not a git repository`.

Run only when git is missing:

```powershell
git init
```

Expected: Git initializes an empty repository in `Rappi PT`.

- [ ] **Step 2: Create dependency file**

Create `requirements.txt`:

```txt
streamlit==1.45.1
pandas==2.2.3
plotly==5.24.1
openai==1.78.1
pytest==8.3.5
```

- [ ] **Step 3: Create package and pytest configuration**

Create `pyproject.toml`:

```toml
[project]
name = "rappi-availability-dashboard"
version = "0.1.0"
description = "Local dashboard and semantic chatbot for the Rappi AI Interns 2026 technical test."
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
```

Create `src/rappi_availability/__init__.py`:

```python
"""Rappi availability dashboard package."""
```

- [ ] **Step 4: Create fixture data that matches the export shape**

Create `tests/fixtures/availability_sample.csv`:

```csv
Plot name,metric (sf_metric),Value Prefix,Value Suffix,Sun Feb 01 2026 06:59:40 GMT-0500 (hora estándar de Colombia),Sun Feb 01 2026 06:59:50 GMT-0500 (hora estándar de Colombia),Sun Feb 01 2026 07:00:00 GMT-0500 (hora estándar de Colombia),Sun Feb 01 2026 07:00:10 GMT-0500 (hora estándar de Colombia)
NOW,synthetic_monitoring_visible_stores,,,100,120,90,150
```

Create `data/processed/.gitkeep` as an empty file.

- [ ] **Step 5: Install dependencies**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Expected: pip installs Streamlit, pandas, Plotly, OpenAI SDK, and pytest without errors.

- [ ] **Step 6: Commit bootstrap**

Run:

```powershell
git add requirements.txt pyproject.toml src/rappi_availability/__init__.py tests/fixtures/availability_sample.csv data/processed/.gitkeep
git commit -m "chore: bootstrap rappi dashboard project"
```

Expected: one commit with project scaffolding.

---

### Task 2: Data Loading and Normalization

**Files:**
- Create: `tests/test_load_data.py`
- Create: `src/rappi_availability/load_data.py`
- Create: `scripts/build_dataset.py`
- Modify: `data/processed/.gitkeep`

- [ ] **Step 1: Write failing parser and loader tests**

Create `tests/test_load_data.py`:

```python
from pathlib import Path

import pandas as pd

from rappi_availability.load_data import (
    load_all_availability_data,
    load_wide_csv,
    parse_export_timestamp,
)


FIXTURE = Path(__file__).parent / "fixtures" / "availability_sample.csv"


def test_parse_export_timestamp_strips_colombia_timezone_label():
    timestamp = parse_export_timestamp(
        "Sun Feb 01 2026 06:59:40 GMT-0500 (hora estándar de Colombia)"
    )

    assert timestamp == pd.Timestamp("2026-02-01 06:59:40")


def test_load_wide_csv_turns_timestamp_columns_into_rows():
    frame = load_wide_csv(FIXTURE)

    assert list(frame.columns) == [
        "timestamp",
        "visible_stores",
        "metric",
        "plot_name",
        "source_file",
    ]
    assert len(frame) == 4
    assert frame["visible_stores"].tolist() == [100.0, 120.0, 90.0, 150.0]
    assert frame["metric"].unique().tolist() == ["synthetic_monitoring_visible_stores"]


def test_load_all_availability_data_deduplicates_overlapping_timestamps(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    second.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    frame = load_all_availability_data(tmp_path)

    assert len(frame) == 4
    assert frame["observations"].tolist() == [2, 2, 2, 2]
    assert frame["visible_stores"].tolist() == [100.0, 120.0, 90.0, 150.0]
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_load_data.py -q
```

Expected: FAIL because `rappi_availability.load_data` does not exist.

- [ ] **Step 3: Implement data loading**

Create `src/rappi_availability/load_data.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ID_COLUMNS = ["Plot name", "metric (sf_metric)", "Value Prefix", "Value Suffix"]
OUTPUT_COLUMNS = ["timestamp", "visible_stores", "metric", "plot_name", "source_file"]


def parse_export_timestamp(label: str) -> pd.Timestamp:
    timestamp_text = re.sub(r"\s+GMT[+-]\d{4}.*$", "", label.strip())
    return pd.to_datetime(timestamp_text, format="%a %b %d %Y %H:%M:%S")


def iter_csv_files(input_dir: Path | str) -> list[Path]:
    root = Path(input_dir)
    return sorted(
        path
        for path in root.glob("*.csv")
        if path.is_file() and not path.name.startswith("._")
    )


def load_wide_csv(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path)
    raw = pd.read_csv(csv_path)
    if raw.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    row = raw.iloc[0]
    time_columns = [column for column in raw.columns if column not in ID_COLUMNS]
    records: list[dict[str, object]] = []

    for column in time_columns:
        value = pd.to_numeric(row[column], errors="coerce")
        if pd.isna(value):
            continue
        records.append(
            {
                "timestamp": parse_export_timestamp(column),
                "visible_stores": float(value),
                "metric": str(row["metric (sf_metric)"]),
                "plot_name": str(row["Plot name"]),
                "source_file": csv_path.name,
            }
        )

    return pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)


def load_all_availability_data(input_dir: Path | str) -> pd.DataFrame:
    frames = [load_wide_csv(path) for path in iter_csv_files(input_dir)]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "visible_stores",
                "metric",
                "observations",
                "source_files",
            ]
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["timestamp", "visible_stores"])
    deduped = (
        combined.groupby(["timestamp", "metric"], as_index=False)
        .agg(
            visible_stores=("visible_stores", "median"),
            observations=("visible_stores", "size"),
            source_files=("source_file", lambda values: "|".join(sorted(set(values)))),
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    return deduped


def save_processed_dataset(frame: pd.DataFrame, output_path: Path | str) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target
```

- [ ] **Step 4: Create preprocessing command**

Create `scripts/build_dataset.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rappi_availability.load_data import load_all_availability_data, save_processed_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized Rappi availability dataset.")
    parser.add_argument("--input", default="Archivo (1)", help="Folder containing exported CSV files.")
    parser.add_argument(
        "--output",
        default="data/processed/availability_long.csv",
        help="Destination normalized CSV path.",
    )
    args = parser.parse_args()

    frame = load_all_availability_data(args.input)
    output_path = save_processed_dataset(frame, args.output)
    print(f"Wrote {len(frame):,} rows to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests and build the processed dataset**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_load_data.py -q
.\.venv\Scripts\python scripts/build_dataset.py --input "Archivo (1)" --output data/processed/availability_long.csv
```

Expected:

```txt
3 passed
Wrote 67,141 rows to data/processed/availability_long.csv
```

The row count is deduplicated unique timestamps from the observed 69,128 raw points.

- [ ] **Step 6: Commit data layer**

Run:

```powershell
git add src/rappi_availability/load_data.py scripts/build_dataset.py tests/test_load_data.py data/processed/.gitkeep
git commit -m "feat: normalize availability exports"
```

Expected: one commit with parser, tests, and preprocessing command.

---

### Task 3: Metrics and Event Detection

**Files:**
- Create: `tests/test_metrics.py`
- Create: `src/rappi_availability/metrics.py`

- [ ] **Step 1: Write failing metric tests**

Create `tests/test_metrics.py`:

```python
import pandas as pd

from rappi_availability.metrics import compute_kpis, daily_summary, detect_events, resample_series


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
            "observations": [1, 1, 1, 2],
        }
    )


def test_compute_kpis_returns_core_dashboard_numbers():
    kpis = compute_kpis(sample_frame())

    assert kpis["points"] == 4
    assert kpis["current_value"] == 200.0
    assert kpis["minimum_value"] == 50.0
    assert kpis["maximum_value"] == 200.0
    assert kpis["median_value"] == 125.0
    assert kpis["duplicate_points"] == 1


def test_daily_summary_groups_by_calendar_date():
    frame = daily_summary(sample_frame())

    assert frame["date"].tolist() == ["2026-02-01", "2026-02-02"]
    assert frame["median_visible_stores"].tolist() == [100.0, 200.0]


def test_resample_series_uses_median_for_dashboard_smoothing():
    frame = resample_series(sample_frame(), frequency="2min")

    assert frame["visible_stores"].tolist() == [75.0, 150.0, 200.0]


def test_detect_events_sorts_largest_absolute_changes_first():
    events = detect_events(sample_frame(), frequency="1min", limit=2)

    assert len(events) == 2
    assert events.iloc[0]["abs_change"] == 100.0
    assert events.iloc[0]["direction"] == "increase"
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_metrics.py -q
```

Expected: FAIL because `rappi_availability.metrics` does not exist.

- [ ] **Step 3: Implement metric logic**

Create `src/rappi_availability/metrics.py`:

```python
from __future__ import annotations

import pandas as pd


def _sorted(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"])
    return result.sort_values("timestamp").reset_index(drop=True)


def filter_by_time(
    frame: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    result = _sorted(frame)
    if start is not None:
        result = result[result["timestamp"] >= pd.Timestamp(start)]
    if end is not None:
        result = result[result["timestamp"] <= pd.Timestamp(end)]
    return result.reset_index(drop=True)


def resample_series(frame: pd.DataFrame, frequency: str = "1min") -> pd.DataFrame:
    result = _sorted(frame)
    if result.empty:
        return pd.DataFrame(columns=["timestamp", "visible_stores"])

    resampled = (
        result.set_index("timestamp")["visible_stores"]
        .resample(frequency)
        .median()
        .dropna()
        .reset_index()
    )
    return resampled


def compute_kpis(frame: pd.DataFrame) -> dict[str, object]:
    result = _sorted(frame)
    if result.empty:
        return {
            "points": 0,
            "current_value": 0.0,
            "average_value": 0.0,
            "median_value": 0.0,
            "minimum_value": 0.0,
            "maximum_value": 0.0,
            "minimum_timestamp": None,
            "maximum_timestamp": None,
            "low_availability_points": 0,
            "duplicate_points": 0,
        }

    values = result["visible_stores"]
    median_value = float(values.median())
    low_threshold = median_value * 0.70
    min_index = values.idxmin()
    max_index = values.idxmax()
    duplicate_points = int((result.get("observations", pd.Series([1] * len(result))) > 1).sum())

    return {
        "points": int(len(result)),
        "current_value": float(values.iloc[-1]),
        "average_value": float(values.mean()),
        "median_value": median_value,
        "minimum_value": float(values.min()),
        "maximum_value": float(values.max()),
        "minimum_timestamp": result.loc[min_index, "timestamp"],
        "maximum_timestamp": result.loc[max_index, "timestamp"],
        "low_availability_points": int((values < low_threshold).sum()),
        "duplicate_points": duplicate_points,
    }


def daily_summary(frame: pd.DataFrame) -> pd.DataFrame:
    result = _sorted(frame)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "points",
                "average_visible_stores",
                "median_visible_stores",
                "min_visible_stores",
                "max_visible_stores",
            ]
        )

    result["date"] = result["timestamp"].dt.date.astype(str)
    return (
        result.groupby("date", as_index=False)
        .agg(
            points=("visible_stores", "size"),
            average_visible_stores=("visible_stores", "mean"),
            median_visible_stores=("visible_stores", "median"),
            min_visible_stores=("visible_stores", "min"),
            max_visible_stores=("visible_stores", "max"),
        )
        .round(2)
    )


def detect_events(
    frame: pd.DataFrame,
    frequency: str = "1min",
    limit: int = 10,
) -> pd.DataFrame:
    series = resample_series(frame, frequency=frequency)
    if len(series) < 2:
        return pd.DataFrame(
            columns=["timestamp", "visible_stores", "previous_value", "change", "abs_change", "direction"]
        )

    series["previous_value"] = series["visible_stores"].shift(1)
    series["change"] = series["visible_stores"] - series["previous_value"]
    series = series.dropna(subset=["previous_value"])
    series["abs_change"] = series["change"].abs()
    series["direction"] = series["change"].map(lambda value: "increase" if value > 0 else "decrease")
    return (
        series.sort_values(["abs_change", "timestamp"], ascending=[False, True])
        .head(limit)
        .reset_index(drop=True)
    )
```

- [ ] **Step 4: Run metric tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_metrics.py -q
```

Expected:

```txt
4 passed
```

- [ ] **Step 5: Commit metric layer**

Run:

```powershell
git add src/rappi_availability/metrics.py tests/test_metrics.py
git commit -m "feat: compute availability metrics"
```

Expected: one commit with tested analytics functions.

---

### Task 4: Semantic Chatbot

**Files:**
- Create: `tests/test_semantic_chat.py`
- Create: `src/rappi_availability/semantic_chat.py`

- [ ] **Step 1: Write failing chatbot tests**

Create `tests/test_semantic_chat.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_semantic_chat.py -q
```

Expected: FAIL because `rappi_availability.semantic_chat` does not exist.

- [ ] **Step 3: Implement semantic answers**

Create `src/rappi_availability/semantic_chat.py`:

```python
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
    if any(word in text for word in ["minimo", "menor", "peor", "bajo", "caida"]):
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
```

- [ ] **Step 4: Run chatbot tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_semantic_chat.py -q
```

Expected:

```txt
4 passed
```

- [ ] **Step 5: Commit chatbot layer**

Run:

```powershell
git add src/rappi_availability/semantic_chat.py tests/test_semantic_chat.py
git commit -m "feat: answer semantic availability questions"
```

Expected: one commit with the semantic answer engine.

---

### Task 5: Streamlit Dashboard and Chat UI

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create the Streamlit app**

Create `app.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
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


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> pd.DataFrame:
    if PROCESSED_PATH.exists():
        frame = pd.read_csv(PROCESSED_PATH, parse_dates=["timestamp"])
    else:
        frame = load_all_availability_data(DATA_DIR)
    return frame.sort_values("timestamp").reset_index(drop=True)


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


st.set_page_config(
    page_title="Rappi Availability AI Dashboard",
    page_icon="R",
    layout="wide",
)

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
    aggregation = st.selectbox("Agregación visual", ["10s raw", "1min", "5min", "15min", "1H"], index=2)
    show_llm_polish = st.toggle("Pulir respuestas con OpenAI", value=False)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    filtered = filter_by_time(data, start=start, end=end)
else:
    filtered = data

kpis = compute_kpis(filtered)

metric_columns = st.columns(5)
metric_columns[0].metric("Puntos", format_number(kpis["points"]))
metric_columns[1].metric("Último valor", format_number(kpis["current_value"]))
metric_columns[2].metric("Mediana", format_number(kpis["median_value"]))
metric_columns[3].metric("Mínimo", format_number(kpis["minimum_value"]))
metric_columns[4].metric("Máximo", format_number(kpis["maximum_value"]))

frequency_map = {"10s raw": None, "1min": "1min", "5min": "5min", "15min": "15min", "1H": "1H"}
plot_frame = filtered[["timestamp", "visible_stores"]].copy()
if frequency_map[aggregation]:
    plot_frame = resample_series(filtered, frequency=frequency_map[aggregation])

line = px.line(
    plot_frame,
    x="timestamp",
    y="visible_stores",
    title="Visible stores en el tiempo",
    labels={"timestamp": "Timestamp", "visible_stores": "Visible stores"},
)
line.update_layout(height=430, margin=dict(l=20, r=20, t=50, b=20))
st.plotly_chart(line, use_container_width=True)

left, right = st.columns([1, 1])
with left:
    st.subheader("Resumen diario")
    daily = daily_summary(filtered)
    bar = px.bar(
        daily,
        x="date",
        y="median_visible_stores",
        title="Mediana diaria de visible stores",
        labels={"date": "Fecha", "median_visible_stores": "Mediana"},
    )
    bar.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(bar, use_container_width=True)

with right:
    st.subheader("Cambios más fuertes")
    events = detect_events(filtered, frequency="1min", limit=10)
    st.dataframe(
        events[
            ["timestamp", "visible_stores", "previous_value", "change", "direction"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Chatbot semántico")
st.caption("Prueba preguntas como: ¿cuál fue el peor momento?, dame la tendencia general, ¿qué día fue mejor?")

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
```

- [ ] **Step 2: Run full tests before browser verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Expected:

```txt
11 passed
```

- [ ] **Step 3: Compile app imports**

Run:

```powershell
.\.venv\Scripts\python -m py_compile app.py src/rappi_availability/load_data.py src/rappi_availability/metrics.py src/rappi_availability/semantic_chat.py scripts/build_dataset.py
```

Expected: command exits with no output.

- [ ] **Step 4: Run local app**

Run:

```powershell
.\.venv\Scripts\streamlit run app.py
```

Expected: Streamlit prints a local URL, usually `http://localhost:8501`.

Manual verification:

- The page loads without a Python traceback.
- The KPI row shows non-zero point count.
- The line chart renders timestamps from February 2026.
- The daily bar chart renders multiple dates.
- The events table lists increases and decreases.
- Chat question `¿Cuál fue el peor momento?` returns a numeric value and timestamp.
- Chat question `Dame la tendencia general` returns starting and ending values from the active filter.

- [ ] **Step 5: Commit app UI**

Stop Streamlit with `Ctrl+C`, then run:

```powershell
git add app.py
git commit -m "feat: build availability dashboard UI"
```

Expected: one commit with the local web app.

---

### Task 6: README and Presentation

**Files:**
- Create: `README.md`
- Create: `presentation/rappi-ai-dashboard.md`

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# Rappi Availability AI Dashboard

Local web app for the Rappi AI Interns 2026 technical test. It turns exported availability CSV files into a dashboard and a semantic chatbot over the active data filter.

## What It Builds

- Availability time-series dashboard for `synthetic_monitoring_visible_stores`.
- Date filters and visual aggregation controls.
- KPI row with current, median, minimum, and maximum values.
- Daily median chart and strongest-change event table.
- Chatbot that answers Spanish questions about the displayed data.
- Optional OpenAI answer polishing when `OPENAI_API_KEY` is available.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/build_dataset.py --input "Archivo (1)" --output data/processed/availability_long.csv
.\.venv\Scripts\streamlit run app.py
```

## Test

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m py_compile app.py src/rappi_availability/load_data.py src/rappi_availability/metrics.py src/rappi_availability/semantic_chat.py scripts/build_dataset.py
```

## AI Usage

- Codex/GPT was used to inspect the brief, understand the wide CSV export, design the architecture, and generate a test-driven implementation plan.
- The chatbot uses deterministic semantic routing so the demo works without secrets and stays grounded in the filtered data.
- When `OPENAI_API_KEY` is present, the app can polish verified answers through OpenAI while keeping the numeric answer computed locally.

## Data Notes

The provided files are aggregated time-series exports. They do not contain individual store IDs, so the app reports visible-store availability over time and does not infer per-store online/offline histories.
```

- [ ] **Step 2: Create presentation outline**

Create `presentation/rappi-ai-dashboard.md`:

```markdown
# Rappi AI-Powered Dashboard Presentation

## Slide 1 - Problem

Store availability affects user experience and operations. The goal was to make the historical availability export easy to inspect and query during a local demo.

## Slide 2 - Data Understanding

The dataset is a SignalFx-style wide export: one metric row per CSV and timestamp columns every 10 seconds. I normalized 201 files into one long time series and deduplicated overlapping export windows.

## Slide 3 - Dashboard

The dashboard focuses on fast operational readout: KPIs, line chart, daily median bars, event table, and date filters. It exposes raw spikes instead of hiding them so reviewers can see the real data quality.

## Slide 4 - Chatbot

The chatbot maps Spanish questions to analytical intents: minimum, maximum, summary, trend, daily comparison, and strongest events. Answers are computed from the currently filtered data so chart and chat stay aligned.

## Slide 5 - AI Tools Used

I used Codex/GPT as an engineering agent for requirement analysis, architecture design, code generation, tests, and presentation structuring. Optional OpenAI polishing can make chatbot answers more conversational while preserving locally computed metrics.

## Slide 6 - Tradeoffs and Demo Flow

I chose Streamlit to prioritize a working product within 1.5 hours. The demo flow is: load dashboard, filter dates, explain anomalies, ask the chatbot for the worst moment, ask for trend, then show the tested code structure.
```

- [ ] **Step 3: Commit docs**

Run:

```powershell
git add README.md presentation/rappi-ai-dashboard.md
git commit -m "docs: explain demo and ai usage"
```

Expected: one commit with setup and presentation materials.

---

### Task 7: Final Verification and Demo Script

**Files:**
- Verify: all created files.

- [ ] **Step 1: Rebuild processed data from raw CSVs**

Run:

```powershell
Remove-Item -LiteralPath data/processed/availability_long.csv -ErrorAction SilentlyContinue
.\.venv\Scripts\python scripts/build_dataset.py --input "Archivo (1)" --output data/processed/availability_long.csv
```

Expected:

```txt
Wrote 67,141 rows to data/processed/availability_long.csv
```

- [ ] **Step 2: Run all automated checks**

Run:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m py_compile app.py src/rappi_availability/load_data.py src/rappi_availability/metrics.py src/rappi_availability/semantic_chat.py scripts/build_dataset.py
```

Expected:

```txt
11 passed
```

The compile command should exit with no output.

- [ ] **Step 3: Run the app and verify demo questions**

Run:

```powershell
.\.venv\Scripts\streamlit run app.py
```

Ask these questions in the chatbot:

```txt
¿Cuál fue el peor momento de disponibilidad?
Dame la tendencia general.
¿Qué día tuvo mejor mediana?
¿Cuáles fueron los cambios más fuertes?
```

Expected:

- Every answer references the active date filter.
- Minimum and maximum answers include a timestamp.
- Trend answer includes initial and final values.
- Event answer lists at least one timestamp with a change amount.

- [ ] **Step 4: Final commit after verification**

Run:

```powershell
git status --short
git add data/processed/availability_long.csv
git commit -m "build: add normalized availability dataset"
```

Expected: the working tree is clean except the raw source files and the Word document if they are intentionally untracked.

---

## Requirement Coverage

- Dashboard visualization: Task 5 builds KPIs, time series, daily chart, event table, and date filters.
- Chatbot semántico: Task 4 builds Spanish intent routing and Task 5 integrates it into the app.
- Local app: Task 5 runs with Streamlit locally.
- Source code folder: Tasks 1 through 6 create organized source, tests, docs, and scripts.
- Presentation: Task 6 creates a demo presentation outline.
- AI tools explanation: Task 6 documents Codex/GPT usage and optional OpenAI polishing.
- Functionality: Tasks 2 through 5 are covered by tests and manual Streamlit checks.
- Code quality: package structure separates loading, metrics, chat, and UI.

## Implementation Order

1. Task 1 creates a runnable Python project.
2. Task 2 normalizes raw CSVs into analytical data.
3. Task 3 computes reusable dashboard metrics.
4. Task 4 creates grounded semantic answers.
5. Task 5 exposes the app UI.
6. Task 6 prepares the explanation deliverables.
7. Task 7 verifies the final demo from raw data to browser.
