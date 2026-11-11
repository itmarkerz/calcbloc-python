"""Unit tests for the band helpers on small hand-made sections."""

from __future__ import annotations

from decimal import Decimal

import pytest

from calcbloc import band_breakdown, marginal_rate, tax_from_bands

SECTION = {
    "id": "toy",
    "kind": "bands",
    "rows": [
        {"label": "Zero", "from": 0, "to": 10_000, "rate": 0},
        {"label": "Low", "from": 10_000, "to": 40_000, "rate": 0.2},
        {"label": "High", "from": 40_000, "to": None, "rate": 0.4},
    ],
}


def test_progressive_total() -> None:
    assert tax_from_bands(SECTION, 0) == 0
    assert tax_from_bands(SECTION, 10_000) == 0
    assert tax_from_bands(SECTION, 25_000) == 3_000
    assert tax_from_bands(SECTION, 40_000) == 6_000
    assert tax_from_bands(SECTION, 50_000) == 10_000


def test_negative_income_is_zero() -> None:
    assert tax_from_bands(SECTION, -5) == 0
    assert all(s.amount == 0 for s in band_breakdown(SECTION, -5))


def test_breakdown_per_band() -> None:
    slices = band_breakdown(SECTION, 50_000)
    assert [(s.label, s.amount, s.tax) for s in slices] == [("Zero", 10_000, 0), ("Low", 30_000, 6_000), ("High", 10_000, 4_000)]
    assert slices[-1].upper is None


def test_above_stacks_on_lower_income() -> None:
    # 5,000 on top of 38,000: 2,000 at 20% + 3,000 at 40%.
    assert tax_from_bands(SECTION, 5_000, above=38_000) == 1_600
    assert [s.amount for s in band_breakdown(SECTION, 5_000, above=38_000)] == [0, 2_000, 3_000]
    with pytest.raises(ValueError):
        tax_from_bands(SECTION, 1, above=-1)


def test_decimal_arithmetic_has_no_float_noise() -> None:
    s = {"kind": "bands", "rows": [{"from": 0, "to": None, "rate": 0.035}]}
    assert tax_from_bands(s, 10_000) == 350.0
    assert tax_from_bands(s, Decimal("0.10")) == 0.0035


def test_accepts_a_list_of_rows_and_unsorted_rows() -> None:
    rows = list(reversed(SECTION["rows"]))
    assert tax_from_bands(rows, 50_000) == 10_000


def test_rejects_value_sections_and_bad_rows() -> None:
    with pytest.raises(ValueError, match="values"):
        tax_from_bands({"id": "pa", "kind": "values", "rows": [{"label": "x", "value": 1}]}, 1)
    with pytest.raises(ValueError):
        tax_from_bands({"kind": "bands", "rows": [{"from": 0, "to": None}]}, 1)
    with pytest.raises(ValueError):
        tax_from_bands({"kind": "bands", "rows": [{"from": 0, "to": None, "rate": "20%"}]}, 1)
    with pytest.raises(ValueError):
        tax_from_bands({"kind": "bands", "rows": []}, 1)
    with pytest.raises(ValueError):
        tax_from_bands({"kind": "bands", "rows": [{"from": 10, "to": 5, "rate": 0.1}]}, 1)
    with pytest.raises(ValueError):
        tax_from_bands(SECTION, True)  # type: ignore[arg-type]


def test_marginal_rate_edges() -> None:
    assert marginal_rate(SECTION, 0) == 0
    assert marginal_rate(SECTION, 10_000) == 0  # "not over 10,000"
    assert marginal_rate(SECTION, 10_000.01) == 0.2
    assert marginal_rate(SECTION, 40_000) == 0.2
    assert marginal_rate(SECTION, 1e9) == 0.4
    assert marginal_rate(SECTION, -1) == 0
