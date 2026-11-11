"""Typed shapes of CalcBloc tax tables and API responses.

These are :class:`typing.TypedDict` definitions: at runtime every value is a plain ``dict`` decoded from
JSON, so you can index it as usual, and type checkers (mypy, pyright) know the keys. Fields the API may add
in a later minor version are not listed; the dictionaries can carry extra keys.

Conventions used throughout the data:

* Money is in the country's currency, per year unless a field says otherwise.
* Rates are decimals: ``0.2`` means 20%.
* ``to: None`` on a band means "and above" (no upper limit).
* Dates are ISO 8601 strings (``"2026-04-06"``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

__all__ = [
    "Group",
    "Unit",
    "RowStatus",
    "Source",
    "SectionSource",
    "BandRow",
    "ValueRow",
    "SectionRow",
    "Section",
    "FlatRow",
    "Region",
    "TableAttribution",
    "ApiAttribution",
    "TaxTable",
    "ManifestRegion",
    "ManifestCountry",
    "PendingCountry",
    "Manifest",
    "CountryParameter",
    "CountryCalcEndpoint",
    "CountryTablesEndpoint",
    "CountryInfo",
    "CountriesResponse",
    "CalculationResponse",
    "CompareSide",
    "CompareResponse",
    "RateLimit",
    "BandSlice",
]

Group = Literal["income-tax", "employee", "employer", "other"]
"""Which part of the payroll a section belongs to."""

Unit = Literal["rate", "money", "number", "text"]
"""Unit of a flat row's value (``rate`` rows carry a decimal in ``rate``)."""

RowStatus = Literal["verified", "under_review", "not_applicable"]
"""Verification status of a single figure."""


class Source(TypedDict, total=False):
    """An official source document (``sources`` list of a table)."""

    title: str
    url: str
    retrievedAt: str
    effectiveFrom: str
    effectiveTo: str


class SectionSource(TypedDict, total=False):
    """The official source of one section (or of one row, when a row cites its own)."""

    title: str
    url: str
    retrievedAt: str


BandRow = TypedDict(
    "BandRow",
    {
        "label": str,
        "from": Union[int, float],
        "to": Optional[Union[int, float]],
        "rate": Union[int, float],
        "note": str,
        "source": SectionSource,
        "status": str,
    },
    total=False,
)
BandRow.__doc__ = """One band of a ``kind: "bands"`` section: income from ``from`` up to ``to`` is taxed at ``rate``."""


class ValueRow(TypedDict, total=False):
    """One figure of a ``kind: "values"`` section (a threshold, allowance, flat rate or note)."""

    label: str
    value: Union[int, float, str]
    unit: Unit
    note: str
    source: SectionSource
    status: str


SectionRow = Union[BandRow, ValueRow]


class Section(TypedDict, total=False):
    """A titled group of figures, e.g. the income tax bands or the employer social security rates."""

    id: str
    title: str
    group: Group
    kind: Literal["bands", "values"]
    rows: List[Dict[str, Any]]
    source: SectionSource
    verified: bool
    basis: str
    note: str


FlatRow = TypedDict(
    "FlatRow",
    {
        "section_id": str,
        "section": str,
        "group": Group,
        "basis": str,
        "note": str,
        "tax_year": str,
        "effective_from": str,
        "effective_to": Optional[str],
        "source_title": str,
        "source_url": str,
        "retrieved_at": str,
        "status": RowStatus,
        "label": str,
        "from": Optional[Union[int, float]],
        "to": Optional[Union[int, float]],
        "rate": Optional[Union[int, float]],
        "value": Optional[Union[int, float, str]],
        "unit": Unit,
    },
    total=False,
)
FlatRow.__doc__ = """One band or value as a flat record (the same rows as the CSV download), with its own source."""


class Region(TypedDict, total=False):
    """A region of a regional table (US state, Canadian province, Scotland, a Swiss canton...)."""

    code: str
    slug: str
    name: str


class TableAttribution(TypedDict, total=False):
    """Attribution block of a bundled table file."""

    source: str
    url: str
    licence: str
    credit: str


class ApiAttribution(TypedDict, total=False):
    """Attribution block the API adds to every response."""

    source: str
    url: str
    required: bool
    text: str


class TaxTable(TypedDict, total=False):
    """A tax table: the response of ``GET /api/v1/tax-tables/{country}/{year}``, and every bundled file."""

    country: str
    countryName: str
    year: str
    yearLabel: str
    isCurrent: bool
    region: Optional[Region]
    currency: str
    effectiveFrom: str
    effectiveTo: str
    status: Literal["verified", "unverified"]
    underReview: List[str]
    dataVerified: bool
    notice: str
    sections: List[Section]
    sources: List[Source]
    requested_year: str
    current_year: str
    years_available: List[str]
    rows: List[FlatRow]
    pageUrl: str
    attribution: Dict[str, Any]


class ManifestRegion(TypedDict, total=False):
    code: str
    name: str
    slug: str


class ManifestCountry(TypedDict, total=False):
    """One country in ``manifest.json``."""

    country: str
    name: str
    currency: str
    current_year: str
    years: List[str]
    regions: List[ManifestRegion]
    files: List[str]
    pageUrl: str
    apiUrl: str
    lastVerified: str
    sourceUrls: List[str]
    rowCount: int
    underReviewRows: int


class PendingCountry(TypedDict, total=False):
    """A country announced but not yet published, with the reason."""

    country: str
    name: str
    reason: str


class Manifest(TypedDict, total=False):
    """The index of the bundled tables (``manifest.json``)."""

    generatedAt: str
    source: str
    licence: str
    credit: str
    api: str
    countries: List[ManifestCountry]
    pending: List[PendingCountry]


class CountryParameter(TypedDict, total=False):
    """A query parameter a calculation endpoint accepts for one country."""

    name: str
    type: Literal["number", "integer", "boolean", "enum"]
    required: bool
    values: List[str]
    min: float
    max: float
    default: Union[str, int, float, bool]
    unit: str
    description: str


class CountryCalcEndpoint(TypedDict, total=False):
    path: str
    calculatorUrl: str
    parameters: List[CountryParameter]


class CountryTablesEndpoint(TypedDict, total=False):
    path: str
    pageUrl: str
    years: List[str]
    current_year: str
    years_available: List[str]
    latestPath: str
    regions: List[Dict[str, str]]
    formats: List[str]


class CountryInfo(TypedDict, total=False):
    """One entry of ``GET /api/v1/countries``."""

    code: str
    name: str
    currency: str
    years: List[str]
    current_year: str
    years_available: List[str]
    available_endpoints: List[str]
    tables_only: bool
    endpoints: Dict[str, Any]


class CountriesResponse(TypedDict, total=False):
    countries: List[CountryInfo]
    attribution: ApiAttribution


class CalculationResponse(TypedDict, total=False):
    """Response of ``GET /api/v1/net-salary`` and ``GET /api/v1/employer-cost``."""

    endpoint: str
    country: str
    countryName: str
    year: str
    requested_year: str
    currency: str
    inputs: Dict[str, Any]
    summary: Dict[str, Optional[float]]
    results: Dict[str, float]
    breakdown: Optional[Dict[str, Any]]
    notes: List[str]
    calculatorUrl: str
    warnings: List[str]
    attribution: ApiAttribution


class CompareSide(TypedDict, total=False):
    country: str
    place: str
    currency: str
    gross: float
    incomeTax: float
    contributions: float
    retained: float
    net: float
    effectiveRate: float
    grossInOtherCurrency: float
    netInOtherCurrency: float
    parts: List[Dict[str, Any]]
    assumptions: List[str]


class CompareResponse(TypedDict, total=False):
    """Response of ``GET /api/v1/compare``."""

    endpoint: str
    inputs: Dict[str, Any]
    a: CompareSide
    b: CompareSide
    exchangeRate: Dict[str, Any]
    difference: Dict[str, Any]
    interpretation: str
    calculatorUrl: str
    warnings: List[str]
    attribution: ApiAttribution


@dataclass(frozen=True)
class RateLimit:
    """Rate-limit headers of the last API response.

    Attributes:
        limit: Requests allowed per day for this key or IP address.
        remaining: Requests left today.
        reset: Seconds until the daily window resets (UTC midnight).
    """

    limit: Optional[int]
    remaining: Optional[int]
    reset: Optional[int]


@dataclass(frozen=True)
class BandSlice:
    """The part of an income that falls in one band (see :func:`calcbloc.band_breakdown`).

    Attributes:
        label: The band's label, or ``None`` when the table gives none.
        lower: Lower edge of the band (``from`` in the data).
        upper: Upper edge of the band, or ``None`` for an open top band (``to`` in the data).
        rate: The band's rate as a decimal.
        amount: How much of the income falls in this band.
        tax: ``amount * rate``.
    """

    label: Optional[str]
    lower: float
    upper: Optional[float]
    rate: float
    amount: float
    tax: float
