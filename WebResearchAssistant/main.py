from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import operator
import time

# Define the agent state
class AgentState(TypedDict):
    query: str
    search_results: List[dict]
    selected_urls: List[str]
    scraped_content: Annotated[list, operator.add]
    final_answer: str
    max_results: int

# Tool 1: Search Tool
def search_web(query: str, max_results: int = 3) -> List[dict]:
    """
    Search the web using DuckDuckGo and return URLs with titles
    """
    print(f"🔍 Searching for: {query}")
    
    try:
        ddgs = DDGS()
        results = []
        
        # Perform search and get top results
        search_results = ddgs.text(query, max_results=max_results)
        
        for result in search_results:
            results.append({
                "title": result.get("title", "No title"),
                "url": result.get("href", ""),
                "snippet": result.get("body", "")
            })
        
        print(f"✅ Found {len(results)} results")
        return results
    
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []

# Tool 2: Content Extraction Tool
def extract_content(url: str) -> dict:
    """
    Extract main content from a URL using BeautifulSoup
    """
    print(f"📄 Scraping: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find main content
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        
        if main_content:
            # Get all paragraphs
            paragraphs = main_content.find_all('p')
            text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Limit content length
            text = text[:3000] if len(text) > 3000 else text
            
            print(f"✅ Extracted {len(text)} characters")
            return {
                "url": url,
                "content": text,
                "success": True
            }
        else:
            return {"url": url, "content": "", "success": False}
    
    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return {"url": url, "content": "", "success": False, "error": str(e)}

# Initialize Ollama LLM
llm = ChatOllama(
    model="gemma3:latest",
    temperature=0.3
)

# Node 1: Perform Search
def perform_search(state: AgentState) -> AgentState:
    """Search the web for relevant URLs"""
    
    query = state["query"]
    max_results = state.get("max_results", 3)
    
    search_results = search_web(query, max_results)
    
    return {
        "query": query,
        "search_results": search_results,
        "selected_urls": [],
        "scraped_content": [],
        "final_answer": "",
        "max_results": max_results
    }

# Node 2: Select URLs to scrape
def select_urls(state: AgentState) -> AgentState:
    """Select which URLs to scrape based on search results"""
    
    # Simple strategy: select top N URLs
    urls = [result["url"] for result in state["search_results"][:state["max_results"]]]
    
    print(f"\n📋 Selected {len(urls)} URLs to scrape")
    
    return {
        "query": state["query"],
        "search_results": state["search_results"],
        "selected_urls": urls,
        "scraped_content": [],
        "final_answer": "",
        "max_results": state["max_results"]
    }

# Node 3: Extract content from URLs
def extract_content_from_urls(state: AgentState) -> AgentState:
    """Scrape content from selected URLs"""
    
    scraped_content = []
    
    for url in state["selected_urls"]:
        content = extract_content(url)
        if content["success"]:
            scraped_content.append(content)
        time.sleep(1)  # Be polite, don't hammer servers
    
    print(f"\n✅ Successfully scraped {len(scraped_content)} pages")
    
    return {
        "query": state["query"],
        "search_results": state["search_results"],
        "selected_urls": state["selected_urls"],
        "scraped_content": scraped_content,
        "final_answer": "",
        "max_results": state["max_results"]
    }

# Node 4: Generate final answer using LLM
def generate_answer(state: AgentState) -> AgentState:
    """Use LLM to process scraped content and answer the query"""
    
    print("\n🤖 Generating answer with LLM...")
    
    # Prepare context from scraped content
    context = "\n\n".join([
        f"Source: {item['url']}\n{item['content'][:1000]}"
        for item in state["scraped_content"]
    ])
    
    if not context:
        return {
            "query": state["query"],
            "search_results": state["search_results"],
            "selected_urls": state["selected_urls"],
            "scraped_content": state["scraped_content"],
            "final_answer": "I couldn't extract enough content to answer your question.",
            "max_results": state["max_results"]
        }
    
    system_msg = SystemMessage(content="""You are a helpful research assistant. 
    Based on the provided web content, answer the user's question accurately and concisely.
    Cite sources when possible. If the content doesn't contain the answer, say so.""")
    
    user_msg = HumanMessage(content=f"""Question: {state['query']}

Web Content:
{context}

Please provide a clear and accurate answer based on the above content.""")
    
    response = llm.invoke([system_msg, user_msg])
    
    return {
        "query": state["query"],
        "search_results": state["search_results"],
        "selected_urls": state["selected_urls"],
        "scraped_content": state["scraped_content"],
        "final_answer": response.content,
        "max_results": state["max_results"]
    }

# Conditional edge function
def should_continue_scraping(state: AgentState) -> str:
    """Decide whether to scrape content or end"""
    if state["selected_urls"]:
        return "scrape"
    else:
        return "answer"

# Build the LangGraph workflow
def create_research_agent():
    """Create the complete research agent workflow"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("search", perform_search)
    workflow.add_node("select", select_urls)
    workflow.add_node("scrape", extract_content_from_urls)
    workflow.add_node("answer", generate_answer)
    
    # Add edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "select")
    
    # Conditional edge after selection
    workflow.add_conditional_edges(
        "select",
        should_continue_scraping,
        {
            "scrape": "scrape",
            "answer": "answer"
        }
    )
    
    workflow.add_edge("scrape", "answer")
    workflow.add_edge("answer", END)
    
    return workflow.compile()

# Main function
def main():
    print("🌐 LangGraph Web Research Agent")
    print("=" * 60)
    print("Ask me anything and I'll search, scrape, and analyze!")
    print("Type 'quit' to exit\n")
    
    app = create_research_agent()
    
    while True:
        query = input("Your question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye! 👋")
            break
        
        if not query:
            continue
        
        # Create initial state
        initial_state = {
            "query": query,
            "search_results": [],
            "selected_urls": [],
            "scraped_content": [],
            "final_answer": "",
            "max_results": 3  # Number of URLs to scrape
        }
        
        print("\n" + "=" * 60)
        
        try:
            # Run the agent
            final_state = app.invoke(initial_state)
            
            # Display results
            print("\n" + "=" * 60)
            print("📊 RESULTS")
            print("=" * 60)
            print(f"\n🔍 Search Results Found: {len(final_state['search_results'])}")
            for i, result in enumerate(final_state['search_results'], 1):
                print(f"  {i}. {result['title']}")
                print(f"     {result['url']}")
            
            print(f"\n📄 Pages Scraped: {len(final_state['scraped_content'])}")
            
            print("\n💡 ANSWER:")
            print("-" * 60)
            print(final_state['final_answer'])
            print("=" * 60 + "\n")
        
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()