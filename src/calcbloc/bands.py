"""Convenience arithmetic on progressive band sections (``kind: "bands"``).

These helpers apply a band table to an amount the way progressive tax brackets work: each slice of income
is taxed at the rate of the band it falls in. They do **not** know a country's rules about allowances,
credits, deductions, tapers, surcharges, rounding or filing status, so the result is only the band
arithmetic for the amount you pass in. Check each section's ``basis`` and ``note`` to see what the amount
should be (for example "Taxable income above the Personal Allowance, per year").

This is a convenience for developers, not tax advice. For a full take-home pay figure use the API's
``net-salary`` endpoint, which runs the same engines as the calculators on calcbloc.com.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .types import BandSlice

__all__ = ["tax_from_bands", "band_breakdown", "marginal_rate"]

Number = Union[int, float, Decimal]
BandSource = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]

_Band = Tuple[Optional[str], Decimal, Optional[Decimal], Decimal]


def _dec(x: Any, what: str) -> Decimal:
    if isinstance(x, bool) or not isinstance(x, (int, float, Decimal)):
        raise ValueError(f"{what} must be a number, got {x!r}")
    # str() keeps the decimal the data was written with (0.035, not 0.035000000000000003).
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _bands(source: BandSource) -> List[_Band]:
    if isinstance(source, Mapping):
        kind = source.get("kind")
        if kind is not None and kind != "bands":
            sid = source.get("id", "?")
            raise ValueError(f'Section "{sid}" has kind "{kind}"; only "bands" sections can be applied to an amount.')
        rows: Iterable[Mapping[str, Any]] = source.get("rows") or []
    else:
        rows = source
    out: List[_Band] = []
    for i, row in enumerate(rows):
        if "from" not in row or "rate" not in row:
            raise ValueError(f"Row {i} is not a band (needs 'from' and 'rate'): {dict(row)!r}")
        lower = _dec(row["from"], f"Row {i} 'from'")
        upper = None if row.get("to") is None else _dec(row["to"], f"Row {i} 'to'")
        rate = _dec(row["rate"], f"Row {i} 'rate'")
        if upper is not None and upper < lower:
            raise ValueError(f"Row {i} has 'to' ({upper}) below 'from' ({lower}).")
        label = row.get("label")
        out.append((label if isinstance(label, str) else None, lower, upper, rate))
    if not out:
        raise ValueError("The section has no bands.")
    return sorted(out, key=lambda b: b[1])


def _slices(source: BandSource, income: Number, above: Number) -> List[Tuple[_Band, Decimal]]:
    inc = _dec(income, "income")
    base = _dec(above, "above")
    if base < 0:
        raise ValueError("above must not be negative.")
    if inc <= 0:
        return [(b, Decimal(0)) for b in _bands(source)]
    start, end = base, base + inc
    result = []
    for band in _bands(source):
        _, lower, upper, _ = band
        top = end if upper is None else min(end, upper)
        result.append((band, max(Decimal(0), top - max(start, lower))))
    return result


def band_breakdown(section: BandSource, income: Number, *, above: Number = 0) -> List[BandSlice]:
    """Split ``income`` across the bands of ``section`` and return one :class:`BandSlice` per band.

    Args:
        section: A section with ``kind == "bands"`` from a tax table (or a list of its band rows).
        income: The amount to apply the bands to, in the table's currency and period (usually per year).
            Zero or a negative amount gives zero in every band.
        above: Income already counted below this amount, which uses up the lower bands first. Use it to
            stack one kind of income on another; UK dividends, for example, sit on top of other taxable income.

    Returns:
        A list in band order; bands the income does not reach have ``amount == 0``.
    """
    out = []
    for (label, lower, upper, rate), amount in _slices(section, income, above):
        out.append(
            BandSlice(
                label=label,
                lower=float(lower),
                upper=None if upper is None else float(upper),
                rate=float(rate),
                amount=float(amount),
                tax=float(amount * rate),
            )
        )
    return out


def tax_from_bands(section: BandSource, income: Number, *, above: Number = 0) -> float:
    """Apply a progressive band section to ``income`` and return the total.

    Each slice of ``income`` is multiplied by the rate of the band it falls in, and the products are added
    up. The arithmetic is done in :class:`decimal.Decimal` from the figures as written in the data, then
    returned as a float without rounding (round to the currency's minor unit yourself).

    This is a convenience, not tax advice: it applies the bands and nothing else. Allowances, credits,
    tapers, surcharges and the authority's own rounding rules are not applied. Read the section's ``basis``
    to see which amount the bands apply to.

    Args:
        section: A section with ``kind == "bands"`` (or a list of its band rows).
        income: The amount the bands apply to (for example taxable income per year).
        above: Income already counted below ``income`` (see :func:`band_breakdown`).

    Returns:
        The total, as a float.

    Raises:
        ValueError: If the section is not a band section or a row has no numeric ``from``/``rate``.

    Example:
        >>> from calcbloc import tables, tax_from_bands
        >>> uk = tables.load("uk", "2026-27")
        >>> tax_from_bands(tables.section(uk, "income-tax-england"), 35_000 - 12_570)
        4486.0
    """
    total = sum((amount * band[3] for band, amount in _slices(section, income, above)), Decimal(0))
    return float(total)


def marginal_rate(section: BandSource, income: Number) -> float:
    """Return the rate of the band that ``income`` falls in.

    A band covers amounts above its ``from`` up to and including its ``to`` (the usual "over X but not over Y"
    wording); amounts at or below the first band's lower edge get the first band's rate. Useful on its own
    for tables where one rate applies to the whole amount, such as New Zealand's ESCT rate thresholds.

    Args:
        section: A section with ``kind == "bands"`` (or a list of its band rows).
        income: The amount to look up.
    """
    x = _dec(income, "income")
    bands = _bands(section)
    chosen = bands[0][3]
    for _, lower, upper, rate in bands:
        if x <= lower:
            break
        chosen = rate
        if upper is None or x <= upper:
            break
    return float(chosen)
