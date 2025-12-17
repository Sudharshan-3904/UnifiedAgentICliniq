import logging
import sys

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

from src.agent.graph import app
from src.agent.state import AgentState

# Test with a simple query
initial_state = {
    "user_query": "What is aspirin?",
    "retry_count": 0,
    "messages": [],
    "prompt": None,
    "generation": None,
    "safety_report": None,
    "is_valid": False,
    "refinement_count": 0,
    "refinement_feedback": None,
    "final_output": None,
    "tool_used": None
}

config = {"configurable": {"thread_id": "test_thread"}}

try:
    print("Starting agent...")
    result = app.invoke(initial_state, config=config)
    print("✓ Agent executed successfully")
    print(f"Generation: {result.get('generation')}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
