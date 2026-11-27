# Changelog

All notable changes to this package are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the package uses
[semantic versioning](https://semver.org/). Data-only updates (a new snapshot of the tables) bump the patch
version and give the data date.

## [0.2.0] - Unreleased

For CalcBloc API 1.10.

### Added (API 1.10)

- `Client.tax_treaties()` for `GET /api/v1/tax-treaties`: the double taxation treaties stored for a country
  (India), with the maximum withholding rates on dividends, interest, royalties and fees for technical
  services, their articles and wording, the relief methods, dates and the official source. Typed as
  `TaxTreatiesResponse` (`TaxTreaty`, `TreatyWithholding`).
- `verification` in `CalculationResponse` (net salary and employer cost) and in each calculation endpoint of
  `countries()` (`Verification`: `"official-example"`, `"law-text"` or `None`). With a value, the first note
  says how the calculation was checked and links the official sources.
- Take-home pay and employer cost for Denmark (`dk`: `municipality`, `church`, `atp_hours`), Estonia (`ee`:
  `funded_pension`, `pension_age`) and Poland (`pl`: `accident_rate_pct`, `commuter`) work through
  `net_salary()` and `employer_cost()` as they are; `compare()` accepts `dk`, `ee` and `pl`.
- Bundled tables: 217 countries (422 tables), synced from calcbloc-data 2026-11-27; Belgium stays pending.
  Short codes, ISO codes and names for the 84 new countries in `_country_codes.py`.
- Tests use real API 1.10 responses as fixtures (`tests/fixtures/api-1.10/`).

### Changed (API 1.10)

- Schema test: band rates above 100% are also accepted for Laos's excise on fuel-powered cars by engine
  capacity (up to 220%).

For CalcBloc API 1.9.

### Added (API 1.8 and 1.9)

- `Client.supplemental_withholding()` and `Client.equity_tax()` (API 1.8), and `Client.cross_border_equity()`,
  `Client.facts()`, `Client.tax_calendar()`, `Client.tariffs()`, `Client.trade_agreements()` and
  `Client.import_duty()` (API 1.9). They return the API's JSON as a dict.
- Bundled tables: 133 countries (338 tables), synced from calcbloc-data 2026-11-26; Belgium stays pending.
  Short codes, ISO codes and names for all of them in `_country_codes.py`.

### Changed (API 1.8 and 1.9)

- Schema test: band rates above 100% are accepted for an ad valorem vehicle registration tax (Hong Kong's
  first registration tax, 115% and 132%).

For CalcBloc API 1.7:

### Changed

- The `RateLimitError` message without a key no longer states fixed limits. It quotes the daily limit the API
  reported in `X-RateLimit-Limit` when one has been seen ("The free daily allowance without a key (300
  requests a day) is used up."), says "The free per-minute allowance without a key is used up for this
  minute." for the per-minute limit, and otherwise gives no number. It still links to a free email-only key
  and says how to set it (`Client(api_key="...")` or `CALCBLOC_API_KEY`). Docstrings point to
  https://calcbloc.com/developers#limits instead of quoting numbers.
- README: keyless limits are now 300 requests a day and 20 a minute per IP address; countries can be given by
  short code (`nz`, `de`, `uk`), with the older keys still accepted; US `filing_status` values are `single`,
  `mfj` and `hoh`; `region` is required for take-home pay in the US and Canada and for employer cost in the
  US, Australia and Canada; equity compensation, bonus and supplemental withholding and cross-border
  withholding are not supported yet.

### Added

- Countries can be given by short code (`nz`; `gb` or `uk` for the UK), ISO code (`NZ`) or English name
  (`New Zealand`), case-insensitively, as well as by the existing code (`new-zealand`): in `tables.load()`,
  `country_info()`, `years()` and `regions()`, and in `Client.tax_tables()`, which maps them to the code
  before building the request path. The table mirrors the API's own (`calcbloc/_country_codes.py`).
- Types: `short_code` and `iso_code` on `CountryInfo`, `labels` and `aliases` on `CountryParameter`, and the
  `coverage` object (`Coverage`) on `CountriesResponse`.

## [0.1.0] - Unreleased

First release.

### Added

- `calcbloc.tables`: offline tax tables bundled with the package (data generated 2026-11-13): 41 countries,
  246 tables including every regional table, in the shape of the API's `/api/v1/tax-tables` response.
  `load()`, `list_countries()`, `years()`, `regions()`, `country_info()`, `manifest()`, `section()`,
  `bundled_files()` and `data_date()`.
- `tax_from_bands()`, `band_breakdown()` and `marginal_rate()`: band arithmetic on a `"bands"` section, done in
  `Decimal` (a convenience, not tax advice).
- `calcbloc.Client`: typed client for the CalcBloc API v1 (`countries`, `tax_tables` as JSON or CSV,
  `net_salary`, `employer_cost`, `compare`, `openapi`), standard library only, with typed errors
  (`CalcBlocError`, `AuthenticationError`, `RateLimitError`, `NetworkError`) and rate-limit headers.
  Works without a key, within the keyless allowance; the API key is read from `Client(api_key=...)` or
  `CALCBLOC_API_KEY`, and a 429 without a key says the free allowance is used up and links to a free key.
- Tests against official worked examples and rate schedules: Revenue (Ireland), GOV.UK, IRAS (Singapore),
  IRS (United States) and Inland Revenue (New Zealand).
- `scripts/sync_tables.py` to copy and validate the tables from the `calcbloc-data` repository.
