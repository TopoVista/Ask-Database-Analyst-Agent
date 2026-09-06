"""Tests for Causal Analysis Specialist."""

from __future__ import annotations

import pytest

from app.specialists.causal_specialist import CausalSpecialist, register


class TestConfounderDetection:
    @pytest.mark.asyncio
    async def test_detects_common_cause(self):
        specialist = CausalSpecialist()
        variables = ["sm", "lc", "age"]
        result = await specialist.detect_confounders(variables, treatment="sm", outcome="lc")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_variables(self):
        specialist = CausalSpecialist()
        result = await specialist.detect_confounders([], treatment="x", outcome="y")
        assert result == []


class TestDAGGeneration:
    @pytest.mark.asyncio
    async def test_generates_dag(self):
        specialist = CausalSpecialist()
        variables = ["x", "y", "z"]
        result = await specialist.generate_dag(variables, treatment="x", outcome="y")
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 3

    @pytest.mark.asyncio
    async def test_dag_respects_treatment_outcome(self):
        specialist = CausalSpecialist()
        result = await specialist.generate_dag(["a", "b"], treatment="a", outcome="b")
        node_ids = [n["id"] for n in result["nodes"]]
        assert "a" in node_ids
        assert "b" in node_ids


class TestCausalEffect:
    @pytest.mark.asyncio
    async def test_estimates_effect(self):
        specialist = CausalSpecialist()
        data = [
            {"treatment": 1, "outcome": 10, "confounder": 5},
            {"treatment": 0, "outcome": 5, "confounder": 3},
            {"treatment": 1, "outcome": 12, "confounder": 6},
            {"treatment": 0, "outcome": 4, "confounder": 2},
        ]
        result = await specialist.estimate_causal_effect(
            data, treatment="treatment", outcome="outcome", confounders=["confounder"]
        )
        assert "effect_estimate" in result
        assert isinstance(result["effect_estimate"], float)


class TestRegister:
    def test_register_returns_specialist(self):
        specialist = register()
        assert isinstance(specialist, CausalSpecialist)
