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
    "japan": ("jp", "JP", "Japan", ("jpn", "nippon", "nihon", "日本")),
    "south-korea": ("kr", "KR", "South Korea", ("kor", "korea", "republic of korea", "대한민국", "한국")),
    "mexico": ("mx", "MX", "Mexico", ("mex", "méxico", "estados unidos mexicanos")),
    "brazil": ("br", "BR", "Brazil", ("bra", "brasil", "república federativa do brasil")),
    "chile": ("cl", "CL", "Chile", ("chl", "república de chile")),
    "colombia": ("co", "CO", "Colombia", ("col", "república de colombia")),
    "argentina": ("ar", "AR", "Argentina", ("arg", "república argentina")),
    "costa-rica": ("cr", "CR", "Costa Rica", ("cri", "república de costa rica")),
    "saudi-arabia": ("sa", "SA", "Saudi Arabia", ("sau", "ksa", "saudi", "kingdom of saudi arabia", "المملكة العربية السعودية", "السعودية")),
    "qatar": ("qa", "QA", "Qatar", ("qat", "state of qatar", "دولة قطر", "قطر")),
    "kuwait": ("kw", "KW", "Kuwait", ("kwt", "state of kuwait", "دولة الكويت", "الكويت")),
    "bahrain": ("bh", "BH", "Bahrain", ("bhr", "kingdom of bahrain", "مملكة البحرين", "البحرين")),
    "oman": ("om", "OM", "Oman", ("omn", "sultanate of oman", "سلطنة عمان", "عمان")),
    "israel": ("il", "IL", "Israel", ("isr", "state of israel", "ישראל", "מדינת ישראל")),
    "south-africa": ("za", "ZA", "South Africa", ("zaf", "rsa", "republic of south africa", "suid-afrika")),
    "indonesia": ("id", "ID", "Indonesia", ("idn", "republik indonesia")),
    "china": ("cn", "CN", "China", ("chn", "prc", "people's republic of china", "中国", "中华人民共和国")),
    "malaysia": ("my", "MY", "Malaysia", ("mys", "persekutuan malaysia")),
    "thailand": ("th", "TH", "Thailand", ("tha", "kingdom of thailand", "ประเทศไทย", "ไทย")),
    "vietnam": ("vn", "VN", "Vietnam", ("vnm", "viet nam", "việt nam", "socialist republic of vietnam")),
    "philippines": ("ph", "PH", "Philippines", ("phl", "pilipinas", "republic of the philippines")),
    "pakistan": ("pk", "PK", "Pakistan", ("pak", "islamic republic of pakistan", "پاکستان")),
    "bangladesh": ("bd", "BD", "Bangladesh", ("bgd", "people's republic of bangladesh", "বাংলাদেশ")),
    "sri-lanka": ("lk", "LK", "Sri Lanka", ("lka", "democratic socialist republic of sri lanka", "ceylon", "ශ්‍රී ලංකාව", "இலங்கை")),
    "nepal": ("np", "NP", "Nepal", ("npl", "federal democratic republic of nepal", "नेपाल")),
    "jordan": ("jo", "JO", "Jordan", ("jor", "hashemite kingdom of jordan", "المملكة الأردنية الهاشمية", "الأردن")),
    "tunisia": ("tn", "TN", "Tunisia", ("tun", "republic of tunisia", "tunisie", "الجمهورية التونسية", "تونس")),
    "algeria": ("dz", "DZ", "Algeria", ("dza", "people's democratic republic of algeria", "algérie", "الجزائر", "الجمهورية الجزائرية الديمقراطية الشعبية")),
    "paraguay": ("py", "PY", "Paraguay", ("pry", "república del paraguay", "tetã paraguái")),
    "bolivia": ("bo", "BO", "Bolivia", ("bol", "estado plurinacional de bolivia", "plurinational state of bolivia")),
    "el-salvador": ("sv", "SV", "El Salvador", ("slv", "república de el salvador", "republic of el salvador")),
    "honduras": ("hn", "HN", "Honduras", ("hnd", "república de honduras", "republic of honduras")),
    "jamaica": ("jm", "JM", "Jamaica", ("jam",)),
    "trinidad-and-tobago": ("tt", "TT", "Trinidad and Tobago", ("tto", "trinidad", "tobago", "republic of trinidad and tobago")),
    "egypt": ("eg", "EG", "Egypt", ("egy", "arab republic of egypt", "misr", "مصر", "جمهورية مصر العربية")),
    "nigeria": ("ng", "NG", "Nigeria", ("nga", "federal republic of nigeria")),
    "kenya": ("ke", "KE", "Kenya", ("ken", "republic of kenya", "jamhuri ya kenya")),
    "morocco": ("ma", "MA", "Morocco", ("mar", "kingdom of morocco", "maroc", "royaume du maroc", "المغرب", "المملكة المغربية")),
    "ghana": ("gh", "GH", "Ghana", ("gha", "republic of ghana")),
    "peru": ("pe", "PE", "Peru", ("per", "perú", "republica del peru", "república del perú")),
    "uruguay": ("uy", "UY", "Uruguay", ("ury", "república oriental del uruguay", "republica oriental del uruguay")),
    "ecuador": ("ec", "EC", "Ecuador", ("ecu", "república del ecuador", "republica del ecuador")),
    "panama": ("pa", "PA", "Panama", ("pan", "panamá", "república de panamá", "republica de panama")),
    "dominican-republic": ("do", "DO", "Dominican Republic", ("dom", "república dominicana", "republica dominicana", "rd")),
    "guatemala": ("gt", "GT", "Guatemala", ("gtm", "república de guatemala", "republica de guatemala")),
    "kazakhstan": ("kz", "KZ", "Kazakhstan", ("kaz", "qazaqstan", "казахстан", "қазақстан")),
    "georgia": ("ge", "GE", "Georgia", ("geo", "sakartvelo", "საქართველო")),
    "armenia": ("am", "AM", "Armenia", ("arm", "hayastan", "հայաստան")),
    "azerbaijan": ("az", "AZ", "Azerbaijan", ("aze", "azerbaycan", "azərbaycan")),
    "uzbekistan": ("uz", "UZ", "Uzbekistan", ("uzb", "ozbekiston", "oʻzbekiston", "ўзбекистон")),
    "russia": ("ru", "RU", "Russia", ("rus", "russian federation", "россия", "российская федерация")),
    "tanzania": ("tz", "TZ", "Tanzania", ("tza", "united republic of tanzania", "jamhuri ya muungano wa tanzania")),
    "uganda": ("ug", "UG", "Uganda", ("uga", "republic of uganda", "jamhuri ya uganda")),
    "rwanda": ("rw", "RW", "Rwanda", ("rwa", "republic of rwanda", "repubulika y'u rwanda", "république du rwanda")),
    "ethiopia": ("et", "ET", "Ethiopia", ("eth", "federal democratic republic of ethiopia", "ኢትዮጵያ")),
    "mauritius": ("mu", "MU", "Mauritius", ("mus", "republic of mauritius", "maurice", "république de maurice")),
    "botswana": ("bw", "BW", "Botswana", ("bwa", "republic of botswana", "lefatshe la botswana")),
    "montenegro": ("me", "ME", "Montenegro", ("mne", "crna gora", "црна гора")),
    "north-macedonia": ("mk", "MK", "North Macedonia", ("mkd", "macedonia", "republic of north macedonia", "северна македонија", "maqedonia e veriut")),
    "albania": ("al", "AL", "Albania", ("alb", "shqiperia", "shqipëria", "republika e shqiperise")),
    "bosnia-and-herzegovina": ("ba", "BA", "Bosnia and Herzegovina", ("bih", "bosnia", "bosna i hercegovina", "босна и херцеговина")),
    "moldova": ("md", "MD", "Moldova", ("mda", "republic of moldova", "republica moldova")),
    "kosovo": ("xk", "XK", "Kosovo", ("xkx", "kosova", "kosovë", "republic of kosovo", "republika e kosovës")),
    "andorra": ("ad", "AD", "Andorra", ("and", "principat d'andorra", "principality of andorra")),
    "monaco": ("mc", "MC", "Monaco", ("mco", "principality of monaco", "principauté de monaco")),
    "san-marino": ("sm", "SM", "San Marino", ("smr", "repubblica di san marino", "republic of san marino")),
    "hong-kong": ("hk", "HK", "Hong Kong", ("hkg", "hong kong sar", "hong kong sar china", "hksar", "香港")),
    "taiwan": ("tw", "TW", "Taiwan", ("twn", "republic of china", "roc", "臺灣", "台灣", "中華民國")),
    "macao": ("mo", "MO", "Macao", ("mac", "macau", "macao sar", "macao sar china", "澳門", "澳门")),
    "cambodia": ("kh", "KH", "Cambodia", ("khm", "kingdom of cambodia", "កម្ពុជា")),
    "brunei": ("bn", "BN", "Brunei", ("brn", "brunei darussalam", "negara brunei darussalam")),
    "cote-divoire": ("ci", "CI", "Côte d’Ivoire", ("civ", "ivory coast", "cote d'ivoire", "côte d'ivoire", "republic of côte d'ivoire", "république de côte d'ivoire")),
    "senegal": ("sn", "SN", "Senegal", ("sen", "sénégal", "republic of senegal", "république du sénégal")),
    "cameroon": ("cm", "CM", "Cameroon", ("cmr", "cameroun", "republic of cameroon", "république du cameroun")),
    "zambia": ("zm", "ZM", "Zambia", ("zmb", "republic of zambia")),
    "zimbabwe": ("zw", "ZW", "Zimbabwe", ("zwe", "republic of zimbabwe")),
    "namibia": ("na", "NA", "Namibia", ("nam", "republic of namibia")),
    "bahamas": ("bs", "BS", "Bahamas", ("bhs", "the bahamas", "commonwealth of the bahamas")),
    "barbados": ("bb", "BB", "Barbados", ("brb", "bajan")),
    "belize": ("bz", "BZ", "Belize", ("blz", "british honduras")),
    "guyana": ("gy", "GY", "Guyana", ("guy", "co-operative republic of guyana")),
    "suriname": ("sr", "SR", "Suriname", ("sur", "republiek suriname", "republic of suriname")),
    "haiti": ("ht", "HT", "Haiti", ("hti", "haïti", "ayiti", "republic of haiti", "république d'haïti")),
    "kyrgyzstan": ("kg", "KG", "Kyrgyzstan", ("kgz", "kyrgyz republic", "kirghizia", "кыргызстан", "кыргыз республикасы", "киргизия")),
    "tajikistan": ("tj", "TJ", "Tajikistan", ("tjk", "republic of tajikistan", "тоҷикистон", "таджикистан", "ҷумҳурии тоҷикистон")),
    "maldives": ("mv", "MV", "Maldives", ("mdv", "republic of maldives", "ދިވެހިރާއްޖެ", "dhivehi raajje")),
    "bhutan": ("bt", "BT", "Bhutan", ("btn", "kingdom of bhutan", "druk yul", "འབྲུག་ཡུལ།")),
    "myanmar": ("mm", "MM", "Myanmar", ("mmr", "burma", "republic of the union of myanmar", "မြန်မာ")),
    "madagascar": ("mg", "MG", "Madagascar", ("mdg", "republic of madagascar", "repoblikan'i madagasikara", "madagasikara", "république de madagascar")),
    "dr-congo": ("cd", "CD", "DR Congo", ("cod", "democratic republic of the congo", "drc", "congo-kinshasa", "république démocratique du congo", "rdc")),
    "congo": ("cg", "CG", "Republic of the Congo", ("cog", "congo-brazzaville", "république du congo", "congo brazzaville")),
    "malawi": ("mw", "MW", "Malawi", ("mwi", "republic of malawi", "malaŵi", "dziko la malaŵi")),
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
