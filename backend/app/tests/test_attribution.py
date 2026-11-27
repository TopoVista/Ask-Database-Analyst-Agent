from __future__ import annotations

from decimal import Decimal

from app.domain.attribution import four_way_attribution


def test_four_way_attribution_preserves_reconciliation_and_shapley_allocations():
    result = four_way_attribution(Decimal("2400000"), Decimal("2100000"), Decimal("2220000"), Decimal("1800000"))
    assert result == {
        "data_effect": "-180000",
        "definition_effect": "-300000",
        "interaction_effect": "-120000",
        "data_contribution": "-240000",
        "definition_contribution": "-360000",
        "total_change": "-600000",
        "reconciles": True,
    }
