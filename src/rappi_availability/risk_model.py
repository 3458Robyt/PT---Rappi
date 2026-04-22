from __future__ import annotations

import math

import pandas as pd

from rappi_availability.metrics import resample_series


EMPTY_INCIDENT_COLUMNS = [
    "incident_id",
    "start",
    "end",
    "duration_minutes",
    "min_visible_stores",
    "median_visible_stores",
    "depth_visible_stores",
    "depth_pct",
    "recovery_timestamp",
    "recovery_value",
    "recovery_velocity_per_min",
    "severity",
]


def _round(value: float | int | None, digits: int = 2) -> float:
    if value is None or pd.isna(value) or math.isinf(float(value)):
        return 0.0
    return round(float(value), digits)


def _empty_result() -> dict[str, object]:
    return {
        "summary": {
            "threshold_value": 0.0,
            "slo_target_pct": 0.0,
            "total_minutes": 0,
            "healthy_minutes": 0,
            "low_minutes": 0,
            "operational_sli_pct": 0.0,
            "allowed_low_minutes": 0.0,
            "error_budget_used_pct": 0.0,
            "error_budget_remaining_pct": 0.0,
            "budget_burn_rate": 0.0,
            "incident_count": 0,
            "mttr_minutes": 0.0,
            "mtbf_minutes": 0.0,
            "worst_incident_start": None,
            "worst_incident_duration_minutes": 0,
            "worst_incident_min_visible_stores": 0.0,
            "volatility_index": 0.0,
            "p10_visible_stores": 0.0,
            "p50_visible_stores": 0.0,
            "p90_visible_stores": 0.0,
            "p10_p90_spread": 0.0,
            "recovery_velocity_per_min": 0.0,
            "status": "Sin datos",
        },
        "minute_series": pd.DataFrame(columns=["timestamp", "visible_stores", "healthy"]),
        "incidents": pd.DataFrame(columns=EMPTY_INCIDENT_COLUMNS),
    }


def _severity(duration_minutes: int, depth_pct: float) -> str:
    if duration_minutes >= 180 or depth_pct >= 85:
        return "Crítico"
    if duration_minutes >= 60 or depth_pct >= 60:
        return "Alto"
    if duration_minutes >= 15 or depth_pct >= 35:
        return "Medio"
    return "Bajo"


def _detect_incidents(series: pd.DataFrame, threshold_value: float) -> pd.DataFrame:
    if series.empty or "healthy" not in series:
        return pd.DataFrame(columns=EMPTY_INCIDENT_COLUMNS)

    working = series.copy()
    working["low"] = ~working["healthy"]
    working["group"] = (working["low"] != working["low"].shift()).cumsum()

    rows: list[dict[str, object]] = []
    low_groups = working[working["low"]].groupby("group", sort=True)
    for incident_number, (_, group) in enumerate(low_groups, start=1):
        start = group["timestamp"].min()
        end = group["timestamp"].max()
        duration_minutes = int(len(group))
        min_visible = float(group["visible_stores"].min())
        median_visible = float(group["visible_stores"].median())
        depth_visible = max(0.0, threshold_value - min_visible)
        depth_pct = (depth_visible / threshold_value * 100) if threshold_value else 0.0

        later_healthy = working[(working["timestamp"] > end) & working["healthy"]].head(1)
        if later_healthy.empty:
            recovery_timestamp = None
            recovery_value = 0.0
            recovery_velocity = 0.0
        else:
            recovery_timestamp = later_healthy.iloc[0]["timestamp"]
            recovery_value = float(later_healthy.iloc[0]["visible_stores"])
            recovery_minutes = max(1, duration_minutes)
            recovery_velocity = max(0.0, recovery_value - min_visible) / recovery_minutes

        rows.append(
            {
                "incident_id": incident_number,
                "start": start,
                "end": end,
                "duration_minutes": duration_minutes,
                "min_visible_stores": _round(min_visible),
                "median_visible_stores": _round(median_visible),
                "depth_visible_stores": _round(depth_visible),
                "depth_pct": _round(depth_pct),
                "recovery_timestamp": recovery_timestamp,
                "recovery_value": _round(recovery_value),
                "recovery_velocity_per_min": _round(recovery_velocity),
                "severity": _severity(duration_minutes, depth_pct),
            }
        )

    return pd.DataFrame.from_records(rows, columns=EMPTY_INCIDENT_COLUMNS)


def compute_risk_model(
    frame: pd.DataFrame,
    healthy_ratio: float = 0.70,
    slo_target: float = 0.95,
) -> dict[str, object]:
    if frame.empty:
        return _empty_result()

    minute_series = resample_series(frame, frequency="1min")
    if minute_series.empty:
        return _empty_result()

    median_value = float(minute_series["visible_stores"].median())
    threshold_value = median_value * healthy_ratio
    minute_series = minute_series.copy()
    minute_series["healthy"] = minute_series["visible_stores"] >= threshold_value

    total_minutes = int(len(minute_series))
    healthy_minutes = int(minute_series["healthy"].sum())
    low_minutes = total_minutes - healthy_minutes
    operational_sli_pct = healthy_minutes / total_minutes * 100 if total_minutes else 0.0
    allowed_low_minutes = total_minutes * max(0.0, 1 - slo_target)
    budget_burn_rate = low_minutes / allowed_low_minutes if allowed_low_minutes else 0.0
    error_budget_used_pct = budget_burn_rate * 100 if allowed_low_minutes else 0.0
    error_budget_remaining_pct = max(0.0, 100 - error_budget_used_pct)

    incidents = _detect_incidents(minute_series, threshold_value)
    if incidents.empty:
        mttr_minutes = 0.0
        mtbf_minutes = 0.0
        worst_incident_start = None
        worst_duration = 0
        worst_min = 0.0
        recovery_velocity = 0.0
    else:
        mttr_minutes = float(incidents["duration_minutes"].mean())
        starts = incidents["start"].tolist()
        ends = incidents["end"].tolist()
        gaps = [
            (starts[index] - ends[index - 1]).total_seconds() / 60
            for index in range(1, len(incidents))
        ]
        mtbf_minutes = float(pd.Series(gaps).mean()) if gaps else 0.0
        worst = incidents.sort_values(
            ["duration_minutes", "depth_pct", "start"],
            ascending=[False, False, True],
        ).iloc[0]
        worst_incident_start = worst["start"]
        worst_duration = int(worst["duration_minutes"])
        worst_min = float(worst["min_visible_stores"])
        recovery_velocity = float(incidents["recovery_velocity_per_min"].mean())

    values = minute_series["visible_stores"]
    p10 = float(values.quantile(0.10))
    p50 = float(values.quantile(0.50))
    p90 = float(values.quantile(0.90))
    spread = p90 - p10
    volatility = float(values.std(ddof=0) / p50) if p50 else 0.0

    if operational_sli_pct >= slo_target * 100:
        status = "Dentro de SLO"
    elif error_budget_remaining_pct > 0:
        status = "En riesgo"
    else:
        status = "Budget agotado"

    return {
        "summary": {
            "threshold_value": _round(threshold_value),
            "slo_target_pct": _round(slo_target * 100),
            "total_minutes": total_minutes,
            "healthy_minutes": healthy_minutes,
            "low_minutes": low_minutes,
            "operational_sli_pct": _round(operational_sli_pct),
            "allowed_low_minutes": _round(allowed_low_minutes),
            "error_budget_used_pct": _round(error_budget_used_pct),
            "error_budget_remaining_pct": _round(error_budget_remaining_pct),
            "budget_burn_rate": _round(budget_burn_rate),
            "incident_count": int(len(incidents)),
            "mttr_minutes": _round(mttr_minutes),
            "mtbf_minutes": _round(mtbf_minutes),
            "worst_incident_start": worst_incident_start,
            "worst_incident_duration_minutes": worst_duration,
            "worst_incident_min_visible_stores": _round(worst_min),
            "volatility_index": _round(volatility, 4),
            "p10_visible_stores": _round(p10),
            "p50_visible_stores": _round(p50),
            "p90_visible_stores": _round(p90),
            "p10_p90_spread": _round(spread),
            "recovery_velocity_per_min": _round(recovery_velocity),
            "status": status,
        },
        "minute_series": minute_series,
        "incidents": incidents,
    }
