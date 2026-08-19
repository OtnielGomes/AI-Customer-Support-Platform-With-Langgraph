"""Integration tests for ticket listing, HITL, traces, and analytics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.exceptions import register_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.escalations import router as escalations_router
from app.api.routes.health import router as health_router
from app.api.routes.portal import router as portal_router
from app.api.routes.runs import router as runs_router
from app.api.routes.tickets import router as tickets_router
from app.config import get_settings


class FakeGraph:
    """Graph double with ``astream`` and ``aget_state``."""

    def __init__(self) -> None:
        self.mode = "resolve"
        self.resume_payload: dict | None = None
        self.stream_calls = 0

    async def astream(self, payload, config=None, stream_mode=None):
        self.stream_calls += 1
        events = []
        if self.mode == "escalate":
            events = [
                {"supervisor": {"intent": "unknown", "confidence": 0.2}},
                {"escalation": {"needs_human": True}},
            ]
        elif self.mode == "resume":
            self.resume_payload = payload
            events = [
                {"escalation": {"draft_answer": "Human handled this."}},
                {"output_guardrails": {"draft_answer": "Human handled this."}},
            ]
        else:
            events = [
                {"supervisor": {"intent": "billing", "confidence": 0.95}},
                {
                    "billing": {
                        "draft_answer": "Invoice found.",
                        "tool_results": [{"tool": "get_invoice", "result": {"id": "INV-1001"}}],
                    }
                },
                {"resolution": {"needs_human": False, "draft_answer": "Invoice found."}},
            ]
        modes = stream_mode if isinstance(stream_mode, list) else [stream_mode or "updates"]
        for event in events:
            if "updates" in modes:
                yield ("updates", event) if isinstance(stream_mode, list) else event

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
    app.include_router(portal_router)
    app.include_router(tickets_router)
    app.include_router(escalations_router)
    app.include_router(runs_router)
    app.include_router(analytics_router)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.publish = AsyncMock(return_value=1)

    app.state.support_graph = fake_graph
    app.state.redis = mock_redis
    with TestClient(app) as test_client:
        test_client.redis = mock_redis  # type: ignore[attr-defined]
        yield test_client


def _ensure_customer(email: str, name: str = "Test User") -> None:
    """Insert a customer row when the portal no longer auto-creates accounts."""
    dsn = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM customers WHERE email = %s", (email,))
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO customers
                        (id, public_id, email, name, customer_tier, account_status)
                    VALUES (%s, %s, %s, %s, 'standard', 'active')
                    """,
                    (str(uuid4()), f"CUST-{uuid4().hex[:8].upper()}", email, name),
                )
        conn.commit()


def _create_ticket(client: TestClient, suffix: str) -> dict:
    email = f"user-{suffix}@example.com"
    _ensure_customer(email)
    response = client.post(
        "/tickets",
        headers=_auth_headers(),
        json={
            "customer_email": email,
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
    history = client.get(f"/tickets/{ticket_id}/messages", headers=_auth_headers())
    assert any(item["role"] == "system" for item in history.json()["items"])

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
    """Close should mark the ticket closed and persist a system notice."""
    created = _create_ticket(client, "close")
    client.post(
        f"/tickets/{created['id']}/takeover",
        headers=_auth_headers(),
        json={"agent": "console"},
    )
    closed = client.post(
        f"/tickets/{created['id']}/close",
        headers=_auth_headers(),
        json={"reason": "Duplicate"},
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "closed"
    assert body["assigned_agent"] is None
    assert "Closed by agent. Duplicate" in (body["resolution"] or "")
    history = client.get(f"/tickets/{created['id']}/messages", headers=_auth_headers())
    assert history.status_code == 200
    roles = [item["role"] for item in history.json()["items"]]
    assert "system" in roles
    published = [
        call.args[1]
        for call in client.redis.publish.await_args_list
        if call.args
    ]
    assert any("ticket_status" in payload for payload in published)


def test_confirm_ticket_persists_system_notice(client: TestClient) -> None:
    """Customer confirm should resolve the ticket and publish status."""
    created = _create_ticket(client, "confirm")
    confirmed = client.post(
        f"/tickets/{created['id']}/confirm",
        headers=_auth_headers(),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "resolved"
    history = client.get(f"/tickets/{created['id']}/messages", headers=_auth_headers())
    assert history.status_code == 200
    roles = [item["role"] for item in history.json()["items"]]
    assert "system" in roles
    published = [
        call.args[1]
        for call in client.redis.publish.await_args_list
        if call.args
    ]
    assert any("ticket_status" in payload for payload in published)


def test_ticket_events_emits_heartbeat(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /tickets/{id}/events should stream an SSE heartbeat then close."""

    async def _one_heartbeat(*_args, **_kwargs):
        yield {"event": "heartbeat", "data": {"ts": "t"}}

    monkeypatch.setattr(
        "app.api.routes.tickets.subscribe_ticket_events",
        _one_heartbeat,
    )
    created = _create_ticket(client, "events")
    with client.stream(
        "GET",
        f"/tickets/{created['id']}/events",
        headers=_auth_headers(),
    ) as response:
        assert response.status_code == 200, response.text
        collected = "".join(response.iter_text())
    assert "heartbeat" in collected


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


def test_create_ticket_unknown_email_is_rejected(client: TestClient) -> None:
    """Unknown emails must not create orphan customers."""
    response = client.post(
        "/tickets",
        headers=_auth_headers(),
        json={
            "customer_email": "nobody-unknown@example.com",
            "customer_name": "Ghost",
            "subject": "Help",
            "description": "I need help",
        },
    )
    assert response.status_code == 404


def test_portal_create_conversation_returns_ticket(client: TestClient) -> None:
    """Opening a portal chat must serialize without lazy-loading ORM relations."""
    email = "portal-chat@example.com"
    _ensure_customer(email, "Portal Chat")
    response = client.post(
        "/portal/conversations",
        headers={**_auth_headers(), "X-Customer-Email": email},
        json={"order_id": None},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["customer_email"] == email
    assert body["customer_name"] == "Portal Chat"
    assert body["status"] == "open"
    assert body["subject"] == "Support chat"


def test_portal_session_valid_and_invalid(client: TestClient) -> None:
    """Portal login validates against existing customers only."""
    email = "portal-session@example.com"
    _ensure_customer(email, "Portal User")
    ok = client.post("/portal/session", headers=_auth_headers(), json={"email": email})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["email"] == email
    assert body["name"] == "Portal User"

    missing = client.post(
        "/portal/session",
        headers=_auth_headers(),
        json={"email": "missing-user@example.com"},
    )
    assert missing.status_code == 404


def test_cross_customer_cannot_read_ticket(client: TestClient) -> None:
    """Customer B must not read customer A's ticket even with a valid API key."""
    created = _create_ticket(client, "own-a")
    other = "user-own-b@example.com"
    _ensure_customer(other, "Other User")
    hidden = client.get(
        f"/tickets/{created['id']}",
        headers={**_auth_headers(), "X-Customer-Email": other},
    )
    assert hidden.status_code == 404


def test_post_message_sse_persists_history(client: TestClient, fake_graph: FakeGraph) -> None:
    """POST /messages streams SSE and stores customer + assistant turns."""
    fake_graph.mode = "resolve"
    created = _create_ticket(client, "sse")
    ticket_id = created["id"]
    with client.stream(
        "POST",
        f"/tickets/{ticket_id}/messages",
        headers=_auth_headers(),
        json={"content": "Where is invoice INV-1001?", "role": "customer"},
    ) as response:
        assert response.status_code == 200, response.text
        payload = "".join(response.iter_text())
    assert "done" in payload
    assert "Invoice found" in payload

    history = client.get(f"/tickets/{ticket_id}/messages", headers=_auth_headers())
    assert history.status_code == 200, history.text
    roles = [item["role"] for item in history.json()["items"]]
    assert "customer" in roles
    assert "assistant" in roles


def test_customer_message_after_takeover_skips_graph(
    client: TestClient, fake_graph: FakeGraph
) -> None:
    """After a human takes over, a customer reply must not invoke the AI."""
    created = _create_ticket(client, "human-owned")
    takeover = client.post(
        f"/tickets/{created['id']}/takeover",
        headers=_auth_headers(),
        json={"agent": "console"},
    )
    assert takeover.status_code == 200, takeover.text
    fake_graph.stream_calls = 0
    with client.stream(
        "POST",
        f"/tickets/{created['id']}/messages",
        headers=_auth_headers(),
        json={"content": "Ainda estou aguardando.", "role": "customer"},
    ) as response:
        assert response.status_code == 200, response.text
        payload = "".join(response.iter_text())
    assert fake_graph.stream_calls == 0
    assert "Invoice found" not in payload
    history = client.get(f"/tickets/{created['id']}/messages", headers=_auth_headers())
    roles = [item["role"] for item in history.json()["items"]]
    assert "customer" in roles
    assert "assistant" not in roles


def test_takeover_assigns_agent(client: TestClient) -> None:
    """Console takeover stores assigned_agent on the ticket."""
    created = _create_ticket(client, "take")
    response = client.post(
        f"/tickets/{created['id']}/takeover",
        headers=_auth_headers(),
        json={"agent": "console"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["assigned_agent"] == "console"
    published = [call.args[1] for call in client.redis.publish.await_args_list]
    assert any("ticket_status" in payload for payload in published)


def test_portal_me_returns_profile(client: TestClient) -> None:
    """GET /portal/me requires a known customer email."""
    email = "portal-me@example.com"
    _ensure_customer(email, "Portal Me")
    missing = client.get("/portal/me", headers=_auth_headers())
    assert missing.status_code == 401
    ok = client.get("/portal/me", headers={**_auth_headers(), "X-Customer-Email": email})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["email"] == email
    assert body["name"] == "Portal Me"
    assert "orders" in body
    assert "conversations" in body

