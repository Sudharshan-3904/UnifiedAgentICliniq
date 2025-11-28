import os
from typing import TypedDict
from dotenv import load_dotenv
import json 
import logging
import traceback

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client


load_dotenv()

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "simple-agent-orchestration")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral")
LLM_TEMP = float(os.getenv("LLM_TEMPERATURE", "0.2"))
TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")

os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
os.environ["LANGCHAIN_PROJECT"] = PROJECT_NAME
os.environ["LANGCHAIN_TRACING_V2"] = TRACING_V2


class AgentState(TypedDict):
    query: str
    reasoning: str
    action_result: str


llm = ChatOllama(
    model=MODEL_NAME,
    temperature=LLM_TEMP,
    streaming=False,
)


def reason_node(state: AgentState) -> AgentState:
    """Use the local Ollama model to decide what to do next."""
    prompt = f"""
You are a reasoning agent. The user asked:

{state['query']}

Think step-by-step and propose an appropriate action to take.
"""
    response = llm.invoke(prompt)
    return {"reasoning": response.content}


def act_node(state: AgentState) -> AgentState:
    """Simulated action stage."""
    reasoning = state["reasoning"]
    action_output = f"Action executed based on reasoning: {reasoning[:50]}..."
    return {"action_result": action_output}


workflow = StateGraph(AgentState)

workflow.add_node("reason", reason_node)
workflow.add_node("act", act_node)

workflow.set_entry_point("reason")
workflow.add_edge("reason", "act")
workflow.add_edge("act", END)


memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n--- Agent Workflow Starting ---\n")
    query = input("Enter query to the model: ")

    initial_state = {"query": query}

    thread_id = "demo-thread-1"

    try:
        result = app.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )

        print("\n--- Final Result ---")
        print(result)

    except Exception as exc:
        # Print and log traceback
        logging.exception("Execution failed, attempting to recover last checkpoint.")

        # Attempt to recover last checkpointed state
        try:
            recovered = app.get_state(
                config={"configurable": {"thread_id": thread_id}}
            )
            logging.info("Recovered checkpoint for thread_id=%s", thread_id)
        except Exception as recover_exc:
            # If recovery fails, include the recovery failure
            recovered = {"error": "failed to recover checkpoint", "details": str(recover_exc)}
            logging.exception("Recovery attempt failed.")

        # Attach exception info to recovered state for debugging/audit
        recovered_snapshot = {
            "recovered_state": recovered,
            "exception": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc()
            }
        }

        # Persist recovered snapshot to file
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(recovered_snapshot, f, indent=2)

        print("\n--- Recovered Snapshot Written to output.json ---")
        raise  # re-raise if you want the process to still error after recovery

    else:
        # Normal completion: write final state (or recovered) to disk
        try:
            recovered = app.get_state(
                config={"configurable": {"thread_id": thread_id}}
            )
        except Exception:
            recovered = result

        with open("output.json", "w", encoding="utf-8") as f:
            json.dump({"final_result": result, "recovered_state": recovered}, f, indent=2)

        print("\n--- Final output written to output.json ---")
