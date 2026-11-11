"""Offline access to the tax tables bundled with this package.

The bundled files are copies of the open CalcBloc dataset (https://calcbloc.com/data), in exactly the shape
the API returns from ``GET /api/v1/tax-tables/{country}/{year}``: income tax brackets, social security and
payroll rates, thresholds and allowances, each figure with its official source and retrieval date. Nothing
here touches the network.

Example:
    >>> from calcbloc import tables
    >>> tables.list_countries()[:3]
    ['us', 'uk', 'australia']
    >>> uk = tables.load("uk")                  # current tax year
    >>> uk["year"], uk["currency"]
    ('2026-27', 'GBP')
    >>> scotland = tables.load("uk", "2026-27", region="scotland")

Data licence: CC BY 4.0. Credit "Data by CalcBloc (calcbloc.com/data)" wherever you show the figures.
"""

from __future__ import annotations

import copy
import gzip
import json
from functools import lru_cache
from importlib import resources
from typing import Any, List, Optional, Union

from .errors import TableNotFoundError
from .types import Manifest, ManifestCountry, ManifestRegion, Section, TaxTable

__all__ = [
    "manifest",
    "list_countries",
    "country_info",
    "years",
    "regions",
    "load",
    "section",
    "bundled_files",
    "data_date",
]

_PACKAGE = "calcbloc"


def _root() -> Any:
    return resources.files(_PACKAGE).joinpath("data").joinpath("tables")


def _read(rel: str) -> bytes:
    """Reads a bundled file by its manifest path (``us/2026.json``), stored as ``.json.gz`` or ``.json``."""
    node = _root()
    parts = rel.split("/")
    for p in parts[:-1]:
        node = node.joinpath(p)
    gz = node.joinpath(parts[-1] + ".gz")
    if gz.is_file():
        return gzip.decompress(gz.read_bytes())
    plain = node.joinpath(parts[-1])
    if plain.is_file():
        return bytes(plain.read_bytes())
    raise TableNotFoundError(f"Bundled file {rel} is missing from the package.", code="not_found")


@lru_cache(maxsize=1)
def _manifest() -> Manifest:
    data: Manifest = json.loads(_read("manifest.json").decode("utf-8"))
    return data


def manifest() -> Manifest:
    """Return the manifest of the bundled data: countries, years, regions, page and API URLs, sources.

    The returned dictionary is a copy; changing it does not affect later calls.
    """
    return copy.deepcopy(_manifest())


def data_date() -> str:
    """Return the date the bundled data was generated (``manifest["generatedAt"]``, ISO 8601)."""
    return str(_manifest().get("generatedAt", ""))


def list_countries() -> List[str]:
    """Return the codes of every country with bundled tables, in manifest order (e.g. ``"us"``, ``"uk"``)."""
    return [c["country"] for c in _manifest().get("countries", [])]


def _country(country: str) -> ManifestCountry:
    code = str(country).strip().lower()
    for c in _manifest().get("countries", []):
        if c["country"] == code:
            return c
    raise TableNotFoundError(
        f'No bundled tax tables for "{country}". Countries: {", ".join(list_countries())}.',
        code="unsupported_country",
    )


def country_info(country: str) -> ManifestCountry:
    """Return the manifest entry for one country (name, currency, years, regions, page URL, sources...).

    Raises:
        TableNotFoundError: ``code == "unsupported_country"`` if the country is not bundled.
    """
    return copy.deepcopy(_country(country))


def years(country: str) -> List[str]:
    """Return the tax years bundled for ``country``, current year first (e.g. ``["2026-27", "2025-26"]``)."""
    return list(_country(country).get("years", []))


def regions(country: str) -> List[ManifestRegion]:
    """Return the regions of ``country`` (code, name, slug); empty if it has no regional tables."""
    return copy.deepcopy(list(_country(country).get("regions", [])))


def _year(c: ManifestCountry, year: Optional[Union[str, int]]) -> str:
    if year is None or str(year).strip().lower() == "latest":
        return c["current_year"]
    y = str(year).strip()
    if y not in c.get("years", []):
        raise TableNotFoundError(
            f'No {c["name"]} tax tables for "{y}". Years: {", ".join(c.get("years", []))} (or latest).',
            code="unsupported_year",
        )
    return y


def _region(c: ManifestCountry, region: str) -> ManifestRegion:
    wanted = str(region).strip().lower()
    available = c.get("regions", [])
    if not available:
        raise TableNotFoundError(f'{c["name"]} tax tables have no regional variants.', code="unsupported_region")
    for r in available:
        if wanted in (r["code"].lower(), str(r.get("slug", "")).lower()):
            return r
    codes = ", ".join(r["code"] for r in available)
    raise TableNotFoundError(f'Unknown region "{region}" for {c["name"]}. Regions: {codes}.', code="unsupported_region")


def load(country: str, year: Optional[Union[str, int]] = None, region: Optional[str] = None) -> TaxTable:
    """Load a bundled tax table.

    Args:
        country: Country code as listed by :func:`list_countries` (case-insensitive), e.g. ``"uk"``.
        year: A tax year from :func:`years` (``"2026"``, ``"2026-27"``; an int such as ``2026`` also works),
            or ``None``/``"latest"`` for the country's current tax year.
        region: Optional region code or slug (``"ca"`` or ``"california"``, ``"scotland"``, ``"zh"``). A regional
            table holds the regional figures only; load the national table for the national ones.

    Returns:
        The table, shaped like the API response (see :class:`calcbloc.types.TaxTable`). Each call returns a
        fresh dictionary.

    Raises:
        TableNotFoundError: With ``code`` ``unsupported_country``, ``unsupported_year`` or
            ``unsupported_region``, matching the API's error codes.
    """
    c = _country(country)
    y = _year(c, year)
    if region is None:
        rel = f'{c["country"]}/{y}.json'
    else:
        r = _region(c, region)
        rel = f'{c["country"]}/{y}/{r["code"]}.json'
    if rel not in c.get("files", []):
        raise TableNotFoundError(
            f"{rel} is not bundled with this version of the package. Fetch it from the API instead: "
            f"Client().tax_tables({c['country']!r}, {y!r}" + (f", region={region!r})" if region else ")"),
            code="unsupported_region" if region else "unsupported_year",
        )
    table: TaxTable = json.loads(_read(rel).decode("utf-8"))
    return table


def section(table: TaxTable, section_id: str) -> Section:
    """Return the section with ``id == section_id`` from a table (e.g. ``"income-tax-england"``).

    Raises:
        KeyError: If the table has no such section; the message lists the section ids it has.
    """
    for s in table.get("sections", []):
        if s.get("id") == section_id:
            return s
    ids = ", ".join(str(s.get("id")) for s in table.get("sections", []))
    raise KeyError(f'No section "{section_id}" in this table. Sections: {ids}.')


def bundled_files() -> List[str]:
    """Return the manifest path of every bundled table file (``"us/2026.json"``, ``"us/2026/ca.json"``...)."""
    return [f for c in _manifest().get("countries", []) for f in c.get("files", [])]
