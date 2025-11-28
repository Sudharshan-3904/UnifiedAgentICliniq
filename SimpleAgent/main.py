import os
import json
import re
import sys
import traceback
from typing import Any, Dict, List, TypedDict
from dataclasses import dataclass

try:
    from ollama import chat as ollama_chat
except Exception:
    try:
        import ollama
        ollama_chat = ollama.chat
    except Exception:
        ollama_chat = None

try:
    from langchain.tools import tool
    from langchain.messages import HumanMessage, ToolMessage, AnyMessage
    from langgraph.graph import StateGraph, START, END
except Exception:
    def tool(fn):
        return fn
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
            self.role = "user"
        def __repr__(self):
            return f"HumanMessage({self.content!r})"
    class ToolMessage:
        def __init__(self, content: str, tool_call_id: str = ""):
            self.content = content
            self.tool_call_id = tool_call_id
            self.role = "tool"
        def __repr__(self):
            return f"ToolMessage({self.content!r})"
    AnyMessage = object
    class StateGraph:
        def __init__(self, *_):
            self.nodes = {}
            self.start = None
        def add_node(self, name, fn):
            self.nodes[name] = fn
        def add_edge(self, a, b):
            pass
        def add_conditional_edges(self, name, cond, to_names):
            self.cond = cond
            self.to_names = to_names
            self.start = name
        def compile(self):
            def invoke(state: Dict[str, Any]):
                current_state = state
                while True:
                    node_fn = self.nodes[self.start]
                    out = node_fn(current_state)
                    current_state = {**current_state, **out}
                    next_name = self.cond(current_state)
                    if next_name == END:
                        return current_state
                    node_fn = self.nodes[next_name]
                    out = node_fn(current_state)
                    current_state = {**current_state, **out}
                return current_state
            return type("Agent", (), {"invoke": staticmethod(invoke)})

WORKSPACE = os.path.join(os.path.dirname(__file__), "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

ORIGINAL_FILE_PATH = "/mnt/data/main.py"

MODEL_NAME = "granite3.1-moe:latest"

SYSTEM_PROMPT = """
You are a file-handling assistant that MUST communicate only using JSON objects.
You must NOT output any free text, explanation, or markdown.

When you want the agent to call a tool, output EXACTLY one JSON object (and nothing else) with this shape:
{"tool":"<tool_name>", "args": { ... }}

When you want to finish and return a final answer to the user, output EXACTLY one JSON object (and nothing else) with this shape:
{"final":"<final text answer here>"}

Do not wrap the JSON in backticks or triple fences. If you must use a code fence for safety, ensure the content inside the fence is just the JSON object (but prefer no fences).
Only use these two shapes. If you are uncertain, ask the user via a tool that lists files or reads files.

Available tools: list_files(path), read_file(path), write_file(path, content), append_file(path, content), delete_file(path).
The agent runs in a sandbox and only has access to the workspace/ directory.
"""

def strip_code_fence(text: str) -> str:
    """Strip surrounding markdown/code fences and whitespace."""
    if not text:
        return text
    text = re.sub(r"^```(?:\w+)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^~~~(?:\w+)?\s*", "", text)
    text = re.sub(r"\s*~~~$", "", text)
    return text.strip()

def extract_json(text: str) -> Any:
    """
    Try to extract a JSON object from text.
    Prefer full-text parse; if that fails, search for first JSON object via regex braces matching.
    Returns parsed JSON or raises ValueError.
    """
    if not text:
        raise ValueError("Empty response")
    txt = strip_code_fence(text)
    try:
        return json.loads(txt)
    except Exception:
        pass
    start = None
    depth = 0
    for i, ch in enumerate(txt):
        if ch == "{":
            if start is None:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = txt[start:i+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    start = None
                    depth = 0
                    continue
    pattern = re.search(r"\{.*\}", txt, flags=re.DOTALL)
    if pattern:
        try:
            return json.loads(pattern.group(0))
        except Exception:
            pass
    raise ValueError("No parseable JSON found in model output.")

def safe_path_in_workspace(path: str) -> str:
    """Return an absolute safe path inside the workspace; raise ValueError if escape attempted."""
    joined = os.path.normpath(os.path.join(WORKSPACE, path))
    abs_workspace = os.path.abspath(WORKSPACE)
    abs_joined = os.path.abspath(joined)
    if not abs_joined.startswith(abs_workspace):
        raise ValueError("Access denied: path outside workspace")
    return abs_joined

@tool
def list_files(path: str = ".") -> str:
    """
    Lists all files and directories inside the workspace.

Arguments:
  path (str): A relative path inside the workspace directory.
              Defaults to "." (the root of the workspace).

Behavior:
  - Returns a JSON object containing a list of directory items.
  - If the path does not exist or is outside the workspace, returns an error.
  - Does NOT read file contents, only lists names.

Use this when:
  - You need to inspect what files or folders exist.
  - You are unsure of valid paths and want to explore the workspace.

    """
    try:
        sp = safe_path_in_workspace(path)
    except Exception as e:
        return f"ERROR: {e}"
    try:
        items = os.listdir(sp)
        return json.dumps({"items": items})
    except Exception as e:
        return f"ERROR: {e}"

@tool
def read_file(path: str) -> str:
    """Reads a text file from the workspace and returns its entire contents.

Arguments:
  path (str): The relative path to the file inside the workspace.

Behavior:
  - Returns a JSON object with the file path and its text contents.
  - If the file does not exist or path escapes the workspace, returns an error.
  - Supports only text files, not binary.

Use this when:
  - You need to inspect existing content before modifying or appending.
  - You want to verify that a file was written correctly.
"""
    try:
        sp = safe_path_in_workspace(path)
    except Exception as e:
        return f"ERROR: {e}"
    if not os.path.exists(sp):
        return "ERROR: not found"
    try:
        with open(sp, "r", encoding="utf-8") as f:
            content = f.read()
        return json.dumps({"path": path, "content": content})
    except Exception as e:
        return f"ERROR: {e}"

@tool
def write_file(path: str, content: str) -> str:
    """Creates or overwrites a file with the given text content.

Arguments:
  path (str): The relative file path to write into inside the workspace.
  content (str): Full replacement text for the file.

Behavior:
  - Completely replaces the file.
  - Creates intermediate directories if needed.
  - Returns a JSON object indicating success or an error message.

Use this when:
  - You need to create a new file.
  - You want to rewrite an existing file completely.
  - You want to initialize a file before later appending to it.
"""
    try:
        sp = safe_path_in_workspace(path)
    except Exception as e:
        return f"ERROR: {e}"
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w", encoding="utf-8") as f:
            f.write(content)
        return json.dumps({"status": "ok", "path": path})
    except Exception as e:
        return f"ERROR: {e}"

@tool
def append_file(path: str, content: str) -> str:
    """Appends text to the end of an existing (or new) file.

Arguments:
  path (str): The relative file path inside the workspace.
  content (str): Text to append at the end of the file.

Behavior:
  - Creates the file if it does not exist.
  - Adds the given text at the end without removing previous data.
  - Returns a JSON success object or error message.

Use this when:
  - You want to add lines incrementally to a file.
  - You want to build up a file step-by-step across multiple tool calls.
"""
    try:
        sp = safe_path_in_workspace(path)
    except Exception as e:
        return f"ERROR: {e}"
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "a", encoding="utf-8") as f:
            f.write(content)
        return json.dumps({"status": "ok", "path": path})
    except Exception as e:
        return f"ERROR: {e}"

@tool
def delete_file(path: str) -> str:
    """Deletes a file inside the workspace.

Arguments:
  path (str): Relative path to the file to delete.

Behavior:
  - Removes the file permanently.
  - Does NOT delete directories.
  - Returns a JSON object confirming deletion or an error message.

Use this when:
  - You need to remove outdated or temporary files.
  - You want to clean up after generating outputs.
"""
    try:
        sp = safe_path_in_workspace(path)
    except Exception as e:
        return f"ERROR: {e}"
    if os.path.isdir(sp):
        return "ERROR: refusing to delete directory"
    if not os.path.exists(sp):
        return "ERROR: not found"
    try:
        os.remove(sp)
        return json.dumps({"status": "deleted", "path": path})
    except Exception as e:
        return f"ERROR: {e}"

TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "delete_file": delete_file,
}

@dataclass
class OllamaChatWrapper:
    model: str = MODEL_NAME
    base_url: str | None = None

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        if ollama_chat is None:
            raise RuntimeError(
                "Ollama client not available. Install the Ollama Python client and ensure Ollama daemon is running."
            )
        try:
            resp = ollama_chat(model=self.model, messages=messages, stream=False)
            try:
                return resp if isinstance(resp, dict) else resp.model_dump()
            except Exception:
                try:
                    return resp if isinstance(resp, dict) else resp.dict()
                except Exception:
                    return {"message": {"content": str(resp)}}
        except TypeError:
            try:
                resp = ollama_chat(messages=messages, model=self.model)
                try:
                    return resp if isinstance(resp, dict) else resp.model_dump()
                except Exception:
                    return resp if isinstance(resp, dict) else resp.dict()
            except Exception as e:
                raise

    def simple_reply(self, user_text: str) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}]
        r = self.chat(messages)
        for key in ("message", "choices"):
            if key in r:
                try:
                    if isinstance(r.get(key), dict) and "content" in r.get(key):
                        return r[key]["content"]
                    if isinstance(r.get(key), list) and r[key] and "content" in r[key][0]:
                        return r[key][0]["content"]
                except Exception:
                    continue
        for k in ("content", "text"):
            if k in r:
                return r[k]
        return json.dumps(r)

ollama = OllamaChatWrapper()

class MessagesState(TypedDict):
    messages: List[Any]
    llm_calls: int

def llm_call(state: MessagesState) -> Dict[str, Any]:
    """
    Calls the model with the conversation history plus system prompt.
    Expects the model to return JSON-only outputs per SYSTEM_PROMPT.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in state.get("messages", []):
        content = getattr(m, "content", str(m))
        role = getattr(m, "role", "user")
        messages.append({"role": role, "content": content})
    try:
        resp = ollama.chat(messages)
        content = ""
        if isinstance(resp, dict):
            if "message" in resp and isinstance(resp["message"], dict) and "content" in resp["message"]:
                content = resp["message"]["content"]
            elif "choices" in resp and isinstance(resp["choices"], list) and resp["choices"]:
                c0 = resp["choices"][0]
                if isinstance(c0, dict) and "message" in c0 and "content" in c0["message"]:
                    content = c0["message"]["content"]
                elif isinstance(c0, dict) and "content" in c0:
                    content = c0["content"]
            elif "content" in resp:
                content = resp["content"]
            else:
                content = json.dumps(resp)
        else:
            content = str(resp)
    except Exception as e:
        tb = traceback.format_exc()
        content = json.dumps({"final": f"LLM call failed: {e}\n{tb}"})
    new_msg = HumanMessage(content=content)
    return {"messages": [new_msg], "llm_calls": state.get("llm_calls", 0) + 1}

def tool_node(state: MessagesState) -> Dict[str, Any]:
    """
    Parse the last model message as JSON, execute the indicated tool, and return a ToolMessage with the observation.
    """
    last = state["messages"][-1]
    text = getattr(last, "content", "")
    try:
        parsed = extract_json(text)
    except Exception as e:
        obs = f"ERROR: Could not parse JSON from model output: {e}"
        return {"messages": [ToolMessage(content=obs, tool_call_id="parse_error")]}
    if isinstance(parsed, dict) and "tool" in parsed:
        tool_name = parsed["tool"]
        args = parsed.get("args", {})
        if tool_name not in TOOLS:
            return {"messages": [ToolMessage(content=f"ERROR: Unknown tool '{tool_name}'", tool_call_id="tool_missing")]}
        try:
            if hasattr(TOOLS[tool_name], "invoke"):
                result = TOOLS[tool_name].invoke(args)
            else:
                result = TOOLS[tool_name](**args)
            return {"messages": [ToolMessage(content=str(result), tool_call_id=tool_name)]}
        except TypeError as e:
            return {"messages": [ToolMessage(content=f"ERROR: Tool call failed: {e}", tool_call_id=tool_name)]}
        except Exception as e:
            tb = traceback.format_exc()
            return {"messages": [ToolMessage(content=f"ERROR: Tool exception: {e}\n{tb}", tool_call_id=tool_name)]}
    elif isinstance(parsed, dict) and "final" in parsed:
        return {"messages": [ToolMessage(content=str(parsed["final"]), tool_call_id="final")]}
    else:
        return {"messages": [ToolMessage(content="ERROR: JSON missing 'tool' or 'final' key", tool_call_id="json_key_error")]}

def should_continue(state: MessagesState) -> str:
    """
    Decide next node: if last model output contains JSON with a 'tool' key -> run tool_node,
    otherwise if it contains 'final' -> END, else attempt one tool_node to parse and inform.
    """
    last = state["messages"][-1]
    text = getattr(last, "content", "")
    try:
        parsed = extract_json(text)
        if isinstance(parsed, dict) and "tool" in parsed:
            return "tool_node"
        if isinstance(parsed, dict) and "final" in parsed:
            return END
    except Exception:
        return "tool_node"
    return END

agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()

def pretty_print_out(state: Dict[str, Any]) -> None:
    """Print messages collected in state in a readable way."""
    msgs = state.get("messages", [])
    for m in msgs:
        try:
            content = getattr(m, "content", str(m))
            role = getattr(m, "role", "unknown")
            print(f"[{role}] {content}")
        except Exception:
            print(m)

if __name__ == "__main__":
    user_prompt = input("Enter rompt to model: ")
    initial_state: MessagesState = {"messages": [HumanMessage(content=user_prompt)], "llm_calls": 0}
    try:
        result_state = agent.invoke(initial_state)
        pretty_print_out(result_state)
    except Exception as e:
        print("Agent run failed:", e)
        traceback.print_exc()
        sys.exit(1)
