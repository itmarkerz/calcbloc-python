"""calcbloc: income tax brackets, social security rates and payroll tax tables, offline or via the CalcBloc API.

* :mod:`calcbloc.tables` loads the bundled official tax tables (no network).
* :func:`tax_from_bands` applies a band section to an amount (a convenience, not tax advice).
* :class:`Client` calls the CalcBloc API (https://calcbloc.com/developers) for the latest tables and for
  take-home pay, employer cost and salary comparisons.

Code: MIT licence. Data: CC BY 4.0, credit "Data by CalcBloc (calcbloc.com/data)".
"""

from . import tables
from ._version import __version__
from .bands import band_breakdown, marginal_rate, tax_from_bands
from .client import Client
from .errors import AuthenticationError, CalcBlocError, NetworkError, RateLimitError, TableNotFoundError
from .types import BandSlice, RateLimit

__all__ = [
    "__version__",
    "tables",
    "Client",
    "tax_from_bands",
    "band_breakdown",
    "marginal_rate",
    "CalcBlocError",
    "AuthenticationError",
    "RateLimitError",
    "NetworkError",
    "TableNotFoundError",
    "BandSlice",
    "RateLimit",
]
