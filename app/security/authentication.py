"""Authentication primitives."""

from dataclasses import dataclass, field

from fastapi import Header, HTTPException, status

from app.config import get_settings


@dataclass
class Principal:
    """Authenticated API caller."""

    key_id: str
    scopes: list[str] = field(default_factory=list)


def get_principal_from_api_key(api_key: str | None) -> Principal | None:
    """Resolve API key to principal if valid."""
    if not api_key:
        return None
    mapping = get_settings().parsed_api_keys()
    scopes = mapping.get(api_key)
    if scopes is None:
        return None
    return Principal(key_id=api_key[:8], scopes=scopes)


async def get_current_principal(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Principal:
    """FastAPI dependency returning authenticated principal."""
    principal = get_principal_from_api_key(x_api_key)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return principal
