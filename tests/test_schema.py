"""Sanity checks on every bundled table: shape, provenance of every figure, band arithmetic preconditions."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, Tuple

import pytest

from calcbloc import tables

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GROUPS = {"income-tax", "employee", "employer", "other"}
UNITS = {"rate", "money", "number", "text"}
ROW_STATUSES = {"verified", "under_review", "not_applicable"}


def all_tables() -> Iterator[Tuple[str, Dict[str, Any]]]:
    for rel in tables.bundled_files():
        yield rel, tables.load(*rel[: -len(".json")].split("/"))


ALL = list(all_tables())
IDS = [rel for rel, _ in ALL]


@pytest.mark.parametrize("rel, t", ALL, ids=IDS)
def test_top_level_shape(rel: str, t: Dict[str, Any]) -> None:
    for key in ("country", "countryName", "year", "currency", "effectiveFrom", "effectiveTo", "status", "sections", "sources", "rows", "pageUrl", "attribution", "years_available", "current_year"):
        assert key in t, f"{rel}: missing {key}"
    assert DATE.match(t["effectiveFrom"]) and DATE.match(t["effectiveTo"]), rel
    assert t["effectiveFrom"] <= t["effectiveTo"], rel
    assert t["status"] in ("verified", "unverified"), rel
    assert t["year"] in t["years_available"], rel
    assert t["pageUrl"].startswith("https://calcbloc.com/"), rel
    assert t["attribution"]["licence"] == "CC BY 4.0", rel
    assert t["attribution"]["credit"] == "Data by CalcBloc (calcbloc.com/data)", rel
    assert t["sources"], f"{rel}: no sources"
    for s in t["sources"]:
        assert s["url"].startswith(("https://", "http://")) and s["title"], rel


@pytest.mark.parametrize("rel, t", ALL, ids=IDS)
def test_every_row_has_a_source_url_and_retrieval_date(rel: str, t: Dict[str, Any]) -> None:
    assert t["rows"], f"{rel}: no rows"
    section_ids = {s["id"] for s in t["sections"]}
    for i, row in enumerate(t["rows"]):
        where = f"{rel} rows[{i}] {row.get('section_id')}/{row.get('label')}"
        assert row.get("source_url", "").startswith(("https://", "http://")), f"{where}: no source_url"
        assert DATE.match(row.get("retrieved_at") or ""), f"{where}: no retrieved_at date"
        assert row.get("source_title"), f"{where}: no source_title"
        assert row["section_id"] in section_ids, f"{where}: unknown section"
        assert row["tax_year"] == t["year"], where
        assert row["group"] in GROUPS, where
        assert row["unit"] in UNITS, where
        assert row["status"] in ROW_STATUSES, where
        assert DATE.match(row["effective_from"]), where
        assert row["effective_to"] is None or DATE.match(row["effective_to"]), where


@pytest.mark.parametrize("rel, t", ALL, ids=IDS)
def test_sections(rel: str, t: Dict[str, Any]) -> None:
    ids = [s["id"] for s in t["sections"]]
    assert len(ids) == len(set(ids)), f"{rel}: duplicate section ids"
    for s in t["sections"]:
        where = f"{rel} {s['id']}"
        assert s["kind"] in ("bands", "values"), where
        assert s["group"] in GROUPS, where
        assert s["source"]["url"].startswith(("https://", "http://")), where
        assert DATE.match(s["source"]["retrievedAt"]), where
        assert s["rows"], f"{where}: empty section"
        if s["kind"] == "bands":
            prev_from = None
            for r in s["rows"]:
                assert isinstance(r["from"], (int, float)) and isinstance(r["rate"], (int, float)), where
                assert r["to"] is None or r["to"] >= r["from"], where
                assert 0 <= r["rate"] <= 1, f"{where}: rate {r['rate']} is not a decimal"
                assert prev_from is None or r["from"] >= prev_from, f"{where}: bands out of order"
                prev_from = r["from"]


def test_manifest_lists_consistent_years_and_files() -> None:
    for c in tables.manifest()["countries"]:
        assert c["current_year"] == c["years"][0], c["country"]
        national = {f[: -len(".json")].split("/")[1] for f in c["files"] if f.count("/") == 1}
        assert national == set(c["years"]), c["country"]
        assert c["apiUrl"].startswith("https://calcbloc.com/api/v1/tax-tables/"), c["country"]
        region_codes = {r["code"] for r in c.get("regions", [])}
        for f in c["files"]:
            if f.count("/") == 2:
                assert f[: -len(".json")].split("/")[2] in region_codes, f
