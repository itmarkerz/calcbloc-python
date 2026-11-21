"""Offline loader: lookups, errors and consistency between the manifest and the bundled files."""

from __future__ import annotations

from importlib import resources

import pytest

import calcbloc
from calcbloc import TableNotFoundError, tables
from calcbloc._country_codes import COUNTRY_CODES, norm_key, resolve_country_key


def test_manifest_has_countries_and_metadata() -> None:
    m = tables.manifest()
    assert m["countries"], "no countries bundled"
    assert m["licence"] == "CC BY 4.0"
    assert m["credit"] == "Data by CalcBloc (calcbloc.com/data)"
    assert tables.data_date() == m["generatedAt"]
    assert tables.list_countries() == [c["country"] for c in m["countries"]]
    assert len(set(tables.list_countries())) == len(tables.list_countries())


def test_manifest_is_a_copy() -> None:
    m = tables.manifest()
    m["countries"].clear()
    assert tables.manifest()["countries"]


def test_bundled_files_match_the_package_directory() -> None:
    root = resources.files("calcbloc").joinpath("data").joinpath("tables")
    on_disk = set()
    stack = [("", root)]
    while stack:
        prefix, node = stack.pop()
        for child in node.iterdir():
            rel = f"{prefix}{child.name}"
            if child.is_dir():
                stack.append((rel + "/", child))
            else:
                on_disk.add(rel[:-3] if rel.endswith(".gz") else rel)
    on_disk.discard("manifest.json")
    assert on_disk == set(tables.bundled_files())


@pytest.mark.parametrize("country", tables.list_countries())
def test_every_country_loads_its_current_year(country: str) -> None:
    info = tables.country_info(country)
    t = tables.load(country)
    assert t["country"] == country
    assert t["year"] == info["current_year"] == t["current_year"]
    assert t["region"] is None
    assert t["currency"] == info["currency"]
    assert t["pageUrl"] == info["pageUrl"]
    assert tables.years(country)[0] == info["current_year"]


def test_every_bundled_file_loads() -> None:
    for rel in tables.bundled_files():
        parts = rel[: -len(".json")].split("/")
        t = tables.load(*parts)
        assert t["country"] == parts[0] and t["year"] == parts[1]
        if len(parts) == 3:
            assert t["region"] is not None and t["region"]["code"] == parts[2]


def test_latest_and_none_and_int_years() -> None:
    country = tables.list_countries()[0]
    current = tables.country_info(country)["current_year"]
    assert tables.load(country)["year"] == current
    assert tables.load(country, "latest")["year"] == current
    assert tables.load(country, "LATEST")["year"] == current
    four_digit = next((c for c in tables.list_countries() if tables.country_info(c)["current_year"].isdigit()), None)
    if four_digit:
        y = tables.country_info(four_digit)["current_year"]
        assert tables.load(four_digit, int(y))["year"] == y


def test_country_is_case_insensitive() -> None:
    country = tables.list_countries()[0]
    assert tables.load(country.upper())["country"] == country


def test_region_by_code_or_slug_case_insensitive() -> None:
    country = next(c for c in tables.list_countries() if tables.regions(c))
    region = tables.regions(country)[0]
    by_code = tables.load(country, region=region["code"].upper())
    by_slug = tables.load(country, region=region["slug"])
    assert by_code["region"]["code"] == by_slug["region"]["code"] == region["code"]


def test_load_returns_independent_copies() -> None:
    country = tables.list_countries()[0]
    a = tables.load(country)
    a["sections"].clear()
    assert tables.load(country)["sections"]


def test_unknown_country() -> None:
    with pytest.raises(TableNotFoundError) as e:
        tables.load("atlantis")
    assert e.value.code == "unsupported_country"
    assert isinstance(e.value, LookupError) and isinstance(e.value, calcbloc.CalcBlocError)
    assert tables.list_countries()[0] in e.value.message


@pytest.mark.parametrize("country", tables.list_countries())
def test_every_country_by_short_code_iso_code_and_name(country: str) -> None:
    short, iso, name, _ = COUNTRY_CODES[country]
    manifest_name = tables.country_info(country)["name"]
    for ident in (short, short.upper(), iso, iso.lower(), name, name.upper(), manifest_name, country, country.upper()):
        assert tables.country_info(ident)["country"] == country, ident


def test_new_zealand_uk_and_germany_by_any_identifier() -> None:
    nz = tables.load("new-zealand")
    for ident in ("nz", "NZ", "New Zealand", "new zealand", " NEW-ZEALAND "):
        assert tables.load(ident) == nz, ident
    assert tables.load("gb") == tables.load("uk")
    assert tables.load("GB", "2025-26", region="scotland") == tables.load("uk", "2025-26", region="scotland")
    assert tables.load("de") == tables.load("germany")
    assert tables.years("Germany") == tables.years("germany")
    assert tables.regions("ch") == tables.regions("switzerland")


@pytest.mark.parametrize("ident", ["atlantis", "xx", "", "New Atlantis"])
def test_unknown_identifiers_still_raise(ident: str) -> None:
    with pytest.raises(TableNotFoundError) as e:
        tables.load(ident)
    assert e.value.code == "unsupported_country"


def test_normalisation_matches_the_api() -> None:
    assert norm_key(" Türkiye ") == "turkiye"
    assert norm_key("New_Zealand") == "new-zealand"
    assert resolve_country_key("Türkiye") == "turkey"
    assert resolve_country_key("czech.republic") == "czechia"
    assert resolve_country_key("United Arab Emirates") == "uae"
    assert resolve_country_key("atlantis") is None


def test_unknown_year() -> None:
    with pytest.raises(TableNotFoundError) as e:
        tables.load(tables.list_countries()[0], "1999")
    assert e.value.code == "unsupported_year"


def test_unknown_region() -> None:
    country = next(c for c in tables.list_countries() if tables.regions(c))
    with pytest.raises(TableNotFoundError) as e:
        tables.load(country, region="nowhere")
    assert e.value.code == "unsupported_region"


def test_region_on_a_country_without_regions() -> None:
    country = next((c for c in tables.list_countries() if not tables.regions(c)), None)
    if country is None:
        pytest.skip("every bundled country has regions")
    with pytest.raises(TableNotFoundError) as e:
        tables.load(country, region="x")
    assert e.value.code == "unsupported_region"


def test_section_lookup() -> None:
    t = tables.load(tables.list_countries()[0])
    first = t["sections"][0]
    assert tables.section(t, first["id"]) == first
    with pytest.raises(KeyError, match=first["id"]):
        tables.section(t, "no-such-section")
