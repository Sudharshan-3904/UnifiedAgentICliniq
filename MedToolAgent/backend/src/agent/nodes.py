from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from ..config.settings import settings
from ..agent.state import AgentState
from ..tools.base import agent_tools, search_pubmed, fetch_ehr_data, rag_clinical_data
from ..utils.logger import logger
import os
import re

# Initialize Models
llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.AGENT_MODEL)
safety_llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.SAFETY_MODEL)

# Since gemma3 doesn't support tool binding, we'll use a prompt-based approach
TOOL_PROMPT = """You are a medical AI assistant participating in a multi-turn conversation with a user. Use the conversation history to decide whether a tool is needed on a given turn.

You have access to the following tools:

1. search_pubmed(query: str, num_articles: int = 10, top_n: int = 3) - Search PubMed for medical literature and return top relevant articles ranked by semantic similarity
   USE THIS TOOL ONLY WHEN:
   - The user explicitly asks for recent research, studies, or publications
   - The query requires evidence-based medical literature or clinical trials
   - The user needs specific scientific papers or medical research findings
   - The question is about latest treatment guidelines or emerging medical knowledge
   
   DO NOT USE THIS TOOL FOR:
   - General medical knowledge questions that can be answered directly
   - Basic medical definitions or explanations
   - Patient-specific queries (use fetch_ehr_data instead)
   - Clinical guidelines already in your knowledge base (use rag_clinical_data instead)

2. fetch_ehr_data(patient_id: str) - Fetch Electronic Health Records for a patient
   USE THIS TOOL WHEN: The user asks about a specific patient's medical history or records

3. rag_clinical_data(query: str) - Retrieve clinical data from local knowledge base
   USE THIS TOOL WHEN: The user asks about clinical guidelines or protocols that might be in the local database

IMPORTANT: First try to answer the question directly using your medical knowledge. Only use tools when specifically needed for evidence, patient data access, or local knowledge retrieval.

This is a MULTI-TURN conversation. Always consider prior messages when deciding whether to call a tool. If you decide to call a tool, respond with EXACTLY this format on its own line (no extra text):

TOOL_CALL: tool_name("argument")

For example:
TOOL_CALL: search_pubmed("asthma treatment")

Notes:
- If you call a tool, wait for the tool result and then produce your assistant reply based on that result in the next message.
- For `search_pubmed`, you can optionally specify `num_articles` and `top_n` like: search_pubmed("query", num_articles=20, top_n=5)
- If you can answer without external tools, return a direct, concise answer.
"""

def prompt_builder(state: AgentState):
    logger.info("Building prompt...")
    query = state["user_query"]
    # Read a local context file if it exists
    context = ""
    context_file = os.path.join(settings.BASE_DIR, "context.txt")
    if os.path.exists(context_file):
        with open(context_file, "r") as f:
            context = f.read()

    system_message = SystemMessage(content=TOOL_PROMPT)
    user_message = HumanMessage(content=f"User Query: {query}")

    # Merge conversation history if present. Accept either message objects or simple dicts.
    prev_msgs = state.get("messages", []) or []

    normalized_prev = []
    for m in prev_msgs:
        # Normalize both message objects and dicts into canonical message objects
        content = ""
        role = "human"

        if isinstance(m, dict):
            role = m.get("role", "human").lower()
            content = m.get("content", "")
        else:
            # message object, derive role and content
            role = getattr(m.__class__, "__name__", "human").lower()
            content = getattr(m, "content", "")

        if role.startswith("system"):
            normalized_prev.append(SystemMessage(content=content))
        elif role.startswith("ai") or role.startswith("aimessage") or role.startswith("assistant"):
            normalized_prev.append(AIMessage(content=content))
        else:
            normalized_prev.append(HumanMessage(content=content))

    # Build final messages: ensure system message is first
    final_messages = [system_message]
    # Avoid duplicating system messages if already present
    if normalized_prev and isinstance(normalized_prev[0], SystemMessage):
        final_messages = normalized_prev
    else:
        final_messages = [system_message] + normalized_prev

    # Append current user message for this turn
    final_messages = final_messages + [user_message]

    return {"prompt": f"{context}\n\n{query}", "messages": final_messages}

def llm_agent(state: AgentState):
    logger.info("Running LLM Agent...")
    messages = state["messages"]
    
    # Invoke the LLM without tool binding
    response = llm.invoke(messages)
    
    # Check if the response contains a tool call
    tool_call_match = re.search(r'TOOL_CALL:\s*(\w+)\((.*?)\)', response.content)

    if tool_call_match:
        tool_name = tool_call_match.group(1)
        arg_str = tool_call_match.group(2).strip()

        # Extract main quoted argument (e.g., the query) and optional kwargs like num_articles/top_n
        query_arg = None
        quoted = re.search(r'"([^"]+)"|\'([^\']+)\'', arg_str)
        if quoted:
            query_arg = quoted.group(1) or quoted.group(2)

        num_articles = None
        top_n = None
        m = re.search(r'num_articles\s*=\s*(\d+)', arg_str)
        if m:
            num_articles = int(m.group(1))
        m2 = re.search(r'top_n\s*=\s*(\d+)', arg_str)
        if m2:
            top_n = int(m2.group(1))

        logger.info(f"Detected tool call: {tool_name}({arg_str})")

        # Execute the tool (validate required args first)
        tool_result = None
        if tool_name == "search_pubmed":
            if not query_arg:
                logger.warning("search_pubmed called without a query argument")
                tool_result = "Error: search_pubmed requires a query argument. Please call the tool as: TOOL_CALL: search_pubmed(\"your query\")"
            else:
                params = {"query": query_arg}
                if num_articles is not None:
                    params["num_articles"] = num_articles
                if top_n is not None:
                    params["top_n"] = top_n
                tool_result = search_pubmed.invoke(params)
        elif tool_name == "fetch_ehr_data":
            if not query_arg:
                logger.warning("fetch_ehr_data called without a patient_id")
                tool_result = "Error: fetch_ehr_data requires a patient_id. Please call: TOOL_CALL: fetch_ehr_data(\"patient_id\")"
            else:
                tool_result = fetch_ehr_data.invoke({"patient_id": query_arg})
        elif tool_name == "rag_clinical_data":
            if not query_arg:
                logger.warning("rag_clinical_data called without a query")
                tool_result = "Error: rag_clinical_data requires a query. Please call: TOOL_CALL: rag_clinical_data(\"your query\")"
            else:
                tool_result = rag_clinical_data.invoke({"query": query_arg})
        if tool_result:
            # If tool returned an error string (usually due to missing args), don't call LLM; return an assistant-style message so caller sees the issue
            if isinstance(tool_result, str) and tool_result.startswith("Error:"):
                err_msg = AIMessage(content=tool_result)
                new_messages = messages + [response, err_msg]
                return {"messages": new_messages, "generation": tool_result, "tool_used": tool_name}

            # Normal flow: add tool result to messages and invoke LLM again
            tool_message = HumanMessage(content=f"Tool Result: {tool_result}\n\nNow provide a comprehensive answer based on this information.")
            new_messages = messages + [response, tool_message]
            final_response = llm.invoke(new_messages)
            return {"messages": new_messages + [final_response], "generation": final_response.content, "tool_used": tool_name}
    
    return {"messages": messages + [response], "generation": response.content, "tool_used": None}

def refinement_agent(state: AgentState):
    logger.info("Running Refinement Agent...")
    generation = state["generation"]
    query = state["user_query"]
    refinement_count = state.get("refinement_count", 0)
    
    # Limit iterations (e.g., max 3 refinements)
    if refinement_count >= 3:
        logger.info("Max refinement iterations reached.")
        return {"refinement_feedback": None}
        
    # Evaluation prompt
    eval_prompt = f"""
    You are a critical evaluator. Analyze the following AI response to the user's query.
    
    User Query: {query}

    AI Response: {generation}
    
    Does the response directly and accurately answer the query?
    Check for:
    1. Directness: Does it answer the specific question asked?
    2. Completeness: Is any key information missing?
    3. Relevance: Is the information relevant to the query?
    
    If the response is good, reply with "ALIGNED".
    If it needs improvement, reply with "NEEDS_REFINEMENT" followed by specific instructions on how to improve it.
    """
    
    response = llm.invoke(eval_prompt)
    content = response.content
    
    if "ALIGNED" in content:
        logger.info("Response is aligned.")
        return {"refinement_feedback": None}
    else:
        logger.info(f"Response needs refinement: {content}")
        feedback = content.replace("NEEDS_REFINEMENT", "").strip()
        # Add feedback as a new message to guide the agent
        refinement_message = HumanMessage(content=f"Refinement Feedback: {feedback}. Please update your response to address this.")
        return {
            "refinement_count": refinement_count + 1,
            "refinement_feedback": feedback,
            "messages": [refinement_message]
        }

def safety_agent(state: AgentState):
    logger.info("Running Safety Agent...")
    generation = state["generation"]
    
    # Simple safety check prompt
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
    
    return {"safety_report": report, "is_valid": is_valid}

def recovery(state: AgentState):
    logger.info("Running Recovery...")
    retry_count = state.get("retry_count", 0) + 1
    
    # Add a message to the history to guide the agent to fix the issue
    safety_report = state["safety_report"]
    recovery_message = HumanMessage(content=f"The previous response was flagged as unsafe/invalid. Reason: {safety_report}. Please correct it.")
    
    return {"retry_count": retry_count, "messages": [recovery_message]}
