import os
import json
import requests
from dotenv import load_dotenv
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama

# ==================== Load ENV ====================
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# ==================== Agent State ====================
class AgentState(TypedDict):
    user_input: str
    location: Optional[str]
    weather: Optional[dict]
    tool_result: Optional[str]
    next_action: Optional[str]
    final_answer: Optional[str]
    last_model_output: Optional[str]

# ==================== Local LLM ====================
llm = ChatOllama(model=MODEL_NAME, temperature=0.3)

# ==================== WEATHER TOOL (current weather + AQI) ====================
def weather_tool(location: str) -> dict:
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=yes"
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ==================== LLM Router ====================
def llm_router(state: AgentState):
    location_known = bool(state.get("location"))
    weather_loaded = state.get("weather") is not None

    prompt = f"""
You are a routing controller for an AI assistant.

TOOLS AVAILABLE:
1. weather_tool(location) → fetches current weather + AQI

RULES:
- If location is missing → choose ONLY "ask_location".
- If location exists but weather is missing → choose ONLY "call_weather".
- If both exist → choose ONLY "finish".

Respond ONLY with JSON:
{{"next_action": "ask_location" | "call_weather" | "finish"}}

CURRENT STATE:
location_known: {location_known}
weather_loaded: {weather_loaded}
location: "{state.get('location')}"
user_input: "{state['user_input']}"
"""

    raw = llm.invoke(prompt).content.strip()

    try:
        data = json.loads(raw)
        state["next_action"] = data["next_action"]
    except:
        state["next_action"] = "finish"

    state["last_model_output"] = raw
    return state

# ==================== Nodes ====================
def ask_location(state: AgentState):
    state["final_answer"] = "I need your location to analyze environmental factors. Where are you located?"
    return state

def call_weather(state: AgentState):
    loc = state["location"]
    weather = weather_tool(loc)
    state["weather"] = weather
    state["tool_result"] = json.dumps(weather)
    return state

def finish_node(state: AgentState):
    weather = state.get("weather", {})

    prompt = f"""
You are an environmental health assistant.

Use the following factual data to generate a concise summary:

User symptoms: {state['user_input']}
Location: {state['location']}
Weather & AQI data: {json.dumps(weather, indent=2)}

Provide a factual, concise summary of whether the symptoms could be influenced by environmental factors like:
- air quality (AQI, PM2.5)
- temperature
- humidity
- wind

Do NOT hallucinate data. Base your answer ONLY on the provided weather information.
"""

    answer = llm.invoke(prompt).content
    state["final_answer"] = answer
    return state

# ==================== LangGraph Orchestration ====================
graph = StateGraph(AgentState)

graph.add_node("router", llm_router)
graph.add_node("ask_location", ask_location)
graph.add_node("call_weather", call_weather)
graph.add_node("finish", finish_node)

graph.set_entry_point("router")

graph.add_conditional_edges(
    "router",
    lambda s: s["next_action"],
    {
        "ask_location": "ask_location",
        "call_weather": "call_weather",
        "finish": "finish"
    }
)

graph.add_edge("call_weather", "router")  # loop back after tool
graph.add_edge("ask_location", END)
graph.add_edge("finish", END)

agent = graph.compile()

# ==================== Interactive Loop ====================
if __name__ == "__main__":
    print("Environmental Symptom Agent\n")

    # Initial message
    state = agent.invoke({
        "user_input": "I've been coughing a lot for 2 days.",
        "location": "Coimbatore",
        "weather": None,
        "tool_result": None,
        "next_action": None,
        "final_answer": None,
        "last_model_output": None,
    })

    print("\nAI:", state["final_answer"])

