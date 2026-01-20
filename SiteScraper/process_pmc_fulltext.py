import sys
import cloudscraper
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from datetime import datetime
import json
import os
import hashlib

MD_FILE_STORAGE = "md_files"

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)


def save_markdown(article_id, title, url, data):
    os.makedirs(MD_FILE_STORAGE, exist_ok=True)

    raw_filename = url.split('/')[-1] or ''
    if '?' in raw_filename:
        raw_filename = raw_filename.split('?')[0]

    sanitized_name = sanitize_filename(raw_filename) or sanitize_filename(title)[:50]
    # If article_id is None, extraction failed, so we use a timestamp or placeholder
    aid = article_id if article_id else "manual"
    base_name = f"{aid}_{sanitized_name}"
    markdown_filename = f"{base_name}.md"
    markdown_filepath = os.path.join(MD_FILE_STORAGE, markdown_filename)

    lines = []
    lines.append(f"# {title}\n")
    lines.append(f"URL: {url}\n")
    lines.append("---\n")

    for section in data.get("sections", []):
        lines.append(f"## {section['section_title']}\n")
        for content in section.get("content", []):
            if content.get("type") == "paragraph":
                lines.append(f"{content.get('text')}\n")
            elif content.get("type") == "list":
                for item in content.get("items", []):
                    lines.append(f"- {item}\n")

    content = "\n".join(lines)

    suffix = 1
    # Check for duplicate content (optional optimization from routine_run)
    while os.path.exists(markdown_filepath):
        try:
            with open(markdown_filepath, 'r', encoding='utf-8') as f:
                existing = f.read()
        except Exception:
            pass
        markdown_filename = f"{base_name}_{suffix}.md"
        markdown_filepath = os.path.join(MD_FILE_STORAGE, markdown_filename)
        suffix += 1

    with open(markdown_filepath, 'w', encoding='utf-8') as md_file:
        md_file.write(content)

    print(f"Markdown file saved as: {markdown_filepath}")
    return 'saved', markdown_filepath

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }

def extract_article_content(soup, url):
    """
    Extracts article content based on logic in routine_run.py, 
    specifically targeting NCBI/PMC article structures.
    """
    content_root = None
    
    article_tag = soup.find("article")
    if article_tag:
        article_content_section = article_tag.find("section", attrs={"aria-label": "Article content"})
        if article_content_section:
            content_root = article_content_section.find("section", class_="body main-article-body")
    
    if not content_root:
        content_root = soup.select_one("div.main-content.lit-style")
    if not content_root:
        content_root = soup.find("div", class_="document")
    if not content_root:
         content_root = soup.find("main")
         
    if not content_root:
        return {"error": "Main content container not found"}

    title_tag = soup.find("h1")
    if not title_tag and content_root:
        title_tag = content_root.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "title": title,
        "url": url,
        "sections": [],
        "extracted_date": datetime.now().isoformat()
    }

    # Extract sections (H2, H3, P, UL)
    sections = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in sections:
        # Skip references and acknowledgments often found at the bottom
        if elem.find_parent(class_=["ref-list", "ack", "app-group", "fn-group", "back", "reflist"]):
            continue
        
        if elem.name in ["h2", "h3"]:
            if current_section:
                data["sections"].append(current_section)

            section_title = elem.get_text(strip=True)
            current_section = {
                "section_title": section_title,
                "content": []
            }
        
        elif elem.name == "p":
            paragraph_text = elem.get_text(strip=True)
            if paragraph_text: 
                if current_section is None:
                    current_section = {"section_title": "Introduction", "content": []}
                
                current_section["content"].append({
                    "type": "paragraph",
                    "text": paragraph_text
                })

        elif elem.name == "ul":
            list_items = [li.get_text(strip=True) for li in elem.find_all("li")]
            if list_items:
                if current_section is None:
                    current_section = {"section_title": "Introduction", "content": []}
                
                current_section["content"].append({
                    "type": "list",
                    "items": list_items
                })
    
    if current_section:
        if current_section not in data["sections"]:
            data["sections"].append(current_section)
            
    return data

def process_url(url):
    scraper = cloudscraper.create_scraper()
    try:
        print(f"Fetching initial URL: {url}...")
        res = scraper.get(url, headers=get_headers())
        if res.status_code != 200:
            print(f"Error fetching URL: {res.status_code}")
            return

        soup = BeautifulSoup(res.content, 'html.parser')

        # Check for PMC Full Text link
        pmc_link = soup.select_one("a.link-item.pmc")
        
        target_url = url
        if pmc_link and pmc_link.get('href'):
            rel_href = pmc_link.get('href')
            target_url = urljoin(url, rel_href)
            print(f"Found PMC Full Text link. Redirecting scraping to: {target_url}")
            

            res = scraper.get(target_url, headers=get_headers())
            if res.status_code != 200:
                 print(f"Error fetching target URL: {res.status_code}")
                 return
            soup = BeautifulSoup(res.content, 'html.parser')
        else:
            print("PMC Full Text link (a.link-item.pmc) not found. Attempting to scrape current page.")


        data = extract_article_content(soup, target_url)

        if "error" in data:
            print(f"Extraction failed: {data['error']}")
            return

        article_id = None
        match = re.search(r'/(\d+)/?$', url)
        if match:
            article_id = match.group(1)
        

        save_markdown(article_id, data['title'], target_url, data)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_url = sys.argv[1]
        process_url(input_url)
    else:
        print("Please provide a URL as an argument.")
        print("Usage: python process_pmc_fulltext.py <url>")
