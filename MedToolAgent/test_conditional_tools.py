"""
Test script to demonstrate conditional PubMed tool calling.
This script tests various queries to show when PubMed is called vs. when it's not.
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
from src.agent.state import AgentState
from src.utils.logger import logger

def test_query(query: str, description: str):
    """Test a single query and show if PubMed was called."""
    print("\n" + "="*80)
    print(f"TEST: {description}")
    print(f"QUERY: {query}")
    print("="*80)
    
    # Create initial state
    initial_state = {
        "user_query": query,
        "messages": [],
        "generation": "",
        "safety_report": "",
        "is_valid": False,
        "retry_count": 0,
        "tool_used": None
    }
    
    # Run the agent
    config = {"configurable": {"thread_id": f"test_{hash(query)}"}}
    
    try:
        result = app.invoke(initial_state, config)
        
        print(f"\nRESULT:")
        print(f"Tool Used: {result.get('tool_used', 'None')}")
        print(f"Response: {result.get('generation', 'No response')[:200]}...")
        
        if result.get('tool_used') == 'search_pubmed':
            print("[OK] PubMed was called (as expected for research queries)")
        elif result.get('tool_used') is None:
            print("[OK] No tool called (direct answer provided)")
        else:
            print(f"[INFO] Other tool called: {result.get('tool_used')}")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        logger.error(f"Error testing query: {e}")

def main():
    """Run test suite for conditional tool calling."""
    print("\n" + "TEST SUITE: CONDITIONAL TOOL CALLING" + "\n")
    print("This demonstrates when PubMed is called vs. when it's not.\n")
    
    # Test cases that SHOULD NOT call PubMed
    print("\nPART 1: Queries that should NOT call PubMed")
    print("(General medical knowledge - should answer directly)")
    
    test_query(
        "What is diabetes?",
        "General definition - should answer directly"
    )
    
    test_query(
        "Explain the symptoms of hypertension",
        "Basic medical explanation - should answer directly"
    )
    
    test_query(
        "What are common side effects of aspirin?",
        "General medication info - should answer directly"
    )
    
    # Test cases that SHOULD call PubMed
    print("\n\nPART 2: Queries that SHOULD call PubMed")
    print("(Research/literature requests - should invoke PubMed)")
    
    test_query(
        "What are the latest studies on diabetes treatment?",
        "Recent research request - should call PubMed"
    )
    
    test_query(
        "Find recent clinical trials for hypertension medications",
        "Clinical trials request - should call PubMed"
    )
    
    test_query(
        "Show me publications about COVID-19 vaccines from 2024",
        "Specific publications request - should call PubMed"
    )
    
    print("\n\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print("\nReview the results above to verify conditional tool calling is working correctly.")
    print("PubMed should only be called for queries explicitly requesting research/literature.\n")

if __name__ == "__main__":
    main()
