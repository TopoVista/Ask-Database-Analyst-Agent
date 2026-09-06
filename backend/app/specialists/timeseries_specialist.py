"""Time-Series/Forecasting Specialist."""

from __future__ import annotations

import math
from typing import Any

from app.core.registry import skill


def _mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def _std(values: list[float]) -> float:
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / max(len(values) - 1, 1)
    return math.sqrt(variance)


def _linear_regression(x: list[float], y: list[float]) -> dict[str, float]:
    n = min(len(x), len(y))
    if n < 2:
        return {"slope": 0.0, "intercept": _mean(y) if y else 0.0, "r_squared": 0.0}
    x_slice = x[:n]
    y_slice = y[:n]
    x_mean = _mean(x_slice)
    y_mean = _mean(y_slice)
    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x_slice, y_slice))
    den = sum((xi - x_mean) ** 2 for xi in x_slice)
    if den == 0:
        return {"slope": 0.0, "intercept": y_mean, "r_squared": 0.0}
    slope = num / den
    intercept = y_mean - slope * x_mean
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x_slice, y_slice))
    ss_tot = sum((yi - y_mean) ** 2 for yi in y_slice)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return {"slope": round(slope, 6), "intercept": round(intercept, 4), "r_squared": round(r_squared, 4)}


def _moving_average(values: list[float], window: int = 3) -> list[float]:
    if window <= 0 or window > len(values):
        return values[:]
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = values[start : i + 1]
        result.append(round(_mean(window_vals), 4))
    return result


def _exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(round(alpha * values[i] + (1 - alpha) * result[-1], 4))
    return result


def _detect_trend(values: list[float]) -> dict[str, Any]:
    if len(values) < 2:
        return {"direction": "insufficient_data", "slope": 0.0, "strength": "none"}
    x = list(range(len(values)))
    reg = _linear_regression(x, values)
    slope = reg["slope"]
    if abs(slope) < 1e-6:
        direction = "flat"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"
    r_sq = reg["r_squared"]
    if r_sq > 0.7:
        strength = "strong"
    elif r_sq > 0.3:
        strength = "moderate"
    else:
        strength = "weak"
    return {"direction": direction, "slope": slope, "strength": strength, "r_squared": r_sq}


def _detect_seasonality(values: list[float], period: int | None = None) -> dict[str, Any]:
    n = len(values)
    if n < 4:
        return {"has_seasonality": False, "period": None, "confidence": 0.0}

    # Detrend the data: remove linear trend to avoid detecting trend as seasonality
    x = list(range(n))
    reg = _linear_regression(x, values)
    detrended = [values[i] - (reg["slope"] * i + reg["intercept"]) for i in range(n)]

    m = _mean(detrended)
    variance = sum((x - m) ** 2 for x in detrended) / n if n > 0 else 0
    if variance < 1e-10:
        return {"has_seasonality": False, "period": None, "confidence": 0.0}

    best_period = None
    best_corr = 0.0
    search_range = range(2, min(n // 2, 25))
    for lag in search_range:
        cov = sum((detrended[i] - m) * (detrended[i - lag] - m) for i in range(lag, n)) / (n - lag)
        corr = cov / variance
        if corr > best_corr:
            best_corr = corr
            best_period = lag
    has_seasonality = best_corr > 0.3
    return {
        "has_seasonality": has_seasonality,
        "period": best_period if has_seasonality else None,
        "confidence": round(best_corr, 3) if has_seasonality else 0.0,
    }


def _detect_change_points(values: list[float], threshold: float = 2.0) -> list[int]:
    if len(values) < 3:
        return []
    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    m = _mean(diffs)
    s = _std(diffs)
    if s == 0:
        return []
    change_points: list[int] = []
    for i, d in enumerate(diffs):
        z = abs((d - m) / s)
        if z > threshold:
            change_points.append(i + 1)
    return change_points


class TimeSeriesSpecialist:
    """Time-Series/Forecasting Specialist.

    Provides skills for moving average, exponential smoothing, trend detection,
    seasonality analysis, change point detection, forecasting, and decomposition.
    """

    name: str = "timeseries_specialist"
    description: str = "Time-series analysis: trend, seasonality, forecasting, anomaly detection"

    @skill("moving_average")
    async def moving_average(self, values: list[float], window: int = 3) -> dict[str, Any]:
        ma = _moving_average(values, window)
        return {"moving_average": ma, "window": window, "count": len(ma)}

    @skill("exponential_smoothing")
    async def exponential_smoothing(self, values: list[float], alpha: float = 0.3) -> dict[str, Any]:
        smoothed = _exponential_smoothing(values, alpha)
        return {"smoothed": smoothed, "alpha": alpha, "count": len(smoothed)}

    @skill("trend")
    async def trend(self, values: list[float]) -> dict[str, Any]:
        return _detect_trend(values)

    @skill("seasonality")
    async def seasonality(self, values: list[float], period: int | None = None) -> dict[str, Any]:
        return _detect_seasonality(values, period)

    @skill("change_points")
    async def change_points(self, values: list[float], threshold: float = 2.0) -> dict[str, Any]:
        points = _detect_change_points(values, threshold)
        return {"change_points": points, "count": len(points), "threshold": threshold}

    @skill("forecast")
    async def forecast(self, values: list[float], horizon: int = 5) -> dict[str, Any]:
        if len(values) < 2:
            return {"forecast": [], "method": "insufficient_data", "horizon": horizon}
        x = list(range(len(values)))
        reg = _linear_regression(x, values)
        last_idx = len(values) - 1
        forecast_values: list[float] = []
        for h in range(1, horizon + 1):
            next_val = reg["slope"] * (last_idx + h) + reg["intercept"]
            forecast_values.append(round(next_val, 4))
        return {
            "forecast": forecast_values,
            "method": "linear_regression",
            "horizon": horizon,
            "slope": reg["slope"],
            "intercept": reg["intercept"],
            "r_squared": reg["r_squared"],
        }

    @skill("decompose")
    async def decompose(self, values: list[float]) -> dict[str, Any]:
        trend_result = _detect_trend(values)
        trend_line: list[float] = []
        if len(values) >= 2:
            x = list(range(len(values)))
            reg = _linear_regression(x, values)
            trend_line = [round(reg["slope"] * xi + reg["intercept"], 4) for xi in x]
        residuals = [round(v - t, 4) for v, t in zip(values, trend_line)] if trend_line else []
        return {
            "trend": trend_line,
            "residuals": residuals,
            "original_mean": round(_mean(values), 4),
            "residual_std": round(_std(residuals), 4) if residuals else 0.0,
        }

    @skill("full_analysis")
    async def full_analysis(self, values: list[float], column_name: str = "") -> dict[str, Any]:
        trend = _detect_trend(values)
        seasonality = _detect_seasonality(values)
        change_points = _detect_change_points(values)
        return {
            "column": column_name,
            "count": len(values),
            "mean": round(_mean(values), 4),
            "std": round(_std(values), 4),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "trend": trend,
            "seasonality": seasonality,
            "change_points": change_points,
        }


def register() -> TimeSeriesSpecialist:
    return TimeSeriesSpecialist()
