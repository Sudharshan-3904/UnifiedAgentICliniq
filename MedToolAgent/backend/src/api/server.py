from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..agent.graph import app as agent_app
from ..utils.logger import logger
import uuid

app = FastAPI(title="MedToolAgent API")

# Simple in-memory session store for conversation threads
# Format: { thread_id: [ {role: str, content: str}, ... ] }
SESSIONS: Dict[str, List[Dict[str, str]]] = {}


class QueryRequest(BaseModel):
    query: Optional[str] = None
    thread_id: Optional[str] = None
    reset: Optional[bool] = False


def _serialize_messages(msgs: List[Any]) -> List[Dict[str, str]]:
    """Serialize message objects (or dicts) to a simple list-of-dicts format."""
    serialized = []
    for m in msgs:
        if isinstance(m, dict):
            # Normalize known role names to canonical forms
            raw_role = m.get("role", "human").lower()
            if "system" in raw_role:
                role = "system"
            elif "ai" in raw_role or "assistant" in raw_role:
                role = "assistant"
            else:
                role = "human"
            serialized.append({"role": role, "content": m.get("content", "")})
            continue

        # Try to read attributes from message-like objects
        cls = getattr(m, "__class__", None)
        role_name = "system"
        if cls is not None:
            raw = cls.__name__.lower()
            if "system" in raw:
                role_name = "system"
            elif "ai" in raw or "assistant" in raw:
                role_name = "assistant"
            else:
                role_name = "human"
        content = getattr(m, "content", str(m))
        serialized.append({"role": role_name, "content": content})
    return serialized


@app.post("/run")
async def run_agent(request: QueryRequest):
    # Ensure there's a thread id
    thread_id = request.thread_id or str(uuid.uuid4())

    logger.info(f"Received query: {request.query} with thread_id: {thread_id} reset={request.reset}")

    # Reset session if requested
    if request.reset:
        if thread_id in SESSIONS:
            SESSIONS.pop(thread_id, None)
        return {"status": "reset", "thread_id": thread_id}

    # Ensure session exists
    if thread_id not in SESSIONS:
        SESSIONS[thread_id] = []

    # Append user message to session
    if request.query:
        SESSIONS[thread_id].append({"role": "human", "content": request.query})

    # Build initial state with the conversation history
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "user_query": request.query or "",
        "retry_count": 0,
        "messages": SESSIONS[thread_id]
    }

    try:
        # Run the graph
        result = agent_app.invoke(initial_state, config=config)

        # Persist returned messages back to session (if present)
        returned_msgs = result.get("messages", [])
        if returned_msgs:
            SESSIONS[thread_id] = _serialize_messages(returned_msgs)

        return {
            "status": "success",
            "thread_id": thread_id,
            "generation": result.get("generation"),
            "safety_report": result.get("safety_report"),
            "is_valid": result.get("is_valid"),
            "messages": SESSIONS.get(thread_id, [])
        }
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "healthy"}
