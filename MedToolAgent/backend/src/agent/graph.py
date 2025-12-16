from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from ..agent.state import AgentState
from ..agent.nodes import prompt_builder, llm_agent, safety_agent, recovery, refinement_agent

# Define the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("prompt_builder", prompt_builder)
workflow.add_node("llm_agent", llm_agent)
workflow.add_node("refinement_agent", refinement_agent)
workflow.add_node("safety_agent", safety_agent)
workflow.add_node("recovery", recovery)

# Define edges
workflow.add_edge(START, "prompt_builder")
workflow.add_edge("prompt_builder", "llm_agent")

# After LLM agent, go to refinement
workflow.add_edge("llm_agent", "refinement_agent")

# Conditional edge for refinement
def route_refinement(state: AgentState):
    if state.get("refinement_feedback"):
        return "llm_agent"
    return "safety_agent"

workflow.add_conditional_edges(
    "refinement_agent",
    route_refinement,
    {
        "llm_agent": "llm_agent",
        "safety_agent": "safety_agent"
    }
)

# Conditional edge for safety
def route_safety(state: AgentState):
    if state["is_valid"]:
        return END
    return "recovery"

workflow.add_conditional_edges(
    "safety_agent",
    route_safety,
    {
        END: END,
        "recovery": "recovery"
    }
)

workflow.add_edge("recovery", "llm_agent")

# Checkpointer
checkpointer = MemorySaver()

# Compile the graph
app = workflow.compile(checkpointer=checkpointer)
