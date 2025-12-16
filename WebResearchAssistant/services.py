"""Search and scraping service abstractions for the Web Research Assistant.
"""
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
from typing import List, Dict


class SearchService:
    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        ddgs = DDGS()
        results = []
        for r in ddgs.text(query, max_results=max_results):
            results.append({"title": r.get("title", "No title"), "url": r.get("href", ""), "snippet": r.get("body", "")})
        return results


class ScraperService:
    def extract(self, url: str) -> Dict:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                paragraphs = main_content.find_all('p')
                text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                text = text[:3000] if len(text) > 3000 else text
                return {"url": url, "content": text, "success": True}
            return {"url": url, "content": "", "success": False}
        except Exception as e:
            return {"url": url, "content": "", "success": False, "error": str(e)}


def make_services():
    return SearchService(), ScraperService()
