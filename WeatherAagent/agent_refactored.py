"""Refactored runner using service abstractions (SRP, DI).

This is a compact entrypoint demonstrating how the agent depends on
well-scoped services rather than monolithic functions.
"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from WeatherAagent.services import make_services


class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    question: str
    location: str


def agent_node_factory(weather_service, llm):
    def agent_node(state: AgentState):
        messages = state["messages"]

        if len(messages) == 0:
            weather = weather_service.fetch_weather(state["location"])
            messages.append({"role": "tool", "result": weather})
            return state | {"messages": messages, "next": "agent"}

        last = messages[-1]
        if last["role"] == "tool":
            weather = last["result"]
            prompt = f"""
You are a medical assistant.
Explain how these weather + AQI conditions can worsen the Condition and give me some precautions.
Do NOT diagnose or give medication instructions.

Weather:
{json.dumps(weather, indent=2)}

User question:
{state['question']}
"""
            response = llm.run(prompt)
            messages.append({"role": "assistant", "content": response})
            return state | {"messages": messages, "next": "END"}

        return state | {"messages": messages, "next": "END"}

    return agent_node


def build_graph(weather_service, llm):
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node_factory(weather_service, llm))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", lambda out: out["next"], {"agent": "agent", "END": END})
    return graph.compile()


def run_agent(question, location=None):
    weather_service, llm = make_services()
    if not location:
        return "Location required for this demo"

    graph = build_graph(weather_service, llm)
    result = graph.invoke({"messages": [], "question": question, "location": location})
    return result["messages"][-1]["content"]


if __name__ == '__main__':
    import json
    print(run_agent('How does weather affect asthma?', 'San Francisco'))
