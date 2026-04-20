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

