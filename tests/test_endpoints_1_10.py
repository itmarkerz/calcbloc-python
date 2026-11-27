"""API 1.10: /tax-treaties, the verification field, and Denmark, Estonia and Poland (fake transport, no network).

The fixtures are real API 1.10.0 responses, produced by the site's own request handler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from calcbloc import CalcBlocError
from calcbloc._country_codes import resolve_country_key
from tests.test_client import error_body, make

FIXTURES = Path(__file__).parent / "fixtures" / "api-1.10"


def fixture(name: str) -> Dict[str, Any]:
    data: Dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def test_tax_treaties_calls_the_endpoint() -> None:
    c, t = make((200, {}, fixture("tax-treaties-in-us")), (200, {}, fixture("tax-treaties-in-us")))
    res = c.tax_treaties("in", partner="us")
    c.tax_treaties("India")
    assert [(x["path"], x["query"]) for x in t.calls] == [
        ("/api/v1/tax-treaties", {"country": "in", "partner": "us"}),
        ("/api/v1/tax-treaties", {"country": "India"}),
    ]
    assert res["country"] == "in" and res["partner"] == "us" and res["count"] == 1
    us = res["treaties"][0]
    assert us["countries"] == ["in", "us"]
    assert us["partner_name"] == "United States"
    assert (us["signed"], us["in_force"]) == ("1989-09-12", "1990-12-18")
    assert us["relief_method"] == {"in": "credit", "us": "credit"}
    assert us["withholding"][0]["kind"] == "dividend_substantial"
    assert us["withholding"][0]["rate"] == 0.15
    assert us["withholding"][0]["article"] == "Article 10(2)(a)"
    assert us["source"]["url"] == "https://www.irs.gov/pub/irs-trty/india.pdf"
    assert res["attribution"]["required"] is True


def test_tax_treaties_unknown_country_raises() -> None:
    c, _ = make((400, {}, error_body("unsupported_country", 'No treaties are stored for "de". Countries: in.')))
    with pytest.raises(CalcBlocError) as e:
        c.tax_treaties("de")
    assert e.value.code == "unsupported_country"


def test_verification_on_calculations() -> None:
    c, t = make(
        (200, {}, fixture("net-salary-pl")),
        (200, {}, fixture("net-salary-dk")),
        (200, {}, fixture("employer-cost-ee")),
        (200, {}, fixture("net-salary-uk")),
    )
    pl = c.net_salary("pl", 120000, accident_rate_pct=1.67, commuter=False)
    dk = c.net_salary("dk", 600000, municipality="average", church=False, atp_hours="0")
    ee = c.employer_cost("ee", 30000, funded_pension="0", pension_age=False)
    uk = c.net_salary("uk", 50000)
    assert t.calls[0]["query"] == {"country": "pl", "salary": "120000", "accident_rate_pct": "1.67", "commuter": "false"}
    assert t.calls[1]["query"] == {"country": "dk", "salary": "600000", "municipality": "average", "church": "false", "atp_hours": "0"}
    assert t.calls[2]["path"] == "/api/v1/employer-cost"
    assert pl["verification"] == "official-example"
    assert pl["notes"][0].startswith("Verification (official-example)")
    assert pl["currency"] == "PLN"
    assert dk["verification"] == "law-text"
    assert ee["verification"] == "official-example"
    assert (ee["summary"]["totalCost"] or 0) > 30000
    assert uk["verification"] is None


def test_countries_verification_per_endpoint() -> None:
    c, _ = make((200, {}, fixture("countries-1.10-sample")))
    res = c.countries()
    by_code = {x["code"]: x for x in res["countries"]}
    assert by_code["denmark"]["endpoints"]["net-salary"]["verification"] == "law-text"
    assert by_code["poland"]["endpoints"]["employer-cost"]["verification"] == "official-example"
    assert by_code["estonia"]["endpoints"]["net-salary"]["verification"] == "official-example"
    assert by_code["uk"]["endpoints"]["net-salary"]["verification"] is None
    assert res["coverage"]["tax_tables"] == 217
    assert {"dk", "ee", "pl"} <= set(res["coverage"]["net_salary_countries"])


@pytest.mark.parametrize(
    "given,key",
    [("dk", "denmark"), ("EE", "estonia"), ("Poland", "poland"), ("fj", "fiji"), ("Faroe Islands", "faroe-islands"), ("gl", "greenland"), ("ky", "cayman-islands")],
)
def test_country_codes_cover_api_1_10(given: str, key: str) -> None:
    assert resolve_country_key(given) == key
