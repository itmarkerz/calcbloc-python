"""Typed client for the CalcBloc API (https://calcbloc.com/developers).

Uses only the Python standard library (:mod:`urllib.request`). All endpoints are ``GET`` requests under
``/api/v1``. Every endpoint works without a key for 50 requests a day (5 a minute) per IP address; a free API
key, sent in the ``X-API-Key`` header, raises that to 5,000 a day (60 a minute). When the free allowance
without a key is used up, :class:`RateLimitError` says so and links to the keys page.

Example:
    >>> from calcbloc import Client
    >>> client = Client(api_key="cb_live_...")          # or Client(): no key, or CALCBLOC_API_KEY
    >>> table = client.tax_tables("canada", region="on")
    >>> pay = client.net_salary("uk", 45_000, region="scotland", pension_pct=5)
    >>> pay["summary"]["netAnnual"]
"""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Literal, Mapping, Optional, Tuple, Union, overload

from ._version import __version__
from .errors import AuthenticationError, CalcBlocError, NetworkError, RateLimitError
from .types import CalculationResponse, CompareResponse, CountriesResponse, RateLimit, TaxTable

__all__ = ["Client", "Response", "Transport", "DEFAULT_BASE_URL", "DEFAULT_TIMEOUT"]

DEFAULT_BASE_URL = "https://calcbloc.com"
DEFAULT_TIMEOUT = 30.0
API_KEY_ENV = "CALCBLOC_API_KEY"
KEYS_URL = "https://calcbloc.com/developers/keys?utm_source=calcbloc-python&utm_medium=app&utm_campaign=itmarkerz-oss"
"""Where to get a free API key (shown in the error raised when the free allowance without a key is used up)."""

Response = Tuple[int, Mapping[str, str], bytes]
"""What a transport returns: ``(status, headers, body)``. Header names are matched case-insensitively."""

Transport = Callable[[str, Mapping[str, str], float], Response]
"""A function ``(url, headers, timeout) -> (status, headers, body)`` that performs one GET request.

The default uses :mod:`urllib.request`. Pass your own to :class:`Client` to add a proxy, retries or caching,
or to test without a network.
"""

ParamValue = Union[str, int, float, bool, None]

_SEGMENT = re.compile(r"^[A-Za-z0-9-]{1,40}$")


def _no_key_limit_message(api_message: str, retry_after: Optional[int]) -> str:
    """The 429 message without a key: the free allowance is used up; add a free key and how to set it."""
    per_minute = "minute" in api_message.lower() and (retry_after is None or retry_after <= 60)
    used_up = (
        "The free allowance without a key (5 requests a minute, 50 a day) is used up for this minute."
        if per_minute
        else "The free allowance of 50 requests a day without a key is used up."
    )
    return (
        f"{used_up} Add your free API key (5,000 requests a day): {KEYS_URL} "
        f'(set it with Client(api_key="...") or the {API_KEY_ENV} environment variable).'
    )


def urllib_transport(url: str, headers: Mapping[str, str], timeout: float) -> Response:
    """Default transport: one GET with :func:`urllib.request.urlopen`. HTTP errors are returned, not raised."""
    req = urllib.request.Request(url, headers=dict(headers), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https URL built by the client)
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp is not None else b""
        return e.code, dict(e.headers.items()) if e.headers else {}, body
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        reason = getattr(e, "reason", e)
        raise NetworkError(f"Could not reach {url.split('?')[0]}: {reason}", code="network_error") from e


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return None


def _int_header(headers: Mapping[str, str], name: str) -> Optional[int]:
    v = _header(headers, name)
    if v is None:
        return None
    try:
        return int(float(v.strip()))
    except ValueError:
        return None


def _query_value(v: Union[str, int, float, bool]) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _segment(value: str, name: str) -> str:
    s = str(value).strip()
    if not _SEGMENT.match(s):
        raise ValueError(f"{name} must be 1-40 letters, digits or hyphens, got {value!r}")
    return s


class Client:
    """Client for the CalcBloc API.

    Args:
        api_key: Your API key (free at https://calcbloc.com/developers/keys). Defaults to the
            ``CALCBLOC_API_KEY`` environment variable. Optional: without a key every endpoint works for
            50 requests a day and 5 a minute per IP address; a free key allows 5,000 a day and 60 a minute.
        base_url: Server to call. Defaults to ``https://calcbloc.com``.
        timeout: Seconds to wait for a response.
        user_agent: Overrides the ``User-Agent`` header.
        transport: Function that performs the HTTP request (see :data:`Transport`); defaults to urllib.

    Attributes:
        last_rate_limit: Rate-limit headers of the most recent response (``None`` before the first call).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: Optional[str] = None,
        transport: Optional[Transport] = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self.api_key: Optional[str] = key.strip() if key and key.strip() else None
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent or f"calcbloc-python/{__version__} (+https://github.com/itmarkerz/calcbloc-python)"
        self._transport: Transport = transport or urllib_transport
        self.last_rate_limit: Optional[RateLimit] = None

    def __repr__(self) -> str:
        return f"Client(base_url={self.base_url!r}, api_key={'set' if self.api_key else None})"

    # ------------------------------------------------------------------ transport

    def _request(self, path: str, params: Optional[Mapping[str, ParamValue]] = None, *, accept: str = "application/json") -> Tuple[Mapping[str, str], bytes]:
        query: Dict[str, str] = {}
        for k, v in (params or {}).items():
            if k == "key":
                raise ValueError("Pass the API key as Client(api_key=...): keys in the URL are refused by the API.")
            if v is not None:
                query[k] = _query_value(v)
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        headers = {"Accept": accept, "User-Agent": self.user_agent}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        status, resp_headers, body = self._transport(url, headers, self.timeout)
        limit, remaining, reset = (
            _int_header(resp_headers, "X-RateLimit-Limit"),
            _int_header(resp_headers, "X-RateLimit-Remaining"),
            _int_header(resp_headers, "X-RateLimit-Reset"),
        )
        if limit is not None or remaining is not None or reset is not None:
            self.last_rate_limit = RateLimit(limit=limit, remaining=remaining, reset=reset)
        if status >= 400:
            raise self._error(status, resp_headers, body)
        return resp_headers, body

    def _error(self, status: int, headers: Mapping[str, str], body: bytes) -> CalcBlocError:
        payload: Optional[Dict[str, Any]] = None
        try:
            decoded = json.loads(body.decode("utf-8")) if body else None
            payload = decoded if isinstance(decoded, dict) else None
        except (ValueError, UnicodeDecodeError):
            payload = None
        err = payload.get("error") if payload else None
        if isinstance(err, dict):
            code = str(err.get("code") or "error")
            message = str(err.get("message") or f"HTTP {status}")
            docs = err.get("docs")
        else:
            code, message, docs = "http_error", f"HTTP {status} from {self.base_url} (not a CalcBloc API error body).", None
        kwargs: Dict[str, Any] = {"code": code, "status": status, "docs": docs if isinstance(docs, str) else None, "body": payload}
        if status == 429 or code == "rate_limited":
            retry_after = _int_header(headers, "Retry-After")
            return RateLimitError(
                message if self.api_key else _no_key_limit_message(message, retry_after),
                retry_after=retry_after,
                limit=_int_header(headers, "X-RateLimit-Limit"),
                remaining=_int_header(headers, "X-RateLimit-Remaining"),
                reset=_int_header(headers, "X-RateLimit-Reset"),
                **kwargs,
            )
        if status == 401:
            return AuthenticationError(message, **kwargs)
        return CalcBlocError(message, **kwargs)

    def _json(self, path: str, params: Optional[Mapping[str, ParamValue]] = None) -> Any:
        _, body = self._request(path, params)
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise CalcBlocError(f"The response from {path} is not valid JSON.", code="invalid_response") from e

    # ------------------------------------------------------------------ reference data

    def countries(self) -> CountriesResponse:
        """``GET /api/v1/countries``: every country with its tax years, regions, endpoints and parameters.

        ``tables_only: True`` marks a country with tax tables but no calculation engine yet; the calculation
        endpoints refuse it with ``400 unsupported_country``.
        """
        data: CountriesResponse = self._json("/api/v1/countries")
        return data

    @overload
    def tax_tables(self, country: str, year: Union[str, int] = ..., region: Optional[str] = ..., format: Literal["json"] = ...) -> TaxTable: ...

    @overload
    def tax_tables(self, country: str, year: Union[str, int] = ..., region: Optional[str] = ..., *, format: Literal["csv"]) -> str: ...

    def tax_tables(self, country: str, year: Union[str, int] = "latest", region: Optional[str] = None, format: str = "json") -> Union[TaxTable, str]:
        """``GET /api/v1/tax-tables/{country}/{year}``: the official tax tables for a country and tax year.

        Args:
            country: Country code, e.g. ``"us"``, ``"uk"``, ``"germany"``.
            year: A tax year from ``years_available`` (``"2026"``, ``"2026-27"``) or ``"latest"`` (default).
            region: Optional region code (US state ``"ca"``, Canadian province ``"on"``, ``"scotland"``...).
            format: ``"json"`` (default) returns a dict; ``"csv"`` returns the CSV text (one row per band or value).
        """
        if format not in ("json", "csv"):
            raise ValueError('format must be "json" or "csv"')
        path = f"/api/v1/tax-tables/{_segment(country, 'country').lower()}/{_segment(str(year), 'year')}"
        params: Dict[str, ParamValue] = {"region": region}
        if format == "csv":
            params["format"] = "csv"
            _, body = self._request(path, params, accept="text/csv")
            return body.decode("utf-8")
        data: TaxTable = self._json(path, params)
        return data

    def openapi(self) -> Dict[str, Any]:
        """``GET /api/openapi.json``: the OpenAPI 3.1 description of the API."""
        data: Dict[str, Any] = self._json("/api/openapi.json")
        return data

    # ------------------------------------------------------------------ calculations

    def net_salary(self, country: str, salary: float, *, region: Optional[str] = None, year: Optional[str] = None, **params: ParamValue) -> CalculationResponse:
        """``GET /api/v1/net-salary``: take-home pay for an annual salary (no key needed for 50 a day).

        Args:
            country: Country code with a take-home engine (see ``countries()``; ``tables_only`` countries
                are refused with ``unsupported_country``).
            salary: Annual gross salary in the country's currency (India: annual CTC).
            region: Region where the country needs one (US: state code, required; UK: ``england``,
                ``scotland`` or ``wales``; Canada: province).
            year: ``"latest"`` or the current tax year; calculations use the current year only.
            **params: Country-specific parameters by their API names, e.g. ``filing_status="single"`` (US),
                ``pension_pct=5`` (UK), ``student_loan="plan2"``. Booleans are sent as ``true``/``false``.
                Unknown names are rejected by the API with ``400 unknown_parameter``.
        """
        data: CalculationResponse = self._json("/api/v1/net-salary", {"country": country, "salary": salary, "region": region, "year": year, **params})
        return data

    def employer_cost(self, country: str, salary: float, *, region: Optional[str] = None, year: Optional[str] = None, **params: ParamValue) -> CalculationResponse:
        """``GET /api/v1/employer-cost``: total cost of employing someone on ``salary`` (no key needed for 50 a day).

        Takes the same arguments as :meth:`net_salary`; the country-specific parameters differ (for example
        ``health_per_month`` for the US or ``ni_category`` for the UK). ``countries()`` lists them.
        """
        data: CalculationResponse = self._json("/api/v1/employer-cost", {"country": country, "salary": salary, "region": region, "year": year, **params})
        return data

    def compare(
        self,
        a: str,
        b: str,
        salary: float,
        *,
        currency: Optional[str] = None,
        us_state: Optional[str] = None,
        uk_region: Optional[str] = None,
        ca_province: Optional[str] = None,
        in_state: Optional[str] = None,
    ) -> CompareResponse:
        """``GET /api/v1/compare``: the same salary in two countries (no key needed for 50 a day).

        The salary is converted at the European Central Bank reference rate and each country's take-home
        engine is run, as on https://calcbloc.com/compare/salary.

        Args:
            a: First country code.
            b: Second country code (must differ from ``a``).
            salary: Annual gross salary (India: CTC) in ``currency``.
            currency: ``a``'s or ``b``'s currency; defaults to ``a``'s.
            us_state: US state when ``a`` or ``b`` is ``"us"`` (API default ``ny``).
            uk_region: ``england``, ``scotland`` or ``wales`` (API default ``england``).
            ca_province: Canadian province or territory (API default ``on``).
            in_state: Indian state for professional tax and LWF (API default ``mh``).
        """
        data: CompareResponse = self._json(
            "/api/v1/compare",
            {"a": a, "b": b, "salary": salary, "currency": currency, "us_state": us_state, "uk_region": uk_region, "ca_province": ca_province, "in_state": in_state},
        )
        return data
