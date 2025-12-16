from typing import TypedDict, Annotated, List, Optional, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    user_query: str
    prompt: Optional[str]
    generation: Optional[str]
    safety_report: Optional[str]
    is_valid: bool
    retry_count: int
    refinement_count: int
    refinement_feedback: Optional[str]
    final_output: Optional[str]
    tool_used: Optional[str]
