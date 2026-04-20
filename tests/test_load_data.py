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
