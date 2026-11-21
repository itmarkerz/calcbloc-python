"""Country identifiers, as the CalcBloc API accepts them since 1.7.

Every country has a key (``"new-zealand"``: the id used in URLs, the bundled data and every response), a short
code (ISO 3166-1 alpha-2 in lower case, with the UK as ``"uk"``; ``"gb"`` also works), an ISO code (``"NZ"``)
and an English name (``"New Zealand"``), plus a few common variants. Matching ignores case and accents; spaces,
dots and underscores count as hyphens. Mirrors the API's own table.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Mapping, Optional, Tuple

__all__ = ["COUNTRY_CODES", "norm_key", "resolve_country_key"]

# key: (short code, ISO code, English name, other names)
COUNTRY_CODES: Dict[str, Tuple[str, str, str, Tuple[str, ...]]] = {
    "us": ("us", "US", "United States", ("usa", "united states of america", "america")),
    "uk": ("uk", "GB", "United Kingdom", ("gb", "gbr", "great britain", "britain", "england", "scotland", "wales", "northern ireland")),
    "australia": ("au", "AU", "Australia", ("aus",)),
    "new-zealand": ("nz", "NZ", "New Zealand", ("nzl", "aotearoa")),
    "canada": ("ca", "CA", "Canada", ("can",)),
    "ireland": ("ie", "IE", "Ireland", ("irl", "eire", "republic of ireland")),
    "india": ("in", "IN", "India", ("ind", "bharat")),
    "germany": ("de", "DE", "Germany", ("deu", "deutschland")),
    "spain": ("es", "ES", "Spain", ("esp", "espana")),
    "netherlands": ("nl", "NL", "Netherlands", ("nld", "the netherlands", "holland", "nederland")),
    "france": ("fr", "FR", "France", ("fra",)),
    "singapore": ("sg", "SG", "Singapore", ("sgp",)),
    "uae": ("ae", "AE", "United Arab Emirates", ("are", "emirates")),
    "italy": ("it", "IT", "Italy", ("ita", "italia")),
    "portugal": ("pt", "PT", "Portugal", ("prt",)),
    "belgium": ("be", "BE", "Belgium", ("bel", "belgie", "belgique")),
    "switzerland": ("ch", "CH", "Switzerland", ("che", "schweiz", "suisse", "svizzera")),
    "denmark": ("dk", "DK", "Denmark", ("dnk", "danmark")),
    "sweden": ("se", "SE", "Sweden", ("swe", "sverige")),
    "austria": ("at", "AT", "Austria", ("aut", "osterreich")),
    "poland": ("pl", "PL", "Poland", ("pol", "polska")),
    "luxembourg": ("lu", "LU", "Luxembourg", ("lux",)),
    "czechia": ("cz", "CZ", "Czechia", ("cze", "czech republic", "cesko")),
    "norway": ("no", "NO", "Norway", ("nor", "norge")),
    "finland": ("fi", "FI", "Finland", ("fin", "suomi")),
    "slovenia": ("si", "SI", "Slovenia", ("svn", "slovenija")),
    "romania": ("ro", "RO", "Romania", ("rou",)),
    "hungary": ("hu", "HU", "Hungary", ("hun", "magyarorszag")),
    "slovakia": ("sk", "SK", "Slovakia", ("svk", "slovensko")),
    "greece": ("gr", "GR", "Greece", ("grc", "hellas", "ελλαδα")),
    "latvia": ("lv", "LV", "Latvia", ("lva", "latvija")),
    "croatia": ("hr", "HR", "Croatia", ("hrv", "hrvatska")),
    "estonia": ("ee", "EE", "Estonia", ("est", "eesti")),
    "bulgaria": ("bg", "BG", "Bulgaria", ("bgr", "българия")),
    "lithuania": ("lt", "LT", "Lithuania", ("ltu", "lietuva")),
    "malta": ("mt", "MT", "Malta", ("mlt",)),
    "cyprus": ("cy", "CY", "Cyprus", ("cyp", "κυπρος")),
    "iceland": ("is", "IS", "Iceland", ("isl", "island")),
    "ukraine": ("ua", "UA", "Ukraine", ("ukr", "ukraina", "україна")),
    "liechtenstein": ("li", "LI", "Liechtenstein", ("lie",)),
    "serbia": ("rs", "RS", "Serbia", ("srb", "srbija", "србија")),
    "turkey": ("tr", "TR", "Türkiye", ("tur", "turkiye")),
}

_SEPARATORS = re.compile(r"[\s_.]+")


def norm_key(value: str) -> str:
    """Lower case, accents removed, spaces/dots/underscores turned into hyphens."""
    decomposed = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in decomposed if not ("̀" <= ch <= "ͯ"))
    return _SEPARATORS.sub("-", stripped.strip().lower())


def _build_aliases() -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for key, (short, iso, name, names) in COUNTRY_CODES.items():
        candidates: List[str] = [key, short, iso, name, *names]
        for alias in candidates:
            k = norm_key(alias)
            prev = aliases.get(k)
            if prev is not None and prev != key:
                raise RuntimeError(f'country alias "{alias}" maps to both {prev} and {key}')
            aliases[k] = key
    return aliases


_ALIASES = _build_aliases()


def resolve_country_key(value: str, names: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The country key (``"new-zealand"``) for a key, short code (``"nz"``), ISO code (``"NZ"``), English name
    (``"New Zealand"``) or listed variant; ``None`` when nothing matches.

    ``names`` adds further key -> name pairs (for example from the bundled manifest).
    """
    k = norm_key(value)
    if not k:
        return None
    hit = _ALIASES.get(k)
    if hit is not None:
        return hit
    for key, name in (names or {}).items():
        if norm_key(key) == k or norm_key(name) == k:
            return key
    return None
