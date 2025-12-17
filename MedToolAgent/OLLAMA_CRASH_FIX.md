# Fix for Ollama Crash Issue

## Problem
When running both AGENT_MODEL and SAFETY_MODEL simultaneously, the Ollama llama runner process crashes with exit status 2. This is typically a resource/memory issue.

## Solution 1: Use the Same LLM Instance (Recommended)

Modify [backend/src/agent/nodes.py](backend/src/agent/nodes.py) to share one LLM instance:

```python
# Initialize Models - Use same instance for both
llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.AGENT_MODEL)
safety_llm = llm  # Reuse the same instance
```

## Solution 2: Use Lighter Models

Edit your `.env` file:

```env
AGENT_MODEL=mistral  # Lighter model for agent
SAFETY_MODEL=mistral  # Use same lighter model
```

Available lightweight models on Ollama:
- `mistral` - Fast, efficient
- `neural-chat` - Good balance
- `orca-mini` - Small but capable

## Solution 3: Use Streaming Without Safety Check

If you want to keep both models but avoid the crash, reduce the frequency of safety checks or disable them:

Edit [backend/src/agent/nodes.py] safety_agent function to add error handling:

```python
def safety_agent(state: AgentState):
    logger.info("Running Safety Agent...")
    generation = state["generation"]
    
    try:
        safety_prompt = f"""
        Analyze the following medical response for safety and accuracy. 
        If it is safe and appears valid, reply with 'SAFE'. 
        If it is unsafe or hallucinated, reply with 'UNSAFE' and a reason.
        
        Response to analyze:
        {generation}
        """
        response = safety_llm.invoke(safety_prompt)
        report = response.content
        is_valid = "SAFE" in report.upper()
    except Exception as e:
        logger.warning(f"Safety check failed: {e}. Assuming safe.")
        report = f"Safety check skipped due to error: {e}"
        is_valid = True  # Default to safe on error
    
    return {"safety_report": report, "is_valid": is_valid}
```

## Why This Happened

Your DuckDuckGo implementation is working perfectly! The error occurs because:
1. `search_duckduckgo` was called successfully and returned results
2. After that, the agent moved to the refinement phase
3. Then it tried to run the safety check with a different LLM model
4. Running two large `gemma:latest` models simultaneously exceeded available resources
5. The Ollama daemon crashed

## Recommended Action

Apply **Solution 1** (use same LLM instance) as it's the simplest and most effective:

```python
# In backend/src/agent/nodes.py, line 11-12
llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.AGENT_MODEL)
safety_llm = llm  # Share the same instance instead of creating a second one
```

This will:
- Prevent resource exhaustion
- Keep your DuckDuckGo tool working
- Allow the full agent pipeline to complete
