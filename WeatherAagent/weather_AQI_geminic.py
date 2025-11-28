# weather_AQI_geminic.py

import os
import sys
import json
import requests
import google.generativeai as genai
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any


#-------------------- API KEYS --------------------#
WEATHER_KEY = os.getenv("WEATHERAPI_KEY")
GEMINI_KEY  = os.getenv("GOOGLE_API_KEY")

if not WEATHER_KEY:
    raise Exception("WEATHERAPI_KEY is missing")
if not GEMINI_KEY:
    raise Exception("GOOGLE_API_KEY is missing")

# Configure Gemini (NEW API)
genai.configure(api_key=GEMINI_KEY)


# -------------------- STATE --------------------
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    question: str
    location: str


# -------------------- AUTO DETECT CITY --------------------
def auto_detect_city():
    try:
        info = requests.get("https://ipinfo.io/json", timeout=5).json()
        return info.get("city")
    except:
        return None


# -------------------- WEATHER TOOL --------------------
def fetch_weather(location: str):
    """Fetch temperature, condition & PM2.5 AQI using WeatherAPI.com"""
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q={location}&aqi=yes"

    try:
        resp = requests.get(url, timeout=5).json()

        return {
            "location": location,
            "temp_c": resp["current"]["temp_c"],
            "condition": resp["current"]["condition"]["text"],
            "humidity": resp["current"]["humidity"],
            "wind_kph": resp["current"]["wind_kph"],
            "aqi_pm25": resp["current"]["air_quality"]["pm2_5"]
        }

    except Exception as e:
        return {"error": str(e)}


# -------------------- GEMINI 2.0 FLASH WRAPPER --------------------
class GeminiLLM:
    """Uses Gemini 2.0 Flash (FAST + FREE)."""

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def run(self, prompt: str):
        result = self.model.generate_content(prompt)
        return result.text


# -------------------- AGENT NODE --------------------
def agent_node(state: AgentState):

    messages = state["messages"]

    # 1️⃣ First pass → fetch weather
    if len(messages) == 0:
        weather = fetch_weather(state["location"])
        messages.append({"role": "tool", "result": weather})
        return state | {"messages": messages, "next": "agent"}

    # 2️⃣ Second pass → generate medical explanation
    last = messages[-1]

    if last["role"] == "tool":
        weather = last["result"]
        model = GeminiLLM()

        prompt = f"""
You are a medical assistant.
Explain how these weather + AQI conditions can worsen the Condition and give me some precautions.
Do NOT diagnose or give medication instructions.

Weather:
{json.dumps(weather, indent=2)}

User question:
{state['question']}
"""

        response = model.run(prompt)
        messages.append({"role": "assistant", "content": response})
        return state | {"messages": messages, "next": "END"}

    return state | {"messages": messages, "next": "END"}


# -------------------- BUILD GRAPH --------------------
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        lambda out: out["next"],
        {"agent": "agent", "END": END}
    )

    return graph.compile()


# -------------------- RUN AGENT --------------------
def run_agent(question, location=None):

    if not location:
        print("→ Detecting location from IP...")
        location = auto_detect_city()

    if not location:
        return "Could not detect location. Try specifying a city manually."

    print(f"→ Detected city: {location}")

    graph = build_graph()

    result = graph.invoke({
        "messages": [],
        "question": question,
        "location": location
    })

    return result["messages"][-1]["content"]


# -------------------- CLI --------------------
if __name__ == "__main__":

    # if len(sys.argv) < 2:
    #     print("Usage:\n python weather_AQI_geminic.py \"<question>\" [city]")
    #     sys.exit(1)

    # question = sys.argv[1]
    # city = sys.argv[2] if len(sys.argv) > 2 else None

    # print("\n=== Agent Output ===\n")
    # print(run_agent(question, city))

    print("----Medical Agent----\n")
    print("----Powered by Gemini 2.0 Flash----\n")
    question = input("\nEnter Your Query: ")
    city = input("\nEnter you City(to Auto Detect leave empty): ")

    print("\n---Agent Output---")
    print(run_agent(question,city))
