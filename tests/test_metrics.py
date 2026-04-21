import pandas as pd

from rappi_availability.metrics import (
    compute_kpis,
    daily_summary,
    detect_events,
    resample_series,
    summarize_range_change,
)


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


def test_summarize_range_change_uses_absolute_delta_when_initial_baseline_is_tiny():
    summary = summarize_range_change(
        first_value=37.0,
        last_value=5_630_566.0,
        reference_value=3_542_000.0,
    )

    assert summary["mode"] == "absolute"
    assert summary["baseline_is_representative"] is False
    assert summary["change"] == 5_630_529.0
    assert summary["percent"] is None


def test_summarize_range_change_uses_percent_when_initial_baseline_is_representative():
    summary = summarize_range_change(
        first_value=3_000_000.0,
        last_value=3_600_000.0,
        reference_value=3_200_000.0,
    )

    assert summary["mode"] == "percent"
    assert summary["baseline_is_representative"] is True
    assert summary["change"] == 600_000.0
    assert summary["percent"] == 20.0
