"""Analytics API routes."""

from fastapi import APIRouter

from app.api.dependencies import PrincipalDep, RedisDep, SessionDep
from app.api.schemas import AnalyticsOverviewResponse, AnalyticsToolsResponse
from app.security.authorization import authorize_route
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    session: SessionDep,
    redis: RedisDep,
    principal: PrincipalDep,
) -> AnalyticsOverviewResponse:
    """Ticket volume, status mix, escalation rate, and daily counts."""
    authorize_route(principal, ["read"])
    return await analytics_service.get_overview(session, redis)


@router.get("/tools", response_model=AnalyticsToolsResponse)
async def analytics_tools(
    session: SessionDep,
    redis: RedisDep,
    principal: PrincipalDep,
) -> AnalyticsToolsResponse:
    """Per-tool call counts, error rate, and latency."""
    authorize_route(principal, ["read"])
    return await analytics_service.get_tool_analytics(session, redis)
