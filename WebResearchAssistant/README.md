# WebResearchAssistant

Lightweight Web Research Assistant that performs a search, scrapes selected pages, extracts main content, and synthesizes a concise summary using an LLM (configured to use an Ollama-compatible endpoint by default).

## Key files

-   `main.py`: entry point and implementation. Implements a small LangGraph-style pipeline:
    -   `SearchNode` — performs a web search (prefers `duckduckgo-search` package, falls back to SerpAPI if configured, then HTML DuckDuckGo scraping)
    -   `SelectScrapeNode` — heuristic selector that chooses which search results to scrape
    -   `ScrapeNode` — concurrent page fetch + content extraction (uses readability)
    -   `SynthesizeNode` — builds a prompt with per-source excerpts and calls the LLM (Ollama) to synthesize a short answer with evidence bullets

## Quick start

1. Create and activate a Python virtualenv (recommended):

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```pwsh
python -m pip install -r requirements.txt
```

3. Run a quick CLI query:

```pwsh
python main.py
```

## Execution flow

-   Input: a user query (CLI or HTTP POST)
-   Search: `SearchNode` produces `state['search_results']` (list of dicts: `title`, `link`, `snippet`)
-   Selection: `SelectScrapeNode` writes `state['to_scrape']` (subset of results)
-   Scraping: `ScrapeNode` fetches pages concurrently and writes `state['scraped_sources']` with `text` and `resolved_link` fields
-   Synthesis: `SynthesizeNode` builds a prompt from scraped content and sends it to the configured LLM; result goes into `state['summary']`
