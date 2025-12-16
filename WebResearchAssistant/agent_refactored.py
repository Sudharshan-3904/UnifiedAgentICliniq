"""Refactored Web Research runner using service abstractions (SRP/DI).
"""
from WebResearchAssistant.services import make_services


def run_query(query: str):
    search, scraper = make_services()
    results = search.search(query, max_results=3)
    urls = [r['url'] for r in results]
    scraped = [scraper.extract(u) for u in urls]
    # simple summarization: return first 300 chars of each
    summary = [{"url": s['url'], "snippet": s.get('content','')[:300]} for s in scraped if s.get('success')]
    return {"query": query, "results": results, "summary": summary}


if __name__ == '__main__':
    print(run_query('What is the latest on transformer models?'))
