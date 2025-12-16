"""
Test script to demonstrate the refinement loop.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(env_path)

from src.agent.graph import app
from src.utils.logger import logger

def test_refinement():
    print("\n" + "TEST SUITE: REFINEMENT LOOP" + "\n")
    
    # Use a query that might need refinement (or just check that the node runs)
    query = "tell me about it"  # Vague query might trigger refinement for clarity
    
    print(f"QUERY: {query}")
    print("="*80)
    
    initial_state = {
        "user_query": query,
        "messages": [],
        "generation": "",
        "safety_report": "",
        "is_valid": False,
        "retry_count": 0,
        "refinement_count": 0,
        "refinement_feedback": None,
        "tool_used": None
    }
    
    config = {"configurable": {"thread_id": "test_refinement"}}
    
    try:
        # We can't easily see the internal steps here without streaming or logging
        # But we can check the final state
        result = app.invoke(initial_state, config)
        
        print(f"\nRESULT:")
        print(f"Refinement Count: {result.get('refinement_count', 0)}")
        print(f"Final Response: {result.get('generation', 'No response')[:200]}...")
        
        if result.get('refinement_count', 0) > 0:
            print("[OK] Refinement loop was triggered")
        else:
            print("[INFO] No refinement needed (response was already aligned)")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        logger.error(f"Error testing refinement: {e}")

if __name__ == "__main__":
    test_refinement()
