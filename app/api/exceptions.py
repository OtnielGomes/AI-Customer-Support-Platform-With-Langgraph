"""Domain exceptions and HTTP mapping."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.security.authorization import AuthorizationError


class DomainError(Exception):
    """Base domain error."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TicketNotFoundError(DomainError):
    """Ticket not found."""

    def __init__(self, ticket_id: str) -> None:
        super().__init__(f"Ticket not found: {ticket_id}", status_code=404)


class CustomerNotFoundError(DomainError):
    """Customer email is unknown or missing."""

    def __init__(self, email: str) -> None:
        if email == "missing":
            super().__init__("Customer email is required", status_code=401)
            return
        super().__init__(f"Customer not found: {email}", status_code=404)


class TicketOwnershipError(DomainError):
    """Authenticated customer does not own the ticket."""

    def __init__(self, ticket_id: str) -> None:
        super().__init__(f"Ticket not found: {ticket_id}", status_code=404)


class RunNotFoundError(DomainError):
    """Agent run not found."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Agent run not found: {run_id}", status_code=404)


class TicketConflictError(DomainError):
    """Ticket is not in a valid state for the requested action."""

    def __init__(self, ticket_id: str, message: str) -> None:
        super().__init__(f"{message}: {ticket_id}", status_code=409)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        _request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )
