"""API 1.8 and 1.9 endpoints: each method calls its path with the API's parameter names (no network)."""
from typing import Any, Dict, List, Tuple

import pytest

from calcbloc import CalcBlocError
from tests.test_client import ATTRIBUTION, error_body, make

OK = (200, {}, {"attribution": ATTRIBUTION})


def test_each_method_calls_its_endpoint() -> None:
    c, t = make(*[OK] * 9)
    c.supplemental_withholding("us", 100000, 10000, type="bonus", region="ca")
    c.equity_tax("uk", "emi", 1000, "2024-01-15", "2026-03-01", fmv_event=12, exercise_price=2)
    c.cross_border_equity("rsu", 100, "2024-01-01", "2026-01-01", "us:2024-01-01:2024-12-31,gb:2025-01-01:2026-01-01", fmv_event=50, us_citizen=False)
    c.facts(country="uk", tax_type="income.pit")
    c.tax_calendar("uk")
    c.tax_calendar()
    c.tariffs("gb", "0901", origin="in")
    c.trade_agreements("gb", partner="in")
    c.import_duty("gb", "in", "0901210000", 1000, proof_of_origin=True)
    got: List[Tuple[str, Dict[str, Any]]] = [(x["path"], x["query"]) for x in t.calls]
    assert got == [
        ("/api/v1/supplemental-withholding", {"country": "us", "salary": "100000", "amount": "10000", "type": "bonus", "region": "ca"}),
        ("/api/v1/equity-tax", {"country": "uk", "instrument": "emi", "units": "1000", "grant_date": "2024-01-15", "event_date": "2026-03-01", "fmv_event": "12", "exercise_price": "2"}),
        ("/api/v1/cross-border-equity", {"instrument": "rsu", "units": "100", "grant_date": "2024-01-01", "event_date": "2026-01-01", "periods": "us:2024-01-01:2024-12-31,gb:2025-01-01:2026-01-01", "fmv_event": "50", "us_citizen": "false"}),
        ("/api/v1/facts", {"country": "uk", "tax_type": "income.pit"}),
        ("/api/v1/tax-calendar", {"country": "uk"}),
        ("/api/v1/tax-calendar", {}),
        ("/api/v1/tariffs", {"destination": "gb", "code": "0901", "origin": "in"}),
        ("/api/v1/trade-agreements", {"country": "gb", "partner": "in"}),
        ("/api/v1/import-duty", {"destination": "gb", "origin": "in", "code": "0901210000", "customs_value": "1000", "proof_of_origin": "true"}),
    ]


def test_api_errors_are_raised() -> None:
    c, _ = make((400, {}, error_body("invalid_parameter", "Code 610910 matches 2 tariff lines")))
    with pytest.raises(CalcBlocError) as e:
        c.import_duty("gb", "cn", "610910", 100)
    assert e.value.code == "invalid_parameter"
