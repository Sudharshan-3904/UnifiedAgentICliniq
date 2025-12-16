"""Test conversational multi-turn chat and session persistence with tool-calling."""
from fastapi.testclient import TestClient

from backend.src.api.server import app, SESSIONS


def test_conversational_session_persistence():
    client = TestClient(app)
    thread_id = "test_thread_1"

    # Ensure clean start
    SESSIONS.pop(thread_id, None)

    # First message (external LLM may be unavailable in tests; we assert session behavior instead)
    r1 = client.post("/run", json={"query": "Hello, please introduce yourself.", "thread_id": thread_id})
    # It's OK if the backend LLM call failed (500). Regardless, the user message should be stored in the session.
    assert r1.status_code in (200, 500)

    # Ensure session contains the first user message
    assert thread_id in SESSIONS
    assert any(m.get("content", "") == "Hello, please introduce yourself." for m in SESSIONS[thread_id])

    # Second message in same thread
    r2 = client.post("/run", json={"query": "Can you summarize your previous response?", "thread_id": thread_id})
    assert r2.status_code in (200, 500)

    # Conversation should have at least two user messages stored in the session
    msgs = SESSIONS.get(thread_id, [])
    human_msgs = [m for m in msgs if not m.get("role", "").startswith("ai")]
    assert len(human_msgs) >= 2

    # Reset and ensure session removed
    r_reset = client.post("/run", json={"thread_id": thread_id, "reset": True})
    assert r_reset.status_code == 200
    assert r_reset.json()["status"] == "reset"
    assert thread_id not in SESSIONS


def test_rag_tool_missing_query_monkeypatch(monkeypatch):
    """Simulate LLM returning a rag_clinical_data tool call with no args and ensure we return an informative error without calling the tool."""
    from backend.src.agent import nodes

    class FakeResp:
        def __init__(self, content):
            self.content = content

    # Make llm.invoke return a message that requests the rag tool without arguments
    monkeypatch.setattr(nodes, "llm", nodes.llm)
    monkeypatch.setattr(nodes.llm, "invoke", lambda messages: FakeResp("TOOL_CALL: rag_clinical_data()"))

    # Prepare a simple state
    state = {
        "user_query": "Please find guidelines",
        "messages": [],
    }

    out = nodes.llm_agent(state)

    # We should get a generation that is an error string telling about missing query
    gen = out.get("generation")
    assert gen is not None
    assert gen.startswith("Error: rag_clinical_data requires a query") or "rag_clinical_data requires a query" in gen
