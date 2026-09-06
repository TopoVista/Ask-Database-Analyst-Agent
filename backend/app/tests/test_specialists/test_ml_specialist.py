"""Tests for ML Specialist."""

from __future__ import annotations

import pytest

from app.specialists.ml_specialist import MLSpecialist, register


class TestTrainModel:
    @pytest.mark.asyncio
    async def test_trains_regression(self):
        specialist = MLSpecialist()
        data = [
            {"x": 1, "y": 2},
            {"x": 2, "y": 4},
            {"x": 3, "y": 6},
            {"x": 4, "y": 8},
            {"x": 5, "y": 10},
        ]
        result = await specialist.train_model(data, target="y", features=["x"], task="regression")
        assert "model_type" in result
        assert result["model_type"] == "regression"

    @pytest.mark.asyncio
    async def test_trains_classification(self):
        specialist = MLSpecialist()
        data = [
            {"x": 1, "y": 0},
            {"x": 2, "y": 0},
            {"x": 3, "y": 1},
            {"x": 4, "y": 1},
            {"x": 5, "y": 1},
        ]
        result = await specialist.train_model(data, target="y", features=["x"], task="classification")
        assert result["model_type"] == "classification"

    @pytest.mark.asyncio
    async def test_handles_insufficient_data(self):
        specialist = MLSpecialist()
        result = await specialist.train_model([{"x": 1}], target="y", features=["x"], task="regression")
        assert "error" in result


class TestFeatureImportance:
    @pytest.mark.asyncio
    async def test_extracts_importance(self):
        specialist = MLSpecialist()
        data = [
            {"a": 1, "b": 2, "y": 3},
            {"a": 2, "b": 3, "y": 5},
            {"a": 3, "b": 4, "y": 7},
            {"a": 4, "b": 5, "y": 9},
        ]
        result = await specialist.train_model(data, target="y", features=["a", "b"], task="regression")
        if "feature_importance" in result:
            assert isinstance(result["feature_importance"], dict)


class TestPredict:
    @pytest.mark.asyncio
    async def test_makes_predictions(self):
        specialist = MLSpecialist()
        train_data = [{"x": i, "y": i * 2} for i in range(10)]
        await specialist.train_model(train_data, target="y", features=["x"], task="regression")
        predictions = await specialist.predict([{"x": 10}, {"x": 11}])
        assert isinstance(predictions, list)


class TestRegister:
    def test_register_returns_specialist(self):
        specialist = register()
        assert isinstance(specialist, MLSpecialist)
