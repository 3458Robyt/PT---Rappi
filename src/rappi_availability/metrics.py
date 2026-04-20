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
    default_observations = pd.Series([1] * len(result), index=result.index)
    duplicate_points = int((result.get("observations", default_observations) > 1).sum())

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
