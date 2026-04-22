import pandas as pd

from rappi_availability.risk_model import compute_risk_model


def sample_frame():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-02-01 08:00:00",
                    "2026-02-01 08:01:00",
                    "2026-02-01 08:02:00",
                    "2026-02-01 08:03:00",
                    "2026-02-01 08:04:00",
                    "2026-02-01 08:05:00",
                    "2026-02-01 08:06:00",
                    "2026-02-01 08:07:00",
                ]
            ),
            "visible_stores": [100.0, 100.0, 40.0, 30.0, 110.0, 120.0, 20.0, 130.0],
            "metric": ["synthetic_monitoring_visible_stores"] * 8,
            "observations": [1] * 8,
        }
    )


def test_compute_risk_model_calculates_sli_and_error_budget():
    result = compute_risk_model(sample_frame(), healthy_ratio=0.70, slo_target=0.95)

    assert result["summary"]["threshold_value"] == 70.0
    assert result["summary"]["total_minutes"] == 8
    assert result["summary"]["low_minutes"] == 3
    assert result["summary"]["operational_sli_pct"] == 62.5
    assert result["summary"]["allowed_low_minutes"] == 0.4
    assert result["summary"]["budget_overrun_minutes"] == 2.6
    assert result["summary"]["budget_overrun_pct"] == 650.0
    assert result["summary"]["error_budget_used_pct"] == 750.0
    assert result["summary"]["error_budget_remaining_pct"] == 0.0
    assert result["summary"]["budget_burn_rate"] == 7.5


def test_compute_risk_model_detects_continuous_incidents():
    result = compute_risk_model(sample_frame(), healthy_ratio=0.70, slo_target=0.95)
    incidents = result["incidents"]

    assert len(incidents) == 2
    assert incidents.iloc[0]["start"] == pd.Timestamp("2026-02-01 08:02:00")
    assert incidents.iloc[0]["end"] == pd.Timestamp("2026-02-01 08:03:00")
    assert incidents.iloc[0]["duration_minutes"] == 2
    assert incidents.iloc[0]["min_visible_stores"] == 30.0
    assert incidents.iloc[1]["duration_minutes"] == 1


def test_compute_risk_model_calculates_mttr_mtbf_and_worst_incident():
    result = compute_risk_model(sample_frame(), healthy_ratio=0.70, slo_target=0.95)

    assert result["summary"]["incident_count"] == 2
    assert result["summary"]["mttr_minutes"] == 1.5
    assert result["summary"]["mtbf_minutes"] == 3.0
    assert result["summary"]["worst_incident_start"] == pd.Timestamp("2026-02-01 08:02:00")
    assert result["summary"]["worst_incident_duration_minutes"] == 2


def test_compute_risk_model_reports_stability_distribution_and_recovery():
    result = compute_risk_model(sample_frame(), healthy_ratio=0.70, slo_target=0.95)

    assert result["summary"]["p10_visible_stores"] == 27.0
    assert result["summary"]["p90_visible_stores"] == 123.0
    assert result["summary"]["p10_p90_spread"] == 96.0
    assert result["summary"]["volatility_index"] > 0
    assert result["summary"]["recovery_velocity_per_min"] > 0


def test_compute_risk_model_handles_empty_frame():
    result = compute_risk_model(pd.DataFrame(columns=["timestamp", "visible_stores"]))

    assert result["summary"]["total_minutes"] == 0
    assert result["summary"]["operational_sli_pct"] == 0.0
    assert result["incidents"].empty
    assert result["minute_series"].empty
