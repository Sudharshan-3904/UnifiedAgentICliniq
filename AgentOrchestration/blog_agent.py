import os
import json
import logging
import pickle
import random
import time
from typing import TypedDict, Optional
from datetime import datetime
from pathlib import Path
from copy import deepcopy

# ---- Langchain / LangGraph imports ----
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint import MemorySaver
from langgraph.prebuilt import ToolNode

# --------------------------------------------------
# Environment setup
# --------------------------------------------------

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"blog_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)
MAX_CHECKPOINTS = 10

# Env vars
BLOGGER_USERNAME = os.getenv("BLOGGER_USERNAME")
BLOGGER_API_KEY = os.getenv("BLOGGER_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
CHAT_MODEL = os.getenv("OLLAMA_MODEL_NAME")

LOGGED_IN = False

# --------------------------------------------------
# Metrics
# --------------------------------------------------

class EvaluationMetrics:
    def __init__(self):
        self.total_requests = 0
        self.successful_generations = 0
        self.failed_generations = 0
        self.successful_posts = 0
        self.failed_posts = 0
        self.total_recovery_attempts = 0
        self.successful_recoveries = 0
        self.start_time = datetime.now()
    
    def record_generation_success(self):
        self.successful_generations += 1
        self.total_requests += 1

    def record_generation_failure(self):
        self.failed_generations += 1
        self.total_requests += 1

    def record_post_success(self):
        self.successful_posts += 1

    def record_post_failure(self):
        self.failed_posts += 1

    def record_recovery_attempt(self, success: bool):
        self.total_recovery_attempts += 1
        if success:
            self.successful_recoveries += 1

    def get_metrics(self) -> dict:
        uptime = datetime.now() - self.start_time
        success_rate = (
            (self.successful_generations / self.total_requests) * 100
            if self.total_requests > 0 else 0
        )
        recovery_rate = (
            (self.successful_recoveries / self.total_recovery_attempts) * 100
            if self.total_recovery_attempts > 0 else 0
        )

        return {
            "total_requests": self.total_requests,
            "successful_generations": self.successful_generations,
            "failed_generations": self.failed_generations,
            "generation_success_rate": round(success_rate, 2),
            "successful_posts": self.successful_posts,
            "failed_posts": self.failed_posts,
            "recovery_attempts": self.total_recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "recovery_success_rate": round(recovery_rate, 2),
            "uptime_seconds": uptime.total_seconds(),
        }

metrics = EvaluationMetrics()

# --------------------------------------------------
# Custom Checkpoint Manager (kept for external recovery UI / inspection)
# --------------------------------------------------

class CheckpointManager:
    @staticmethod
    def save_checkpoint(state: dict, checkpoint_name: str = None):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            checkpoint_name = checkpoint_name or f"checkpoint_{timestamp}"
            checkpoint_path = CHECKPOINT_DIR / f"{checkpoint_name}.pkl"

            with open(checkpoint_path, 'wb') as f:
                pickle.dump(state, f)

            logger.info(f"Checkpoint saved: {checkpoint_path}")
            CheckpointManager._cleanup_old_checkpoints()
            return checkpoint_path
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return None

    @staticmethod
    def load_checkpoint(checkpoint_name: str = None) -> Optional[dict]:
        try:
            if checkpoint_name:
                checkpoint_path = CHECKPOINT_DIR / f"{checkpoint_name}.pkl"
            else:
                checkpoints = sorted(
                    CHECKPOINT_DIR.glob("*.pkl"),
                    key=os.path.getmtime, reverse=True
                )
                if not checkpoints:
                    logger.warning("No checkpoints found")
                    return None
                checkpoint_path = checkpoints[0]

            with open(checkpoint_path, 'rb') as f:
                state = pickle.load(f)

            logger.info(f"Checkpoint loaded: {checkpoint_path}")
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    @staticmethod
    def _cleanup_old_checkpoints():
        try:
            checkpoints = sorted(CHECKPOINT_DIR.glob("*.pkl"), key=os.path.getmtime)
            if len(checkpoints) > MAX_CHECKPOINTS:
                for old_cp in checkpoints[:-MAX_CHECKPOINTS]:
                    old_cp.unlink()
                    logger.info(f"Deleted old checkpoint: {old_cp}")
        except Exception as e:
            logger.error(f"Checkpoint cleanup error: {e}")

    @staticmethod
    def get_checkpoint_list() -> list:
        try:
            checkpoints = sorted(
                CHECKPOINT_DIR.glob("*.pkl"),
                key=os.path.getmtime,
                reverse=True
            )
            return [cp.stem for cp in checkpoints]
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

# --------------------------------------------------
# Recovery Manager
# --------------------------------------------------

class RecoveryManager:
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    @staticmethod
    def retry_operation(operation, *args, operation_name="operation", **kwargs):
        for attempt in range(RecoveryManager.MAX_RETRIES):
            try:
                logger.info(f"Attempting {operation_name} ({attempt+1}/{RecoveryManager.MAX_RETRIES})")
                result = operation(*args, **kwargs)
                metrics.record_recovery_attempt(success=True)
                return result
            except Exception as e:
                metrics.record_recovery_attempt(success=False)
                logger.warning(f"Attempt {attempt+1} failed for {operation_name}: {e}")

                if attempt < RecoveryManager.MAX_RETRIES - 1:
                    wait = RecoveryManager.RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {wait} seconds...")
                    time.sleep(wait)
                else:
                    logger.error(f"All attempts failed for {operation_name}")
                    raise

# --------------------------------------------------
# Chaos Manager
# --------------------------------------------------

class ChaosManager:
    def __init__(self, failure_rate=0.3):
        self.failure_rate = failure_rate
        self.enabled = False
        self.total_injections = 0
        self.successful_injections = 0

    def enable_chaos(self, failure_rate=None):
        if failure_rate is not None:
            if isinstance(failure_rate, str):
                failure_rate = float(failure_rate.strip().replace("%", "")) / 100
            self.failure_rate = max(0.0, min(1.0, failure_rate))

        self.enabled = True
        logger.warning(f"🔥 CHAOS MODE ENABLED (rate={self.failure_rate*100}%)")

    def disable_chaos(self):
        self.enabled = False
        logger.info("Chaos mode disabled.")

    def inject_random_failure(self, op_name="unknown"):
        if not self.enabled:
            return

        self.total_injections += 1
        if random.random() < self.failure_rate:
            self.successful_injections += 1
            msg = f"Injected failure in {op_name}"
            logger.warning(f"🔥 CHAOS FAILURE: {msg}")
            raise Exception(msg)

chaos_manager = ChaosManager()

# --------------------------------------------------
# Debug log infrastructure
# --------------------------------------------------

DEBUG_LOGS = []

def _append_debug_log(entry: dict):
    try:
        DEBUG_LOGS.append(deepcopy(entry))
        log_path = LOG_DIR / "lang_debug_events.jsonl"
        with open(log_path, 'a', encoding='utf8') as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.warning(f"Debug log append failed: {e}")

def invoke_and_log(llm, payload, model_name="llm"):
    try:
        start_ts = datetime.now().isoformat()
        result = llm.invoke(payload)

        entry = {
            "timestamp": start_ts,
            "model": model_name,
            "input": payload,
            "output": getattr(result, "content", str(result)),
        }
        _append_debug_log(entry)
        return result

    except Exception as e:
        entry = {"timestamp": datetime.now().isoformat(), "model": model_name, "input": payload, "error": str(e)}
        _append_debug_log(entry)
        raise

# --------------------------------------------------
# Login
# --------------------------------------------------

def login():
    if not BLOGGER_USERNAME or not BLOGGER_API_KEY:
        raise ValueError("Missing BLOGGER_USERNAME or BLOGGER_API_KEY")
    globals()['LOGGED_IN'] = True
    logger.info("Logged in.")
    return True

# --------------------------------------------------
# Tools
# --------------------------------------------------

raw_llm = init_chat_model(CHAT_MODEL, model_provider="ollama")

@tool
def create_new_blog(title, instructions):
    try:
        if not LOGGED_IN:
            login()

        chaos_manager.inject_random_failure(f"create_blog_{title}")

        prompt = (
            f"You are a blog writer. Create a blog titled '{title}'. "
            f"Instructions:\n{instructions}\n\n"
            "Return valid JSON with fields: title, content."
        )

        def _op():
            return invoke_and_log(raw_llm, prompt, model_name="raw_llm")

        response = RecoveryManager.retry_operation(_op, operation_name=f"create_blog_{title}")
        blog_post = json.loads(response.content)

        # Refinement rounds
        for i in range(2):
            refine_prompt = (
                "Refine this blog. Improve clarity, structure, and style. "
                "Return ONLY JSON with 'title' and 'content'.\n\n"
                f"{json.dumps(blog_post)}"
            )

            def _refine():
                return invoke_and_log(raw_llm, refine_prompt, model_name="raw_llm")

            refined = RecoveryManager.retry_operation(_refine, operation_name=f"refine_blog_{title}_round{i+1}")
            blog_post = json.loads(refined.content)

        CheckpointManager.save_checkpoint({"blog_post": blog_post}, f"blog_{title}")
        metrics.record_generation_success()
        return blog_post

    except Exception as e:
        logger.error(f"Blog creation error: {e}")
        metrics.record_generation_failure()
        return {"error": str(e)}

@tool
def post_new_blog(blog_post):
    try:
        if not LOGGED_IN:
            login()

        title = blog_post.get("title", "Unknown")
        chaos_manager.inject_random_failure(f"post_blog_{title}")

        def _save():
            with open("blog_post.json", "w") as f:
                json.dump(blog_post, f)
            return f"Blog '{title}' posted."

        result = RecoveryManager.retry_operation(_save, operation_name=f"post_blog_{title}")

        CheckpointManager.save_checkpoint(
            {"posted_blog": blog_post, "timestamp": datetime.now().isoformat()},
            f"posted_{title}"
        )
        metrics.record_post_success()
        return result

    except Exception as e:
        metrics.record_post_failure()
        return {"error": str(e)}

@tool
def get_last_n_blogs(n=3):
    try:
        if not LOGGED_IN:
            login()

        chaos_manager.inject_random_failure(f"get_last_{n}_blogs")

        def _retrieve():
            blogs = []
            for root, _, files in os.walk("./Outputs/blogs"):
                for f in files:
                    if f.endswith(".json") and len(blogs) < n:
                        blogs.append(os.path.join(root, f))
            return blogs

        blogs = RecoveryManager.retry_operation(_retrieve, operation_name=f"retrieve_last_{n}")
        return blogs

    except Exception as e:
        return {"error": str(e)}

# --------------------------------------------------
# Chat State
# --------------------------------------------------

class ChatState(TypedDict):
    messages: list
    latest_blog: Optional[dict]
    last_n_blogs: Optional[list]

llm = init_chat_model(CHAT_MODEL, model_provider="ollama")
tool_node = ToolNode([create_new_blog, post_new_blog, get_last_n_blogs])

# --------------------------------------------------
# LLM Node with retry
# --------------------------------------------------

def llm_node(state):
    def _invoke():
        system_message = SystemMessage(
            content=(
                "You are an AI assistant specialized in blog writing.\n"
                "You can create new blog posts, post them, or retrieve old posts.\n"
                "Return JSON when generating blogs."
            )
        )
        msgs = [system_message] + state["messages"]
        return invoke_and_log(llm, msgs, model_name="llm")

    result = RecoveryManager.retry_operation(_invoke, operation_name="llm_node")
    return {"messages": state["messages"] + [result]}

# --------------------------------------------------
# Tool Node
# --------------------------------------------------

def tools_node(state):
    result = tool_node.invoke(state)
    return {"messages": state["messages"] + result.get("messages", [])}

# --------------------------------------------------
# Router
# --------------------------------------------------

def router(state):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    elif isinstance(last, ToolMessage):
        return "llm"
    return "end"

# --------------------------------------------------
# Error Handler Node
# --------------------------------------------------

def error_handler(state, error):
    logger.error(f"Graph error trapped: {error}")
    msg = AIMessage(content=f"Recovered from error: {error}")
    return {"messages": state["messages"] + [msg]}

# --------------------------------------------------
# Build Graph with MemorySaver
# --------------------------------------------------

checkpointer = MemorySaver()
builder = StateGraph(ChatState, checkpointer=checkpointer)

builder.add_node("llm", llm_node)
builder.add_node("tools", tools_node)
builder.add_node("error", error_handler)

builder.add_edge(START, "llm")
builder.add_edge("tools", "llm")
builder.add_conditional_edges("llm", router, {"tools": "tools", "end": END})

# Built-in error recovery
builder.add_error_edge("llm", "error")
builder.add_error_edge("tools", "error")

graph = builder.compile()

# --------------------------------------------------
# Main API Function
# --------------------------------------------------

def process_blog_request(user_message: str, use_checkpoint=False, checkpoint_name=None):
    try:
        logger.info(f"Processing request: {user_message}")

        if use_checkpoint:
            state = CheckpointManager.load_checkpoint(checkpoint_name)
            if state:
                initial_state = state
            else:
                initial_state = {"messages": [HumanMessage(content=user_message)], "last_n_blogs": None, "latest_blog": None}
        else:
            initial_state = {"messages": [HumanMessage(content=user_message)], "last_n_blogs": None, "latest_blog": None}

        CheckpointManager.save_checkpoint(initial_state, f"request_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        final_state = None

        try:
            for step in graph.stream(initial_state, resume=True):
                final_state = step
        except Exception as e:
            logger.warning(f"Graph crashed, attempting resume: {e}")
            for step in graph.stream({}, resume=True):
                final_state = step

        if final_state and "messages" in final_state:
            last = final_state["messages"][-1]
            content = last.content if hasattr(last, "content") else str(last)

            CheckpointManager.save_checkpoint(final_state, f"success_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            return {"content": content, "success": True, "metadata": metrics.get_metrics()}

        return {"content": "No response", "success": False, "metadata": metrics.get_metrics()}

    except Exception as e:
        logger.error(f"Request error: {e}", exc_info=True)
        return {"content": str(e), "success": False, "metadata": metrics.get_metrics()}

# --------------------------------------------------
# Utility API
# --------------------------------------------------

def get_metrics():
    return metrics.get_metrics()

def get_checkpoints():
    return CheckpointManager.get_checkpoint_list()

def recover_from_checkpoint(name):
    return process_blog_request("Recovery", use_checkpoint=True, checkpoint_name=name)

def clear_checkpoints():
    try:
        for cp in CHECKPOINT_DIR.glob("*.pkl"):
            cp.unlink()
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def enable_chaos_testing(rate=0.3):
    chaos_manager.enable_chaos(rate)
    return {"status": "enabled"}

def disable_chaos_testing():
    chaos_manager.disable_chaos()
    return {"status": "disabled"}

