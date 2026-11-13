#!/usr/bin/env python3
"""Copy the CalcBloc tax tables into the package and refresh the README coverage table.

Source of truth: the calcbloc-data repository, ``tables/`` directory, which holds ``manifest.json`` plus one
JSON file per country and tax year (``<country>/<year>.json``) and per region
(``<country>/<year>/<region>.json``), each in the exact shape of the API response.

Usage (from the repository root):

    python scripts/sync_tables.py                       # from ../calcbloc-data/tables
    python scripts/sync_tables.py --source PATH         # or CALCBLOC_DATA_TABLES=PATH
    python scripts/sync_tables.py --no-regions          # national tables only
    python scripts/sync_tables.py --exclude greece      # leave a country out (repeatable)
    python scripts/sync_tables.py --check               # exit 1 if the bundled data differs from the source

Every listed file is validated before anything is written: it must parse, match its path (country, year,
region) and give every flat row a ``source_url`` and ``retrieved_at``. Tables are stored gzip-compressed
(``.json.gz``, byte-identical JSON once decompressed, deterministic gzip header) to keep the wheel small;
``manifest.json`` is stored as plain JSON. Files no longer listed in the manifest are removed.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO.parent / "calcbloc-data" / "tables"
DEST = REPO / "src" / "calcbloc" / "data" / "tables"
README = REPO / "README.md"
START, END = "<!-- coverage:start -->", "<!-- coverage:end -->"
# Referral tag for the README's links to calcbloc.com (the bundled pageUrl values stay plain).
README_UTM = "utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss"


def readme_link(url: str) -> str:
    base, sep, fragment = url.partition("#")
    return f"{base}{'&' if '?' in base else '?'}{README_UTM}{sep}{fragment}"


def fail(msg: str) -> None:
    print(f"sync_tables: error: {msg}", file=sys.stderr)
    sys.exit(2)


def gz(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as f:
        f.write(data)
    return buf.getvalue()


def validate(rel: str, raw: bytes, country: Dict[str, Any]) -> None:
    try:
        t = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        fail(f"{rel}: not valid JSON ({e})")
    parts = rel[: -len(".json")].split("/")
    if t.get("country") != parts[0] or t.get("year") != parts[1]:
        fail(f"{rel}: country/year inside the file ({t.get('country')}/{t.get('year')}) do not match the path")
    region = t.get("region")
    if len(parts) == 3 and (not isinstance(region, dict) or region.get("code") != parts[2]):
        fail(f"{rel}: region inside the file does not match the path")
    if len(parts) == 2 and region is not None:
        fail(f"{rel}: national file carries a region")
    if parts[1] not in country.get("years", []):
        fail(f"{rel}: year {parts[1]} is not in the manifest's years for {parts[0]}")
    for key in ("sections", "rows", "sources", "attribution"):
        if key not in t:
            fail(f"{rel}: missing '{key}'")
    for i, row in enumerate(t["rows"]):
        if not row.get("source_url") or not row.get("retrieved_at"):
            fail(f"{rel}: rows[{i}] ({row.get('section_id')}/{row.get('label')}) has no source_url or retrieved_at")


def plan(source: Path, regions: bool, exclude: List[str]) -> Tuple[Dict[str, Any], Dict[str, bytes]]:
    """Reads and validates the source; returns the (filtered) manifest and {relative path: JSON bytes}."""
    mpath = source / "manifest.json"
    if not mpath.is_file():
        fail(f"no manifest.json in {source} (use --source or CALCBLOC_DATA_TABLES)")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    if not manifest.get("countries"):
        fail("manifest.json lists no countries")
    files: Dict[str, bytes] = {}
    kept = []
    for c in manifest["countries"]:
        if c["country"] in exclude:
            continue
        listed = c.get("files") or []
        chosen = [f for f in listed if regions or f.count("/") == 1]
        national = f"{c['country']}/{c['current_year']}.json"
        if national not in chosen:
            fail(f"{c['country']}: the current-year national table {national} is not listed in the manifest")
        for rel in chosen:
            p = source / rel
            if not p.is_file():
                fail(f"{rel} is listed in the manifest but missing from {source}")
            raw = p.read_bytes()
            validate(rel, raw, c)
            files[rel] = raw
        kept.append({**c, "files": chosen})
    unknown = sorted(set(exclude) - {c["country"] for c in manifest["countries"]})
    if unknown:
        fail(f"--exclude names countries not in the manifest: {', '.join(unknown)}")
    return {**manifest, "countries": kept}, files


def coverage_markdown(manifest: Dict[str, Any]) -> str:
    countries = manifest["countries"]
    regional = sum(len([f for f in c["files"] if f.count("/") == 2]) for c in countries)
    lines = [
        START,
        "",
        f"Bundled data generated {manifest.get('generatedAt', '?')}: **{len(countries)} countries**, "
        f"{sum(len(c['files']) for c in countries)} tables ({regional} of them regional). "
        "This table is generated from `manifest.json` by `scripts/sync_tables.py`.",
        "",
        "| Country | Code | Current tax year | Years bundled | Regional tables | Last checked | Tax tables page |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in countries:
        n_regions = len({f.split("/")[2] for f in c["files"] if f.count("/") == 2})
        page = readme_link(c["pageUrl"])
        lines.append(
            f"| [{c['name']}]({page}) | `{c['country']}` | {c['current_year']} | {', '.join(c['years'])} | "
            f"{n_regions or '-'} | {c.get('lastVerified', '-')} | [{c['name']} tax tables]({page}) |"
        )
    pending = manifest.get("pending") or []
    if pending:
        # Names only: the manifest's "reason" is an internal editorial note, not README copy.
        lines += ["", "Coming later (tables under review, not yet published): " + ", ".join(p["name"] for p in pending) + "."]
    lines += ["", END]
    return "\n".join(lines)


def update_readme(manifest: Dict[str, Any], check: bool) -> bool:
    if not README.is_file():
        return True
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("sync_tables: README has no coverage markers; skipped", file=sys.stderr)
        return True
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + coverage_markdown(manifest) + tail
    if new == text:
        return True
    if check:
        return False
    README.write_text(new, encoding="utf-8", newline="\n")
    return True


def existing(dest: Path) -> Dict[str, Path]:
    out = {}
    for p in dest.rglob("*"):
        if p.is_file():
            rel = p.relative_to(dest).as_posix()
            out[rel[:-3] if rel.endswith(".gz") else rel] = p
    return out


def read_stored(p: Path) -> bytes:
    data = p.read_bytes()
    return gzip.decompress(data) if p.suffix == ".gz" else data


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", type=Path, default=Path(os.environ.get("CALCBLOC_DATA_TABLES", DEFAULT_SOURCE)), help=f"tables directory (default: $CALCBLOC_DATA_TABLES or {DEFAULT_SOURCE})")
    ap.add_argument("--dest", type=Path, default=DEST, help="package data directory (default: src/calcbloc/data/tables)")
    ap.add_argument("--no-regions", action="store_true", help="bundle national tables only")
    ap.add_argument("--exclude", action="append", default=[], metavar="COUNTRY", help="leave a country out (repeatable)")
    ap.add_argument("--check", action="store_true", help="only compare; exit 1 if anything would change")
    args = ap.parse_args(argv)

    manifest, files = plan(args.source.resolve(), not args.no_regions, [e.lower() for e in args.exclude])
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    wanted: Dict[str, bytes] = {"manifest.json": manifest_bytes, **files}
    dest: Path = args.dest.resolve()
    have = existing(dest) if dest.is_dir() else {}

    changed = [rel for rel, data in wanted.items() if rel not in have or read_stored(have[rel]) != data]
    stale = sorted(set(have) - set(wanted))
    readme_ok = update_readme(manifest, check=True)

    if args.check:
        for rel in changed:
            print(f"differs: {rel}")
        for rel in stale:
            print(f"stale:   {rel}")
        if not readme_ok:
            print("differs: README.md coverage table")
        in_sync = not changed and not stale and readme_ok
        print("in sync" if in_sync else "out of sync: run scripts/sync_tables.py")
        return 0 if in_sync else 1

    for rel in stale:
        have[rel].unlink()
    for rel in changed:
        target = dest / (rel if rel == "manifest.json" else rel + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(wanted[rel] if rel == "manifest.json" else gz(wanted[rel]))
    for d in sorted((p for p in dest.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    update_readme(manifest, check=False)

    raw = sum(len(b) for b in wanted.values())
    stored = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    print(
        f"synced {len(manifest['countries'])} countries, {len(files)} tables from {args.source}: "
        f"{len(changed)} written, {len(stale)} removed; JSON {raw / 1e6:.2f} MB, stored {stored / 1e6:.2f} MB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
