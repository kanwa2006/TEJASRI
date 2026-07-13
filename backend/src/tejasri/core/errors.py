"""Application error hierarchy.

Domain and application layers raise these; the API layer maps them to
HTTP responses in one place so business code never imports FastAPI.
"""


class TejasriError(Exception):
    """Base class for all application errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(TejasriError):
    """A requested entity does not exist (or is invisible to this tenant)."""


class ConflictError(TejasriError):
    """State conflict, e.g. optimistic-version mismatch on a care plan."""


class AuthenticationError(TejasriError):
    """Missing or invalid credentials."""


class AuthorizationError(TejasriError):
    """Authenticated but not permitted."""


class ValidationError(TejasriError):
    """Input is structurally valid but semantically unacceptable."""


class ExternalServiceError(TejasriError):
    """An upstream dependency (LLM provider, AWS) failed after retries."""
