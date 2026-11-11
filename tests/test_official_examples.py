"""The bundled tables against worked examples and computed figures published by tax authorities.

Each expected value below is printed in the cited official document; none was computed by us. The tests apply
the bundled band sections with :func:`calcbloc.tax_from_bands`, :func:`calcbloc.band_breakdown` or
:func:`calcbloc.marginal_rate` and must reproduce the published figure exactly (to the cent).

The examples are tied to a tax year. When a year is no longer bundled, its test is skipped with a reminder to
add the next year's example.
"""

from __future__ import annotations

import pytest

from calcbloc import band_breakdown, marginal_rate, tables, tax_from_bands


def table(country: str, year: str, region: str | None = None):
    if year not in tables.years(country):
        pytest.skip(f"{country} {year} is no longer bundled: replace this test with the next year's official example")
    return tables.load(country, year, region)


# ---------------------------------------------------------------------------------------------------------------
# Ireland: Revenue, "Calculating your USC" (2026), Examples 1-4.
# https://www.revenue.ie/en/jobs-and-pensions/usc/calculating-usc.aspx
# ---------------------------------------------------------------------------------------------------------------
REVENUE_USC_URL = "https://www.revenue.ie/en/jobs-and-pensions/usc/calculating-usc.aspx"


@pytest.mark.parametrize(
    "who, income, per_band, total",
    [
        ("Example 1, Jacob", 25_000, [60.06, 259.76, 0, 0], 319.82),
        ("Example 2, Sadhbh", 50_000, [60.06, 333.76, 639.00, 0], 1_032.82),
        ("Example 4, Cian (75, income over the 60,000 limit for reduced rates)", 75_000, [60.06, 333.76, 1_240.32, 396.48], 2_030.62),
    ],
)
def test_ireland_usc_revenue_examples(who: str, income: int, per_band: list, total: float) -> None:
    usc = tables.section(table("ireland", "2026"), "usc")
    assert [round(s.tax, 2) for s in band_breakdown(usc, income)] == per_band, who
    assert round(tax_from_bands(usc, income), 2) == total, f"{who}: {REVENUE_USC_URL}"


def test_ireland_usc_reduced_rate_revenue_example_3() -> None:
    # Example 3, Donnchadh: full medical card, income 50,000: 60.06 + 759.76 (2% on 37,988) = 819.82.
    reduced = tables.section(table("ireland", "2026"), "usc-reduced")
    assert [round(s.tax, 2) for s in band_breakdown(reduced, 50_000)] == [60.06, 759.76]
    assert round(tax_from_bands(reduced, 50_000), 2) == 819.82, REVENUE_USC_URL


# ---------------------------------------------------------------------------------------------------------------
# United Kingdom: GOV.UK, "Tax on dividends", "How much tax you pay on dividends", Example (2026 to 2027).
# https://www.gov.uk/tax-on-dividends
# Wages 29,570 + dividends 3,000; after the 12,570 Personal Allowance, taxable income 20,000 is in the basic rate
# band: 20% on 17,000 of wages, no tax on 500 of dividends (dividend allowance), 10.75% on 2,500 of dividends.
# ---------------------------------------------------------------------------------------------------------------
def test_uk_dividends_govuk_example_2026_27() -> None:
    uk = table("uk", "2026-27")
    allowance = next(r["value"] for r in tables.section(uk, "personal-allowance")["rows"] if r["label"] == "Personal Allowance")
    assert allowance == 12_570

    wages_taxable = 29_570 - allowance
    assert wages_taxable == 17_000
    wages = band_breakdown(tables.section(uk, "income-tax-england"), wages_taxable)
    assert (wages[0].label, wages[0].rate, wages[0].amount) == ("Basic rate", 0.2, 17_000)
    assert sum(s.amount for s in wages[1:]) == 0

    # The 500 allowance uses up band space too, so the taxed dividends start at 17,500.
    dividends = band_breakdown(tables.section(uk, "dividends"), 3_000 - 500, above=wages_taxable + 500)
    assert (dividends[0].rate, dividends[0].amount) == (0.1075, 2_500)
    assert sum(s.amount for s in dividends[1:]) == 0
    # The page lists the rates and amounts; the products are 3,400 and 268.75.
    assert tax_from_bands(tables.section(uk, "income-tax-england"), wages_taxable) == 3_400
    assert tax_from_bands(tables.section(uk, "dividends"), 2_500, above=17_500) == 268.75


# ---------------------------------------------------------------------------------------------------------------
# Singapore: IRAS, "Individual Income Tax rates", resident tax rates from YA 2024 onwards, "Gross Tax Payable"
# column (cumulative tax on the first $X of chargeable income). The bundled 2026 table is YA 2027.
# https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/tax-residency-and-tax-rates/individual-income-tax-rates
# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "chargeable_income, gross_tax",
    [
        (20_000, 0),
        (30_000, 200),
        (40_000, 550),
        (80_000, 3_350),
        (120_000, 7_950),
        (160_000, 13_950),
        (200_000, 21_150),
        (240_000, 28_750),
        (280_000, 36_550),
        (320_000, 44_550),
        (500_000, 84_150),
        (1_000_000, 199_150),
    ],
)
def test_singapore_iras_gross_tax_payable(chargeable_income: int, gross_tax: int) -> None:
    sg = tables.section(table("singapore", "2026"), "income-tax")
    assert tax_from_bands(sg, chargeable_income) == gross_tax


# ---------------------------------------------------------------------------------------------------------------
# United States: IRS Rev. Proc. 2025-32, section 4.01, 2026 tax rate schedules ("The Tax Is: $X plus Y% of the
# excess over $Z"). Table 1 married filing jointly, Table 2 heads of households, Table 3 unmarried individuals.
# https://www.irs.gov/pub/irs-drop/rp-25-32.pdf
# ---------------------------------------------------------------------------------------------------------------
REV_PROC_2025_32 = {
    # section id: [(taxable income at the top of a bracket, tax printed for the next bracket's base)]
    "federal-income-tax-mfj": [(24_800, 2_480), (100_800, 11_600), (211_400, 35_932), (403_550, 82_048), (512_450, 116_896), (768_700, 206_583.50)],
    "federal-income-tax-hoh": [(17_700, 1_770), (67_450, 7_740), (105_700, 16_155), (201_750, 39_207), (256_200, 56_631), (640_600, 191_171)],
    "federal-income-tax-single": [(12_400, 1_240), (50_400, 5_800), (105_700, 17_966), (201_775, 41_024), (256_225, 58_448), (640_600, 192_979.25)],
}


@pytest.mark.parametrize("section_id", sorted(REV_PROC_2025_32))
def test_us_federal_rate_schedules_rev_proc_2025_32(section_id: str) -> None:
    s = tables.section(table("us", "2026"), section_id)
    for income, tax in REV_PROC_2025_32[section_id]:
        assert tax_from_bands(s, income) == tax, f"{section_id} at ${income:,}"


def test_us_single_between_brackets_follows_the_schedule() -> None:
    # Table 3: over $50,400 but not over $105,700 -> $5,800 plus 22% of the excess over $50,400.
    s = tables.section(table("us", "2026"), "federal-income-tax-single")
    assert tax_from_bands(s, 75_000) == pytest.approx(5_800 + 0.22 * (75_000 - 50_400), abs=0.005)
    assert marginal_rate(s, 75_000) == 0.22


# ---------------------------------------------------------------------------------------------------------------
# New Zealand: Inland Revenue, IR335 Employer's guide (September 2026), page 26, "Option 1 - calculating ESCT":
# Josh's salary plus employer contributions is $80,000, so his ESCT rate is 30.0%; Bree's is $53,000, so 17.5%.
# https://www.ird.govt.nz/-/media/project/ir/home/documents/forms-and-guides/ir300---ir399/ir335/ir335.pdf
# ---------------------------------------------------------------------------------------------------------------
def test_new_zealand_esct_rate_ir335_examples() -> None:
    esct = tables.section(table("new-zealand", "2026-27"), "esct")
    assert marginal_rate(esct, 80_000) == 0.30  # Josh
    assert marginal_rate(esct, 53_000) == 0.175  # Bree
    # Threshold wording in the same table: "$18,721 - $64,200 17.5%", "$64,201 - $93,720 30.0%".
    assert marginal_rate(esct, 64_200) == 0.175
    assert marginal_rate(esct, 64_201) == 0.30
