"""Exceptions raised by the CalcBloc client and the offline tables.

Every API error response has the shape ``{"error": {"code", "message", "docs"}, "attribution": {...}}``.
:class:`CalcBlocError` carries those fields, plus the HTTP status. The offline loader raises
:class:`TableNotFoundError`, which uses the same codes as the API (``unsupported_country``,
``unsupported_year``, ``unsupported_region``), so code that handles one can handle the other.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

__all__ = [
    "CalcBlocError",
    "AuthenticationError",
    "RateLimitError",
    "NetworkError",
    "TableNotFoundError",
]


class CalcBlocError(Exception):
    """Base class for every error raised by this package.

    Attributes:
        code: Machine-readable error code, e.g. ``"unsupported_country"`` or ``"rate_limited"``.
        message: Human-readable explanation from the API (or from this package).
        status: HTTP status code, or ``None`` when no HTTP response was received.
        docs: Link to the relevant documentation, when the API sent one.
        body: The decoded JSON error body, when there was one.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "error",
        status: Optional[int] = None,
        docs: Optional[str] = None,
        body: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.docs = docs
        self.body = body

    def __str__(self) -> str:
        prefix = f"[{self.status} {self.code}]" if self.status is not None else f"[{self.code}]"
        return f"{prefix} {self.message}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, status={self.status!r}, message={self.message!r})"


class AuthenticationError(CalcBlocError):
    """401: the endpoint needs an API key (``api_key_required``) or the key is not valid (``invalid_key``)."""


class RateLimitError(CalcBlocError):
    """429 ``rate_limited``: the per-minute or daily limit was reached.

    Attributes:
        retry_after: Seconds to wait before retrying (from the ``Retry-After`` header), if sent.
        limit: Requests allowed per day for this key or address (``X-RateLimit-Limit``), if sent.
        remaining: Requests left today (``X-RateLimit-Remaining``), if sent.
        reset: Seconds until the daily window resets at UTC midnight (``X-RateLimit-Reset``), if sent.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "rate_limited",
        status: Optional[int] = 429,
        docs: Optional[str] = None,
        body: Optional[Mapping[str, Any]] = None,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        reset: Optional[int] = None,
    ) -> None:
        super().__init__(message, code=code, status=status, docs=docs, body=body)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset = reset


class NetworkError(CalcBlocError):
    """The request did not get an HTTP response (DNS failure, refused connection, timeout)."""


class TableNotFoundError(CalcBlocError, LookupError):
    """No bundled table matches the requested country, year or region (offline loader)."""
