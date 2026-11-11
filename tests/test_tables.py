"""Offline loader: lookups, errors and consistency between the manifest and the bundled files."""

from __future__ import annotations

from importlib import resources

import pytest

import calcbloc
from calcbloc import TableNotFoundError, tables


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
