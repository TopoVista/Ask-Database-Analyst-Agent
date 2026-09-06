"""Tests for core abstractions: registry, planning, artifacts, semantic typing."""

from __future__ import annotations

import pytest

from app.core.registry import SpecialistRegistry
from app.data.descriptor import DatasetDescriptor
from app.data.semantic import infer_semantic_type


class TestSpecialistRegistry:
    def test_register_and_get(self):
        registry = SpecialistRegistry()

        @registry.register(
            id="test_specialist",
            name="Test Specialist",
            description="A test",
            capabilities=["cap_a"],
            tools=["tool_x"],
        )
        class TestSpecialist:
            pass

        assert registry.get("test_specialist") is TestSpecialist
        assert registry.get("missing") is None
        assert "test_specialist" in registry.ids()
        meta = registry.metadata("test_specialist")
        assert meta.capabilities == ["cap_a"]
        assert meta.tools == ["tool_x"]

    def test_duplicate_registration_raises(self):
        registry = SpecialistRegistry()

        @registry.register(id="dup", name="Dup", description="")
        class A:
            pass

        with pytest.raises(ValueError):

            @registry.register(id="dup", name="Dup2", description="")
            class B:
                pass


class TestSemanticTypeInference:
    def test_identifier(self):
        samples = ["ID_001", "ID_002", "ID_003", "ID_004"]
        assert infer_semantic_type("customer_id", "object", samples) == "identifier"

    def test_measure(self):
        assert infer_semantic_type("revenue", "float64", ["1.5", "2.5"]) == "measure"
        assert infer_semantic_type("count", "int64", ["1", "2"]) == "measure"

    def test_temporal(self):
        samples = ["2026-01-05", "2026-01-06", "2026-01-07"]
        assert infer_semantic_type("order_date", "object", samples) == "temporal"

    def test_email_is_text_not_identifier(self):
        samples = ["a@x.com", "b@x.com", "c@x.com"]
        assert infer_semantic_type("email", "object", samples) == "text"

    def test_categorical(self):
        samples = ["west", "east", "west", "east", "west"]
        assert infer_semantic_type("region", "object", samples) == "categorical"

    def test_geo(self):
        assert infer_semantic_type("latitude", "float64", ["40.7"]) == "geo_lat"
        assert infer_semantic_type("longitude", "float64", ["-74.0"]) == "geo_lon"

    def test_boolean(self):
        assert infer_semantic_type("is_active", "bool", ["true", "false"]) == "boolean"


class TestArtifactTypes:
    def test_descriptor_roundtrip(self):
        d = DatasetDescriptor(id="1", name="t", source="file:csv", table_name="t")
        d.measure_columns = ["amount"]
        data = d.to_dict()
        assert data["measure_columns"] == ["amount"]
        assert data["columns"] == []
