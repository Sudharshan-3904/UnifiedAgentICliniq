# sample1.py — Simple LangGraph / Ollama agent demo

This README explains the purpose and procedure for `sample1.py` (in this folder). The script demonstrates a tiny step-by-step agent orchestration using a local Ollama LLM, a LangGraph `StateGraph` workflow, and built-in checkpointing via `MemorySaver`.

**Purpose:**

-   Provide a minimal example showing how to: load configuration from `.env`, define a small agent state, call a local Ollama model to produce reasoning, run a simulated action node, and checkpoint/recover workflow state.

**Key Files:**

-   `sample1.py`: The runnable example.

Summary of what `sample1.py` does

-   Loads environment variables from `.env` (using `python-dotenv`).
-   Configures a local Ollama LLM via `ChatOllama` with `OLLAMA_MODEL` and `LLM_TEMPERATURE` from the environment.
-   Defines an `AgentState` TypedDict with `query`, `reasoning`, and `action_result` fields.
-   Implements two nodes for the `StateGraph`:
    -   `reason` node: sends a prompt (user query) to the LLM and stores the step-by-step reasoning.
    -   `act` node: simulates executing an action based on the reasoning and records an `action_result`.
-   Builds a `StateGraph` workflow, compiles it with a `MemorySaver` checkpointer, and provides an interactive example run when executed as `__main__`.

Environment & Dependencies

-   Python packages used (install via `pip`):
    -   `python-dotenv`
    -   `langchain-ollama` (or whichever package supplies `ChatOllama` in your environment)
    -   `langgraph`
    -   `langsmith`

If you use a `requirements.txt`, ensure it includes these packages or equivalent names used in your environment.

Environment variables (read from `.env`)

-   `LANGSMITH_API_KEY`: API key for LangSmith (optional for tracing).
-   `LANGCHAIN_PROJECT`: Project name used by LangChain tracing (default: `simple-agent-orchestration`).
-   `OLLAMA_MODEL`: Local Ollama model name (default: `mistral`).
-   `LLM_TEMPERATURE`: Model temperature (float, default `0.2`).
-   `LANGCHAIN_TRACING_V2`: Toggle tracing (e.g., `true`/`false`).

Example `.env` (create at repository root or where you run the script):

```
LANGSMITH_API_KEY=
LANGCHAIN_PROJECT=simple-agent-orchestration
OLLAMA_MODEL=mistral
LLM_TEMPERATURE=0.2
LANGCHAIN_TRACING_V2=true
```

Usage

1. Install dependencies in your Python environment:

```pwsh
pip install python-dotenv langchain-ollama langgraph langsmith
```

2. Create a `.env` file with the required variables (see example above).

3. Run the demo:

```pwsh
cd rec_check_sample
python sample1.py
```

4. Follow the interactive prompt and enter a query. The script will:

-   Invoke the `reason` node (LLM) and then the `act` node.
-   Print the final workflow result.
-   Recover and print the last checkpointed state (using `thread_id = "demo-thread-1"`).
-   Write the recovered state to `output.json`.

Notes and tips

-   The `ChatOllama` client expects a local Ollama instance or compatible API — confirm `OLLAMA_MODEL` is available locally.
-   The example `act` node is intentionally simple; replace `act_node` with real integrations as needed (HTTP calls, system actions, database writes).
-   For reproducible runs, pin package versions in `requirements.txt` and set `LLM_TEMPERATURE` to `0.0` if you need deterministic outputs.

Questions or next steps

-   Want me to create a `requirements.txt` with pinned versions, or add a CI check for the demo? Ask and I’ll add it.
