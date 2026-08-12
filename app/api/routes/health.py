"""Health check routes."""

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import RedisDep, SessionDep
from app.api.schemas import HealthResponse
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(session: SessionDep, redis: RedisDep) -> HealthResponse:
    """Readiness check for database, Redis, and provider configuration."""
    db_status = "ok"
    redis_status = "ok"

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        pong = await redis.ping()
        if not pong:
            redis_status = "error"
    except Exception:
        redis_status = "error"

    settings = get_settings()
    openai_ok = bool(settings.openai_api_key)
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        openai_configured=openai_ok,
    )


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}
