"""Integration tests for ticket listing, HITL, traces, and analytics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.exceptions import register_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.escalations import router as escalations_router
from app.api.routes.health import router as health_router
from app.api.routes.runs import router as runs_router
from app.api.routes.tickets import router as tickets_router
from app.config import get_settings


class FakeGraph:
    """Graph double with ``astream`` and ``aget_state``."""

    def __init__(self) -> None:
        self.mode = "resolve"
        self.resume_payload: dict | None = None

    async def astream(self, payload, config=None, stream_mode=None):
        if self.mode == "escalate":
            yield {"supervisor": {"intent": "unknown", "confidence": 0.2}}
            yield {"escalation": {"needs_human": True}}
            return
        if self.mode == "resume":
            self.resume_payload = payload
            yield {"escalation": {"draft_answer": "Human handled this."}}
            yield {"output_guardrails": {"draft_answer": "Human handled this."}}
            return
        yield {"supervisor": {"intent": "billing", "confidence": 0.95}}
        yield {
            "billing": {
                "draft_answer": "Invoice found.",
                "tool_results": [{"tool": "get_invoice", "result": {"id": "INV-1001"}}],
            }
        }
        yield {"resolution": {"needs_human": False, "draft_answer": "Invoice found."}}

    async def aget_state(self, config):
        if self.mode == "escalate":
            return SimpleNamespace(
                values={
                    "intent": "unknown",
                    "confidence": 0.2,
                    "draft_answer": "Needs a specialist.",
                    "needs_human": True,
                    "tool_results": [],
                    "retrieved_context": [],
                },
                interrupts=(
                    SimpleNamespace(
                        value={
                            "reason": "low confidence",
                            "draft_answer": "Needs a specialist.",
                        }
                    ),
                ),
                tasks=(),
            )
        answer = "Human handled this." if self.mode == "resume" else "Invoice found."
        return SimpleNamespace(
            values={
                "intent": "billing" if self.mode != "resume" else "unknown",
                "confidence": 0.95 if self.mode != "resume" else 0.2,
                "draft_answer": answer,
                "needs_human": False,
                "tool_results": (
                    [{"tool": "get_invoice", "result": {"id": "INV-1001"}}]
                    if self.mode == "resolve"
                    else []
                ),
                "retrieved_context": [],
            },
            interrupts=(),
            tasks=(),
        )


def _auth_headers() -> dict[str, str]:
    mapping = get_settings().parsed_api_keys()
    key = next(iter(mapping))
    return {"X-API-Key": key}


@pytest.fixture
def fake_graph() -> FakeGraph:
    """Shared fake graph for a test."""
    return FakeGraph()


@pytest.fixture
def client(fake_graph: FakeGraph) -> TestClient:
    """Create test client with mocked graph and real DB session."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(tickets_router)
    app.include_router(escalations_router)
    app.include_router(runs_router)
    app.include_router(analytics_router)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)

    app.state.support_graph = fake_graph
    app.state.redis = mock_redis
    return TestClient(app)


def _create_ticket(client: TestClient, suffix: str) -> dict:
    response = client.post(
        "/tickets",
        headers=_auth_headers(),
        json={
            "customer_email": f"user-{suffix}@example.com",
            "customer_name": "Test User",
            "subject": f"Help {suffix}",
            "description": "I have a question about invoice INV-1001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_tickets_after_create(client: TestClient) -> None:
    """Created tickets should appear in the paginated list."""
    created = _create_ticket(client, "list")
    listed = client.get("/tickets", headers=_auth_headers(), params={"q": "Help list"})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    ids = [item["id"] for item in body["items"]]
    assert created["id"] in ids
    assert body["total"] >= 1


def test_resolve_persists_run_and_events(client: TestClient, fake_graph: FakeGraph) -> None:
    """Resolve should persist a completed run with tool events."""
    fake_graph.mode = "resolve"
    created = _create_ticket(client, "resolve")
    ticket_id = created["id"]
    resolved = client.post(
        f"/tickets/{ticket_id}/resolve",
        headers=_auth_headers(),
        json={"messages": [{"role": "user", "content": "Where is invoice INV-1001?"}]},
    )
    assert resolved.status_code == 200, resolved.text
    payload = resolved.json()
    assert payload["awaiting_human"] is False
    assert payload["run_id"]
    assert payload["answer"] == "Invoice found."

    detail = client.get(f"/tickets/{ticket_id}", headers=_auth_headers())
    assert detail.status_code == 200
    assert detail.json()["status"] == "in_progress"

    confirmed = client.post(
        f"/tickets/{ticket_id}/confirm",
        headers=_auth_headers(),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "resolved"

    runs = client.get(f"/tickets/{ticket_id}/runs", headers=_auth_headers())
    assert runs.status_code == 200
    run_items = runs.json()["items"]
    assert run_items
    run_id = run_items[0]["id"]

    events = client.get(f"/runs/{run_id}/events", headers=_auth_headers())
    assert events.status_code == 200
    names = [event["name"] for event in events.json()["items"]]
    assert "supervisor" in names
    assert "get_invoice" in names


def test_escalation_reply_cycle(client: TestClient, fake_graph: FakeGraph) -> None:
    """Escalate then resume with a human reply."""
    fake_graph.mode = "escalate"
    created = _create_ticket(client, "hitl")
    ticket_id = created["id"]
    resolved = client.post(
        f"/tickets/{ticket_id}/resolve",
        headers=_auth_headers(),
        json={"messages": [{"role": "user", "content": "Something confusing"}]},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["awaiting_human"] is True
    assert resolved.json()["escalated"] is True

    queued = client.get("/escalations", headers=_auth_headers())
    assert queued.status_code == 200
    assert any(item["id"] == ticket_id for item in queued.json()["items"])

    fake_graph.mode = "resume"
    reply = client.post(
        f"/tickets/{ticket_id}/escalation/reply",
        headers=_auth_headers(),
        json={"answer": "Human handled this.", "agent": "agent-1"},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["awaiting_human"] is False
    assert reply.json()["answer"] == "Human handled this."

    detail = client.get(f"/tickets/{ticket_id}", headers=_auth_headers())
    assert detail.json()["status"] == "in_progress"


def test_close_ticket(client: TestClient) -> None:
    """Close should mark the ticket closed."""
    created = _create_ticket(client, "close")
    closed = client.post(
        f"/tickets/{created['id']}/close",
        headers=_auth_headers(),
        json={"reason": "Duplicate"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert "Closed by agent. Duplicate" in (closed.json()["resolution"] or "")


def test_analytics_overview_and_tools(client: TestClient) -> None:
    """Analytics endpoints should return the documented shape."""
    overview = client.get("/analytics/overview", headers=_auth_headers())
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert "total_tickets" in body
    assert "by_status" in body
    assert "escalation_rate" in body

    tools = client.get("/analytics/tools", headers=_auth_headers())
    assert tools.status_code == 200, tools.text
    assert "items" in tools.json()


def test_list_tickets_requires_auth(client: TestClient) -> None:
    """Listing tickets without an API key should fail."""
    response = client.get("/tickets")
    assert response.status_code == 401
