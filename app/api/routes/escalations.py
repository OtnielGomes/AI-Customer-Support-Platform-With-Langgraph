"""Human-escalation queue routes."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import PrincipalDep, SessionDep
from app.api.schemas import TicketListResponse
from app.security.authorization import authorize_route
from app.services import ticket_service

router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get("", response_model=TicketListResponse)
async def list_escalations(
    session: SessionDep,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketListResponse:
    """Return the human-support queue (escalated tickets, oldest first)."""
    authorize_route(principal, ["read"])
    return await ticket_service.list_escalations(session, limit=limit, offset=offset)
