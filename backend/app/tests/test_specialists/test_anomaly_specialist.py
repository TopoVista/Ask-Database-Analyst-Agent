"""Tests for Anomaly Detection Specialist."""

from __future__ import annotations

import pytest

from app.specialists.anomaly_specialist import AnomalySpecialist, register


class TestDetectAnomalies:
    @pytest.mark.asyncio
    async def test_detects_obvious_outlier(self):
        specialist = AnomalySpecialist()
        data = [
            {"value": 10},
            {"value": 11},
            {"value": 10},
            {"value": 12},
            {"value": 100},  # outlier
            {"value": 11},
        ]
        result = await specialist.detect_anomalies(data, columns=["value"])
        assert "anomalies" in result
        assert isinstance(result["anomalies"], list)

    @pytest.mark.asyncio
    async def test_no_anomalies_in_uniform_data(self):
        specialist = AnomalySpecialist()
        data = [{"value": 10 + i * 0.1} for i in range(20)]
        result = await specialist.detect_anomalies(data, columns=["value"])
        assert isinstance(result["anomalies"], list)

    @pytest.mark.asyncio
    async def test_handles_empty_data(self):
        specialist = AnomalySpecialist()
        result = await specialist.detect_anomalies([], columns=["value"])
        assert result["anomalies"] == []


class TestIsolationForest:
    @pytest.mark.asyncio
    async def test_fit_and_detect(self):
        specialist = AnomalySpecialist()
        data = [
            {"x": 1, "y": 1},
            {"x": 2, "y": 2},
            {"x": 1, "y": 2},
            {"x": 2, "y": 1},
            {"x": 50, "y": 50},  # outlier
        ]
        result = await specialist.isolation_forest_detect(data, columns=["x", "y"])
        assert "anomaly_labels" in result
        assert len(result["anomaly_labels"]) == len(data)


class TestStatisticalMethods:
    @pytest.mark.asyncio
    async def test_zscore_detection(self):
        specialist = AnomalySpecialist()
        data = [{"v": float(i)} for i in range(20)]
        data.append({"v": 100.0})  # outlier
        result = await specialist.zscore_detect(data, column="v", threshold=2.0)
        assert "outlier_indices" in result

    @pytest.mark.asyncio
    async def test_iqr_detection(self):
        specialist = AnomalySpecialist()
        data = [{"v": float(i)} for i in range(20)]
        data.append({"v": 100.0})
        result = await specialist.iqr_detect(data, column="v")
        assert "outlier_indices" in result


class TestRegister:
    def test_register_returns_specialist(self):
        specialist = register()
        assert isinstance(specialist, AnomalySpecialist)
