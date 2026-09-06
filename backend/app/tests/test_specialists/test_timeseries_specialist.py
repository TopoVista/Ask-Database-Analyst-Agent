"""Tests for Time-Series Specialist."""

from __future__ import annotations

import pytest

from app.specialists.timeseries_specialist import TimeSeriesSpecialist, register


@pytest.fixture
def ts() -> TimeSeriesSpecialist:
    return register()


class TestMovingAverage:
    @pytest.mark.asyncio
    async def test_basic_ma(self, ts: TimeSeriesSpecialist):
        result = await ts.moving_average([1, 2, 3, 4, 5], window=3)
        assert result["count"] == 5
        assert result["window"] == 3

    @pytest.mark.asyncio
    async def test_window_equals_length(self, ts: TimeSeriesSpecialist):
        result = await ts.moving_average([1, 2, 3], window=3)
        assert result["count"] == 3


class TestExponentialSmoothing:
    @pytest.mark.asyncio
    async def test_basic_smoothing(self, ts: TimeSeriesSpecialist):
        result = await ts.exponential_smoothing([1, 2, 3, 4, 5], alpha=0.5)
        assert result["count"] == 5
        assert result["alpha"] == 0.5

    @pytest.mark.asyncio
    async def test_empty_input(self, ts: TimeSeriesSpecialist):
        result = await ts.exponential_smoothing([])
        assert result["smoothed"] == []


class TestTrend:
    @pytest.mark.asyncio
    async def test_increasing(self, ts: TimeSeriesSpecialist):
        result = await ts.trend([1, 2, 3, 4, 5])
        assert result["direction"] == "increasing"
        assert result["slope"] > 0

    @pytest.mark.asyncio
    async def test_decreasing(self, ts: TimeSeriesSpecialist):
        result = await ts.trend([5, 4, 3, 2, 1])
        assert result["direction"] == "decreasing"
        assert result["slope"] < 0

    @pytest.mark.asyncio
    async def test_flat(self, ts: TimeSeriesSpecialist):
        result = await ts.trend([5, 5, 5, 5, 5])
        assert result["direction"] == "flat"

    @pytest.mark.asyncio
    async def test_insufficient_data(self, ts: TimeSeriesSpecialist):
        result = await ts.trend([42])
        assert result["direction"] == "insufficient_data"


class TestSeasonality:
    @pytest.mark.asyncio
    async def test_no_seasonality(self, ts: TimeSeriesSpecialist):
        result = await ts.seasonality([1, 2, 3, 4, 5, 6, 7, 8])
        assert result["has_seasonality"] is False

    @pytest.mark.asyncio
    async def test_insufficient_data(self, ts: TimeSeriesSpecialist):
        result = await ts.seasonality([1, 2])
        assert result["has_seasonality"] is False


class TestChangePoints:
    @pytest.mark.asyncio
    async def test_no_change_points(self, ts: TimeSeriesSpecialist):
        result = await ts.change_points([1, 1, 1, 1, 1])
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_detects_jump(self, ts: TimeSeriesSpecialist):
        values = [1, 1, 1, 100, 1, 1, 1]
        result = await ts.change_points(values, threshold=1.5)
        assert result["count"] >= 1


class TestForecast:
    @pytest.mark.asyncio
    async def test_basic_forecast(self, ts: TimeSeriesSpecialist):
        result = await ts.forecast([1, 2, 3, 4, 5], horizon=3)
        assert len(result["forecast"]) == 3
        assert result["method"] == "linear_regression"

    @pytest.mark.asyncio
    async def test_insufficient_data(self, ts: TimeSeriesSpecialist):
        result = await ts.forecast([42], horizon=3)
        assert result["forecast"] == []
        assert result["method"] == "insufficient_data"


class TestDecompose:
    @pytest.mark.asyncio
    async def test_basic_decomposition(self, ts: TimeSeriesSpecialist):
        result = await ts.decompose([1, 2, 3, 4, 5])
        assert "trend" in result
        assert "residuals" in result
        assert result["original_mean"] == 3.0


class TestFullAnalysis:
    @pytest.mark.asyncio
    async def test_full_output(self, ts: TimeSeriesSpecialist):
        result = await ts.full_analysis([10, 20, 30, 40, 50], "sales")
        assert result["column"] == "sales"
        assert result["count"] == 5
        assert "trend" in result
        assert "seasonality" in result
        assert "change_points" in result


class TestRegister:
    def test_register_returns_specialist(self):
        specialist = register()
        assert specialist.name == "timeseries_specialist"
        assert specialist.description
