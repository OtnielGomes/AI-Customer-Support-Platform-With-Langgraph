"""Agent-run event routes."""

import uuid

from fastapi import APIRouter

from app.api.dependencies import PrincipalDep, SessionDep
from app.api.schemas import AgentEventListResponse
from app.security.authorization import authorize_route
from app.services import ticket_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}/events", response_model=AgentEventListResponse)
async def list_run_events(
    run_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> AgentEventListResponse:
    """Return ordered execution events for an agent run."""
    authorize_route(principal, ["read"])
    _run, events = await ticket_service.list_run_events(session, run_id)
    return AgentEventListResponse(
        items=[ticket_service.event_to_response(event) for event in events]
    )
