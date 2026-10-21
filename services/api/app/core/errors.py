from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base exception for expected domain failures."""


class NotFound(DomainError):
    """Raised when a requested resource does not exist."""


class Conflict(DomainError):
    """Raised when an operation conflicts with existing state."""


class ValidationError(DomainError):
    """Raised when domain input fails validation."""


class Forbidden(DomainError):
    """Raised when an operation is not allowed for the caller."""


DOMAIN_ERROR_STATUS_CODES = {
    NotFound: 404,
    Conflict: 409,
    ValidationError: 422,
    Forbidden: 403,
}


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = DOMAIN_ERROR_STATUS_CODES.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})
