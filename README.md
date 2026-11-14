# calcbloc: income tax brackets, social security rates and tax tables for Python

[![PyPI](https://img.shields.io/pypi/v/calcbloc.svg)](https://pypi.org/project/calcbloc/)
[![Python versions](https://img.shields.io/pypi/pyversions/calcbloc.svg)](https://pypi.org/project/calcbloc/)
[![Tests](https://github.com/itmarkerz/calcbloc-python/actions/workflows/tests.yml/badge.svg)](https://github.com/itmarkerz/calcbloc-python/actions/workflows/tests.yml)
[![Code licence: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](https://github.com/itmarkerz/calcbloc-python/blob/main/LICENSE)
[![Data licence: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-green.svg)](https://calcbloc.com/data?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss)

Official 2026 tax tables in Python: income tax brackets, social security and payroll contribution rates,
thresholds and allowances for the US, UK, Canada, Australia, much of Europe and more. Every figure carries
its official source and the date it was checked.

CalcBloc is a product of [itmarkerz technologies](https://itmarkerz.co.in/?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss).

`calcbloc` gives you two ways in:

* **Offline tables.** The CalcBloc open dataset ([calcbloc.com/data](https://calcbloc.com/data?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss)) ships inside the
  package. Load a country's tax tables with no network, no API key and no rate limit.
* **A typed API client.** `calcbloc.Client` wraps the [CalcBloc tax tables API](https://calcbloc.com/developers?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss):
  the latest tables (JSON or CSV), plus take-home pay, employer cost and two-country salary comparisons
  computed by the same engines as the calculators on calcbloc.com.

Pure Python, Python 3.9+, no runtime dependencies (the client uses `urllib` from the standard library),
fully typed (`py.typed`).

## Install

```bash
pip install calcbloc
```

> **Not yet published.** The package is not on PyPI yet. Until it is, install from a clone:
> `pip install .` in the repository root.

## Three examples

All output below is real, produced from the data bundled with this version.

### 1. US federal income tax brackets for 2026

```python
from calcbloc import tables, tax_from_bands

us = tables.load("us", "2026")
single = tables.section(us, "federal-income-tax-single")
print(single["title"], "|", single["basis"])
for band in single["rows"]:
    span = f"${band['from']:,} to ${band['to']:,}" if band["to"] is not None else f"over ${band['from']:,}"
    print(f"{band['rate']:>4.0%}  {span}")

print(tax_from_bands(single, 75_000))   # federal income tax on $75,000 of taxable income
print(single["source"]["url"])
```

```text
Federal income tax brackets: Single | Taxable income, per year
 10%  $0 to $12,400
 12%  $12,400 to $50,400
 22%  $50,400 to $105,700
 24%  $105,700 to $201,775
 32%  $201,775 to $256,225
 35%  $256,225 to $640,600
 37%  over $640,600
11212.0
https://www.irs.gov/pub/irs-drop/rp-25-32.pdf
```

The result matches the IRS rate schedule in Rev. Proc. 2025-32: $5,800 plus 22% of the excess over $50,400.

### 2. Ireland's Universal Social Charge, band by band

```python
from calcbloc import band_breakdown, tables, tax_from_bands

usc = tables.section(tables.load("ireland", "2026"), "usc")
for band in band_breakdown(usc, 50_000):
    print(f"{band.rate:.1%} on EUR {band.amount:,.2f} = EUR {band.tax:,.2f}")
print(round(tax_from_bands(usc, 50_000), 2))
```

```text
0.5% on EUR 12,012.00 = EUR 60.06
2.0% on EUR 16,688.00 = EUR 333.76
3.0% on EUR 21,300.00 = EUR 639.00
8.0% on EUR 0.00 = EUR 0.00
1032.82
```

This is Revenue's own worked example (Sadhbh, EUR 50,000) from
[Calculating your USC](https://www.revenue.ie/en/jobs-and-pensions/usc/calculating-usc.aspx), to the cent.

### 3. German social security rates, with their sources

Every table also has a flat `rows` list (the same rows as the CSV download), each with its own tax year,
effective dates, official source URL and retrieval date:

```python
from calcbloc import tables

de = tables.load("germany")
for row in de["rows"]:
    if row["group"] == "employee" and row["unit"] == "rate":
        print(f"{row['rate']:6.2%}  {row['section']}: {row['label']}")

pension = next(r for r in de["rows"] if r["section_id"] == "pension-insurance")
print(pension["source_url"], pension["retrieved_at"])
```

```text
18.60%  Pension insurance (Rentenversicherung): Contribution rate (employee and employer each pay half)
 2.60%  Unemployment insurance (Arbeitslosenversicherung): Contribution rate (employee and employer each pay half)
14.60%  Health insurance (Krankenversicherung): General contribution rate (employee and employer each pay half)
 2.90%  Health insurance (Krankenversicherung): Average additional contribution rate (Zusatzbeitrag; each fund sets its own, shared equally)
 3.60%  Long-term care insurance (Pflegeversicherung): Contribution rate (employee and employer each pay half; see Saxony below)
 0.60%  Long-term care insurance (Pflegeversicherung): Surcharge for childless members (employee only)
 0.25%  Long-term care insurance (Pflegeversicherung): Reduction per child (employee share)
 1.00%  Long-term care insurance (Pflegeversicherung): Saxony: extra employee share (employer pays correspondingly less)
https://www.gesetze-im-internet.de/rvbeitrsbek_2026/BJNR1230A0025.html 2026-10-17
```

## Offline tables

```python
from calcbloc import tables

tables.list_countries()              # ['us', 'uk', 'australia', ...] from the bundled manifest
tables.years("uk")                   # ['2026-27', '2025-26'], current year first
tables.regions("canada")             # [{'code': 'ab', 'name': 'Alberta', 'slug': 'alberta'}, ...]
tables.load("uk")                    # current tax year
tables.load("uk", "2025-26", region="scotland")
tables.load("us", 2026, region="california")   # region by code or slug
tables.manifest()                    # countries, years, regions, page and API URLs, sources
tables.data_date()                   # when the bundled data was generated
```

A table has the same shape as the API's `/api/v1/tax-tables/{country}/{year}` response:

* `sections`: titled groups such as income tax bands, employee and employer contributions. `kind` is `"bands"`
  (rows with `from`, `to`, `rate`) or `"values"` (rows with `label`, `value`, `unit`). Each section has a
  `source` (title, URL, retrieval date) and usually a `basis` saying what the figures apply to.
* `rows`: every band and value as a flat record with `source_url`, `retrieved_at`, `effective_from`,
  `effective_to` and `status` (`verified`, `under_review` or `not_applicable`).
* `sources`, `effectiveFrom`, `effectiveTo`, `status`, `underReview`, `pageUrl` and `attribution`.

Rates are decimals (`0.2` is 20%). Money is in the country's currency, per year unless a label says
otherwise. A regional table (US state, Canadian province, Scotland, a Swiss canton...) holds the regional
figures only. Unknown countries, years or regions raise `calcbloc.TableNotFoundError`, with the same `code`
the API uses (`unsupported_country`, `unsupported_year`, `unsupported_region`).

### Applying brackets: `tax_from_bands`

`tax_from_bands(section, income, above=0)` applies a `"bands"` section progressively: each slice of income is
taxed at the rate of its band. `band_breakdown()` returns the slices, and `marginal_rate()` returns the rate of
the band an amount falls in. Use `above=` to stack one income on another (UK dividends sit on top of other
taxable income).

These helpers are a **convenience, not tax advice**. They apply the bands to the amount you pass and nothing
else: no allowances, credits, tapers, surcharges, filing rules or the authority's rounding. Check the section's
`basis` (for example "Taxable income above the Personal Allowance, per year") to know which amount to pass.
For a complete take-home pay figure, use the API's `net-salary` endpoint.

## The API client

```python
from calcbloc import Client

client = Client()                                   # no key needed: 50 requests a day
table = client.tax_tables("canada", "latest", region="on")
csv_text = client.tax_tables("uk", "2026-27", format="csv")
countries = client.countries()                      # endpoints and parameters per country

client = Client(api_key="your-key")                 # free key: 5,000 a day (or set CALCBLOC_API_KEY)
pay = client.net_salary("uk", 45_000, region="scotland", pension_pct=5)
cost = client.employer_cost("us", 85_000, region="tx", health_per_month=600)
both = client.compare("uk", "ireland", 60_000, currency="GBP")
```

Country-specific parameters are passed as keyword arguments by their API names (`filing_status`,
`pension_pct`, `student_loan`...); `client.countries()` and the
[OpenAPI file](https://calcbloc.com/api/openapi.json) list them, with allowed values and defaults. Unknown
parameters are refused by the API, so typos never pass silently.

Errors raise typed exceptions built from the API's `{"error": {"code", "message", "docs"}}` body:

```python
from calcbloc import AuthenticationError, CalcBlocError, Client, RateLimitError

try:
    Client(api_key="your-key").net_salary("norway", 600_000)
except RateLimitError as e:
    print("retry in", e.retry_after, "seconds")
except AuthenticationError as e:          # invalid_key (401): the key is wrong or revoked
    print(e.code)
except CalcBlocError as e:
    print(e.status, e.code, e.message)    # 400 unsupported_country: Norway has tax tables only
```

Countries marked `tables_only` in `client.countries()` have tax tables but no calculation engine yet; the
calculation endpoints answer them with `400 unsupported_country`. `client.last_rate_limit` holds the
`X-RateLimit-*` headers of the last response. Pass `transport=` to `Client` to plug in your own HTTP layer
(proxy, retries, caching or tests).

### Free use and API keys

* **Offline tables need no key and no network.** `calcbloc.tables` and `tax_from_bands` read the data
  bundled in the package.
* **API calls work without a key** for 50 requests a day and 5 a minute per IP address, on every endpoint.
* **Add a free API key for 5,000 requests a day** (60 a minute). Get one instantly at
  [calcbloc.com/developers/keys](https://calcbloc.com/developers/keys?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) (enter your email address; the key is shown once).
* **Set it** with `Client(api_key="cb_...")`, or in the `CALCBLOC_API_KEY` environment variable, which
  `Client()` reads by default. The client sends it in the `X-API-Key` header; keys in the URL are refused by
  the API because URLs end up in logs.

| Access | Per day | Per minute |
|---|---|---|
| No key (per IP address) | 50 | 5 |
| Free key | 5,000 | 60 |

When the free allowance without a key is used up, the client raises `RateLimitError` with a message that
says so, links to the keys page and shows how to set the key. With a key, the message gives that key's limit.
For higher volumes or use without attribution, see
[calcbloc.com/developers](https://calcbloc.com/developers?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss).

### Offline or API?

| | Offline tables | API |
|---|---|---|
| Network, key, limits | None | HTTPS; 50 requests a day without a key, 5,000 with a free key |
| Tax tables | Snapshot dated `tables.data_date()` | Always the latest published figures |
| CSV download | No (JSON) | `format="csv"` |
| Take-home pay, employer cost, compare | No (only `tax_from_bands` on single sections) | Yes |

Upgrade the package to refresh the bundled snapshot, or call the API when you need today's figures.

## Data licence and attribution

Copyright (c) 2026 itmarkerz technologies. CalcBloc is a product of itmarkerz technologies.

* **Code**: MIT licence (see [LICENSE](https://github.com/itmarkerz/calcbloc-python/blob/main/LICENSE)).
* **Data** (the bundled tables and everything the API returns): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
  (see [DATA_LICENSE.md](https://github.com/itmarkerz/calcbloc-python/blob/main/DATA_LICENSE.md)).
  Show this credit, with a link, wherever you display the figures:

  > Data by CalcBloc ([calcbloc.com/data](https://calcbloc.com/data))

  The canonical, most recent version of each table is its country page on calcbloc.com.

Each table carries an `attribution` block and a `pageUrl` for the matching tax tables page on calcbloc.com.
API use is also covered by the [API terms](https://calcbloc.com/developers/terms?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss).

## Country coverage

<!-- coverage:start -->

Bundled data generated 2026-11-14: **41 countries**, 246 tables (204 of them regional). This table is generated from `manifest.json` by `scripts/sync_tables.py`.

| Country | Code | Current tax year | Years bundled | Regional tables | Last checked | Tax tables page |
|---|---|---|---|---|---|---|
| [United States](https://calcbloc.com/us/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `us` | 2026 | 2026 | 51 | 2026-11-13 | [United States tax tables](https://calcbloc.com/us/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [United Kingdom](https://calcbloc.com/uk/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `uk` | 2026-27 | 2026-27, 2025-26 | 2 | 2026-11-13 | [United Kingdom tax tables](https://calcbloc.com/uk/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Australia](https://calcbloc.com/australia/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `australia` | 2026-27 | 2026-27 | - | 2026-11-13 | [Australia tax tables](https://calcbloc.com/australia/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [New Zealand](https://calcbloc.com/new-zealand/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `new-zealand` | 2026-27 | 2026-27 | - | 2026-11-13 | [New Zealand tax tables](https://calcbloc.com/new-zealand/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Canada](https://calcbloc.com/canada/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `canada` | 2026 | 2026 | 13 | 2026-11-13 | [Canada tax tables](https://calcbloc.com/canada/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Ireland](https://calcbloc.com/ireland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `ireland` | 2026 | 2026 | - | 2026-11-13 | [Ireland tax tables](https://calcbloc.com/ireland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [India](https://calcbloc.com/india/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `india` | 2026-27 | 2026-27 | - | 2026-11-14 | [India tax tables](https://calcbloc.com/india/tax-tables/2026-27?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Germany](https://calcbloc.com/germany/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `germany` | 2026 | 2026 | - | 2026-11-13 | [Germany tax tables](https://calcbloc.com/germany/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Spain](https://calcbloc.com/spain/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `spain` | 2026 | 2026 | 21 | 2026-11-13 | [Spain tax tables](https://calcbloc.com/spain/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Netherlands](https://calcbloc.com/netherlands/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `netherlands` | 2026 | 2026 | - | 2026-11-13 | [Netherlands tax tables](https://calcbloc.com/netherlands/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [France](https://calcbloc.com/france/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `france` | 2026 | 2026 | - | 2026-11-13 | [France tax tables](https://calcbloc.com/france/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Singapore](https://calcbloc.com/singapore/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `singapore` | 2026 | 2026 | - | 2026-11-14 | [Singapore tax tables](https://calcbloc.com/singapore/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [United Arab Emirates](https://calcbloc.com/uae/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `uae` | 2026 | 2026 | - | 2026-11-14 | [United Arab Emirates tax tables](https://calcbloc.com/uae/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Italy](https://calcbloc.com/italy/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `italy` | 2026 | 2026 | 21 | 2026-11-13 | [Italy tax tables](https://calcbloc.com/italy/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Portugal](https://calcbloc.com/portugal/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `portugal` | 2026 | 2026 | 2 | 2026-11-14 | [Portugal tax tables](https://calcbloc.com/portugal/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Switzerland](https://calcbloc.com/switzerland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `switzerland` | 2026 | 2026 | 26 | 2026-11-14 | [Switzerland tax tables](https://calcbloc.com/switzerland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Denmark](https://calcbloc.com/denmark/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `denmark` | 2026 | 2026 | 5 | 2026-11-09 | [Denmark tax tables](https://calcbloc.com/denmark/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Sweden](https://calcbloc.com/sweden/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `sweden` | 2026 | 2026 | 21 | 2026-11-10 | [Sweden tax tables](https://calcbloc.com/sweden/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Austria](https://calcbloc.com/austria/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `austria` | 2026 | 2026 | - | 2026-11-14 | [Austria tax tables](https://calcbloc.com/austria/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Poland](https://calcbloc.com/poland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `poland` | 2026 | 2026 | - | 2026-11-10 | [Poland tax tables](https://calcbloc.com/poland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Luxembourg](https://calcbloc.com/luxembourg/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `luxembourg` | 2026 | 2026 | - | 2026-11-14 | [Luxembourg tax tables](https://calcbloc.com/luxembourg/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Czechia](https://calcbloc.com/czechia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `czechia` | 2026 | 2026 | - | 2026-11-11 | [Czechia tax tables](https://calcbloc.com/czechia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Norway](https://calcbloc.com/norway/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `norway` | 2026 | 2026 | - | 2026-11-11 | [Norway tax tables](https://calcbloc.com/norway/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Finland](https://calcbloc.com/finland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `finland` | 2026 | 2026 | 19 | 2026-11-11 | [Finland tax tables](https://calcbloc.com/finland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Slovenia](https://calcbloc.com/slovenia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `slovenia` | 2026 | 2026 | - | 2026-11-11 | [Slovenia tax tables](https://calcbloc.com/slovenia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Romania](https://calcbloc.com/romania/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `romania` | 2026 | 2026 | - | 2026-11-11 | [Romania tax tables](https://calcbloc.com/romania/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Hungary](https://calcbloc.com/hungary/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `hungary` | 2026 | 2026 | - | 2026-11-11 | [Hungary tax tables](https://calcbloc.com/hungary/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Slovakia](https://calcbloc.com/slovakia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `slovakia` | 2026 | 2026 | - | 2026-11-11 | [Slovakia tax tables](https://calcbloc.com/slovakia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Greece](https://calcbloc.com/greece/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `greece` | 2026 | 2026 | - | 2026-11-11 | [Greece tax tables](https://calcbloc.com/greece/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Latvia](https://calcbloc.com/latvia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `latvia` | 2026 | 2026 | - | 2026-11-11 | [Latvia tax tables](https://calcbloc.com/latvia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Croatia](https://calcbloc.com/croatia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `croatia` | 2026 | 2026 | 21 | 2026-11-11 | [Croatia tax tables](https://calcbloc.com/croatia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Estonia](https://calcbloc.com/estonia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `estonia` | 2026 | 2026 | - | 2026-11-11 | [Estonia tax tables](https://calcbloc.com/estonia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Bulgaria](https://calcbloc.com/bulgaria/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `bulgaria` | 2026 | 2026 | - | 2026-11-11 | [Bulgaria tax tables](https://calcbloc.com/bulgaria/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Lithuania](https://calcbloc.com/lithuania/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `lithuania` | 2026 | 2026 | - | 2026-11-11 | [Lithuania tax tables](https://calcbloc.com/lithuania/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Malta](https://calcbloc.com/malta/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `malta` | 2026 | 2026 | - | 2026-11-11 | [Malta tax tables](https://calcbloc.com/malta/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Cyprus](https://calcbloc.com/cyprus/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `cyprus` | 2026 | 2026 | - | 2026-11-11 | [Cyprus tax tables](https://calcbloc.com/cyprus/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Iceland](https://calcbloc.com/iceland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `iceland` | 2026 | 2026 | - | 2026-11-11 | [Iceland tax tables](https://calcbloc.com/iceland/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Ukraine](https://calcbloc.com/ukraine/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `ukraine` | 2026 | 2026 | - | 2026-11-12 | [Ukraine tax tables](https://calcbloc.com/ukraine/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Liechtenstein](https://calcbloc.com/liechtenstein/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `liechtenstein` | 2026 | 2026 | - | 2026-11-13 | [Liechtenstein tax tables](https://calcbloc.com/liechtenstein/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Serbia](https://calcbloc.com/serbia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `serbia` | 2026 | 2026 | - | 2026-11-13 | [Serbia tax tables](https://calcbloc.com/serbia/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |
| [Türkiye](https://calcbloc.com/turkey/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) | `turkey` | 2026 | 2026 | - | 2026-11-13 | [Türkiye tax tables](https://calcbloc.com/turkey/tax-tables/2026?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) |

Coming later (tables under review, not yet published): Belgium.

<!-- coverage:end -->

## How the data is tested

The test suite checks every bundled table (each row has a source URL and a retrieval date, bands are well
formed) and reproduces figures published by tax authorities with `tax_from_bands`:

* Ireland: Revenue, [Calculating your USC](https://www.revenue.ie/en/jobs-and-pensions/usc/calculating-usc.aspx), Examples 1 to 4 (2026).
* United Kingdom: GOV.UK, [Tax on dividends](https://www.gov.uk/tax-on-dividends), worked example (2026 to 2027).
* Singapore: IRAS, [Individual income tax rates](https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/tax-residency-and-tax-rates/individual-income-tax-rates), gross tax payable column (YA 2024 onwards).
* United States: IRS, [Rev. Proc. 2025-32](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf), 2026 rate schedules for single, married filing jointly and head of household.
* New Zealand: Inland Revenue, [IR335 Employer's guide](https://www.ird.govt.nz/-/media/project/ir/home/documents/forms-and-guides/ir300---ir399/ir335/ir335.pdf), ESCT rate examples.

```bash
pip install -e ".[test]"
pytest
```

## Updating the bundled data

The tables come from the [calcbloc-data](https://github.com/itmarkerz/calcbloc-data) repository. With it
checked out next to this one:

```bash
python scripts/sync_tables.py                 # copies ../calcbloc-data/tables, validates, refreshes this README
python scripts/sync_tables.py --source PATH   # or set CALCBLOC_DATA_TABLES
python scripts/sync_tables.py --check         # exit 1 if the bundled data is out of date
```

Tables are stored gzip-compressed inside the package (the JSON is unchanged once decompressed), so every
country, year and region fits in under 1 MB.

## Links

* Developer documentation: [calcbloc.com/developers](https://calcbloc.com/developers?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss)
* Open data and downloads: [calcbloc.com/data](https://calcbloc.com/data?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss)
* OpenAPI 3.1 description: [calcbloc.com/api/openapi.json](https://calcbloc.com/api/openapi.json)
* Calculators: [calcbloc.com](https://calcbloc.com/?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss)
* Changelog: [CHANGELOG.md](https://github.com/itmarkerz/calcbloc-python/blob/main/CHANGELOG.md)

## About

[CalcBloc](https://calcbloc.com/?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) is built and maintained by [itmarkerz technologies](https://itmarkerz.co.in/?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss),
a web and mobile app development company in Kerala, India. The open data behind this package is at
[calcbloc.com/data](https://calcbloc.com/data?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss) and the API documentation at
[calcbloc.com/developers](https://calcbloc.com/developers?utm_source=calcbloc-python&utm_medium=readme&utm_campaign=itmarkerz-oss). The other CalcBloc packages (JavaScript, PHP, R,
Google Sheets, the MCP server and the dataset itself) are in the
[itmarkerz GitHub organization](https://github.com/itmarkerz).
