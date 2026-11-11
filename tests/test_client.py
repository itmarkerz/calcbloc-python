"""API client tests with a fake transport: no network access."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest

import calcbloc
from calcbloc import AuthenticationError, CalcBlocError, Client, NetworkError, RateLimitError
from calcbloc import client as client_module

ATTRIBUTION = {"source": "CalcBloc", "url": "https://calcbloc.com/developers", "required": True, "text": "Data by CalcBloc (calcbloc.com)"}
LIMIT_HEADERS = {"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "3600"}


class FakeTransport:
    """Records each request and replies with queued (status, headers, body) responses."""

    def __init__(self, *responses: Tuple[int, Mapping[str, str], Any]) -> None:
        self.responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> Tuple[int, Mapping[str, str], bytes]:
        parsed = urllib.parse.urlsplit(url)
        self.calls.append({"url": url, "path": parsed.path, "query": dict(urllib.parse.parse_qsl(parsed.query)), "headers": dict(headers), "timeout": timeout})
        status, resp_headers, body = self.responses.pop(0)
        raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return status, resp_headers, raw


def error_body(code: str, message: str, docs: str = "https://calcbloc.com/developers#parameters") -> Dict[str, Any]:
    return {"error": {"code": code, "message": message, "docs": docs}, "attribution": ATTRIBUTION}


def make(*responses: Tuple[int, Mapping[str, str], Any], api_key: Optional[str] = "test-key") -> Tuple[Client, FakeTransport]:
    t = FakeTransport(*responses)
    return Client(api_key=api_key, transport=t, timeout=7), t


def test_headers_user_agent_and_api_key() -> None:
    c, t = make((200, LIMIT_HEADERS, {"countries": [], "attribution": ATTRIBUTION}))
    assert c.countries() == {"countries": [], "attribution": ATTRIBUTION}
    call = t.calls[0]
    assert call["url"] == "https://calcbloc.com/api/v1/countries"
    assert call["headers"]["X-API-Key"] == "test-key"
    assert call["headers"]["Accept"] == "application/json"
    assert call["headers"]["User-Agent"].startswith(f"calcbloc-python/{calcbloc.__version__}")
    assert call["timeout"] == 7


def test_no_key_sends_no_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALCBLOC_API_KEY", raising=False)
    c, t = make((200, {}, {"countries": []}), api_key=None)
    c.countries()
    assert "X-API-Key" not in t.calls[0]["headers"]
    assert c.api_key is None


def test_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALCBLOC_API_KEY", "  env-key ")
    c = Client(transport=FakeTransport())
    assert c.api_key == "env-key"
    assert "env-key" not in repr(c)


def test_base_url_trailing_slash() -> None:
    t = FakeTransport((200, {}, {"countries": []}))
    Client(base_url="http://localhost:3030/", transport=t).countries()
    assert t.calls[0]["url"] == "http://localhost:3030/api/v1/countries"


def test_tax_tables_defaults_to_latest() -> None:
    c, t = make((200, LIMIT_HEADERS, {"country": "uk", "year": "2026-27", "requested_year": "latest"}))
    table = c.tax_tables("UK")
    assert table["year"] == "2026-27"
    assert t.calls[0]["path"] == "/api/v1/tax-tables/uk/latest"
    assert t.calls[0]["query"] == {}


def test_tax_tables_year_region() -> None:
    c, t = make((200, {}, {"country": "us", "year": "2026"}))
    c.tax_tables("us", 2026, region="ca")
    assert t.calls[0]["path"] == "/api/v1/tax-tables/us/2026"
    assert t.calls[0]["query"] == {"region": "ca"}


def test_tax_tables_csv_returns_text() -> None:
    csv = "section_id,label,from,to,rate\nincome-tax-england,Basic rate,0,37700,0.2\n"
    c, t = make((200, {"Content-Type": "text/csv; charset=utf-8"}, csv.encode("utf-8")))
    out = c.tax_tables("uk", "2026-27", region="scotland", format="csv")
    assert out == csv
    assert t.calls[0]["query"] == {"region": "scotland", "format": "csv"}
    assert t.calls[0]["headers"]["Accept"] == "text/csv"


def test_tax_tables_rejects_bad_input_before_any_request() -> None:
    c, t = make()
    with pytest.raises(ValueError):
        c.tax_tables("../etc", "2026")
    with pytest.raises(ValueError):
        c.tax_tables("uk", "2026/27")
    with pytest.raises(ValueError):
        c.tax_tables("uk", format="xml")  # type: ignore[call-overload]
    assert t.calls == []


def test_net_salary_query_encoding() -> None:
    body = {"endpoint": "net-salary", "country": "us", "summary": {"netAnnual": 61234.5}, "attribution": ATTRIBUTION}
    c, t = make((200, LIMIT_HEADERS, body))
    out = c.net_salary("us", 80_000, region="ca", filing_status="single", multiple_jobs=False, children=2, retirement_pct=None)
    assert out["summary"]["netAnnual"] == 61234.5
    assert t.calls[0]["path"] == "/api/v1/net-salary"
    assert t.calls[0]["query"] == {"country": "us", "salary": "80000", "region": "ca", "filing_status": "single", "multiple_jobs": "false", "children": "2"}


def test_employer_cost_and_compare_paths() -> None:
    c, t = make((200, {}, {"endpoint": "employer-cost"}), (200, {}, {"endpoint": "compare"}))
    c.employer_cost("uk", 45_000, ni_category="A", employment_allowance=True)
    c.compare("uk", "ireland", 60_000, currency="GBP", uk_region="scotland")
    assert t.calls[0]["path"] == "/api/v1/employer-cost"
    assert t.calls[0]["query"] == {"country": "uk", "salary": "45000", "ni_category": "A", "employment_allowance": "true"}
    assert t.calls[1]["path"] == "/api/v1/compare"
    assert t.calls[1]["query"] == {"a": "uk", "b": "ireland", "salary": "60000", "currency": "GBP", "uk_region": "scotland"}


def test_key_in_query_is_refused_locally() -> None:
    c, t = make()
    with pytest.raises(ValueError, match="X-API-Key|api_key"):
        c.net_salary("uk", 1, key="abc")
    assert t.calls == []


def test_rate_limit_headers_are_recorded() -> None:
    c, _ = make((200, {"x-ratelimit-limit": "50", "x-ratelimit-remaining": "12", "x-ratelimit-reset": "999"}, {"countries": []}))
    assert c.last_rate_limit is None
    c.countries()
    assert c.last_rate_limit == calcbloc.RateLimit(limit=50, remaining=12, reset=999)


def test_tables_only_country_is_unsupported_country() -> None:
    message = (
        "net-salary is not available for Norway yet. Its tax tables are at https://calcbloc.com/norway/tax-tables/2026 "
        "(API: /api/v1/tax-tables/norway/2026). See /api/v1/countries for the endpoints each country supports."
    )
    c, _ = make((400, LIMIT_HEADERS, error_body("unsupported_country", message, "https://calcbloc.com/developers")))
    with pytest.raises(CalcBlocError) as e:
        c.net_salary("norway", 600_000)
    err = e.value
    assert type(err) is CalcBlocError
    assert (err.status, err.code, err.message, err.docs) == (400, "unsupported_country", message, "https://calcbloc.com/developers")
    assert err.body is not None and err.body["attribution"] == ATTRIBUTION
    assert str(err).startswith("[400 unsupported_country]")


@pytest.mark.parametrize("code", ["api_key_required", "invalid_key"])
def test_401_is_authentication_error(code: str) -> None:
    c, _ = make((401, {}, error_body(code, "This endpoint needs a free API key: send it in the X-API-Key header.", "https://calcbloc.com/developers/keys")))
    with pytest.raises(AuthenticationError) as e:
        c.net_salary("uk", 30_000)
    assert e.value.code == code and e.value.status == 401


def test_429_is_rate_limit_error() -> None:
    headers = {"Retry-After": "42", "X-RateLimit-Limit": "50", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "7200"}
    c, _ = make((429, headers, error_body("rate_limited", "Too many requests this minute (limit 5).", "https://calcbloc.com/developers#limits")))
    with pytest.raises(RateLimitError) as e:
        c.tax_tables("uk")
    err = e.value
    assert (err.status, err.code, err.retry_after, err.limit, err.remaining, err.reset) == (429, "rate_limited", 42, 50, 0, 7200)
    assert err.docs == "https://calcbloc.com/developers#limits"
    assert isinstance(err, CalcBlocError)


def test_404_unsupported_year() -> None:
    c, _ = make((404, {}, error_body("unsupported_year", 'No United Kingdom tax tables for "1999". Years: 2026-27, 2025-26 (or latest).')))
    with pytest.raises(CalcBlocError) as e:
        c.tax_tables("uk", "1999")
    assert (e.value.status, e.value.code) == (404, "unsupported_year")


def test_non_json_error_body() -> None:
    c, _ = make((502, {"Content-Type": "text/html"}, b"<html>Bad gateway</html>"))
    with pytest.raises(CalcBlocError) as e:
        c.countries()
    assert (e.value.status, e.value.code, e.value.body) == (502, "http_error", None)


def test_invalid_json_success_body() -> None:
    c, _ = make((200, {}, b"not json"))
    with pytest.raises(CalcBlocError) as e:
        c.countries()
    assert e.value.code == "invalid_response"


def test_openapi_path() -> None:
    c, t = make((200, {}, {"openapi": "3.1.0", "info": {"version": "1.2.0"}}))
    assert c.openapi()["openapi"] == "3.1.0"
    assert t.calls[0]["path"] == "/api/openapi.json"


# ------------------------------------------------------------------ default urllib transport (urlopen patched)


class FakeHTTPResponse:
    def __init__(self, status: int, headers: Dict[str, str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


def test_urllib_transport_success(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: Dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float) -> FakeHTTPResponse:
        seen.update(url=req.full_url, method=req.get_method(), key=req.get_header("X-api-key"), timeout=timeout)
        return FakeHTTPResponse(200, {"X-RateLimit-Limit": "5000"}, b'{"countries": []}')

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    c = Client(api_key="k", timeout=3)
    assert c.countries() == {"countries": []}
    assert seen == {"url": "https://calcbloc.com/api/v1/countries", "method": "GET", "key": "k", "timeout": 3}
    assert c.last_rate_limit is not None and c.last_rate_limit.limit == 5000


def test_urllib_transport_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps(error_body("invalid_parameter", 'Parameter "region" must be one of: ab, bc.')).encode()

    def fake_urlopen(req: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {"Content-Type": "application/json"}, io.BytesIO(body))  # type: ignore[arg-type]

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(CalcBlocError) as e:
        Client().tax_tables("canada", region="zz")
    assert (e.value.status, e.value.code) == (400, "invalid_parameter")


def test_urllib_transport_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req: Any, timeout: float) -> Any:
        raise urllib.error.URLError("Name or service not known")

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(NetworkError) as e:
        Client().countries()
    assert e.value.status is None and e.value.code == "network_error"


def test_urllib_transport_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req: Any, timeout: float) -> Any:
        raise TimeoutError("timed out")

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(NetworkError):
        Client().countries()
