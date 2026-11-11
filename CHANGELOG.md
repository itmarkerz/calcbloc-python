# Changelog

All notable changes to this package are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the package uses
[semantic versioning](https://semver.org/). Data-only updates (a new snapshot of the tables) bump the patch
version and give the data date.

## [0.1.0] - Unreleased

First release.

### Added

- `calcbloc.tables`: offline tax tables bundled with the package (data generated 2026-11-11): 29 countries,
  213 tables including every regional table, in the shape of the API's `/api/v1/tax-tables` response.
  `load()`, `list_countries()`, `years()`, `regions()`, `country_info()`, `manifest()`, `section()`,
  `bundled_files()` and `data_date()`.
- `tax_from_bands()`, `band_breakdown()` and `marginal_rate()`: band arithmetic on a `"bands"` section, done in
  `Decimal` (a convenience, not tax advice).
- `calcbloc.Client`: typed client for the CalcBloc API v1 (`countries`, `tax_tables` as JSON or CSV,
  `net_salary`, `employer_cost`, `compare`, `openapi`), standard library only, with typed errors
  (`CalcBlocError`, `AuthenticationError`, `RateLimitError`, `NetworkError`) and rate-limit headers.
  Works without a key (50 requests a day); the API key is read from `Client(api_key=...)` or
  `CALCBLOC_API_KEY`, and a 429 without a key says the free allowance is used up and links to a free key.
- Tests against official worked examples and rate schedules: Revenue (Ireland), GOV.UK, IRAS (Singapore),
  IRS (United States) and Inland Revenue (New Zealand).
- `scripts/sync_tables.py` to copy and validate the tables from the `calcbloc-data` repository.
