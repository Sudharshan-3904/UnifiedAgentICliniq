import requests
from bs4 import BeautifulSoup
import csv
import json
import os
import re

STORAGE_DIR = "md_files"
os.makedirs(STORAGE_DIR, exist_ok=True)

CSV_FILE = r"data\url_status.csv"


def convert_csv_to_list(input_file):
    result = []
    updated_rows = []

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            id_value = row['id']
            link_value = row['link']
            status_value = row['status']

            if status_value.lower() == 'extracted':
                print(f"Skipping already extracted URL: {link_value}")
                continue
            
            result.append([int(id_value), link_value])
            updated_rows.append(row)
    
    return result, updated_rows


def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)


def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

def extract_from_medline(url, article_id, updated_rows):
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return False
    
    if response.status_code != 200:
        print(f"Failed to fetch {url} (Status: {response.status_code})")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    # MedlinePlus specific content root
    # Usually it's in <article> or <div id="mplus-content"> or similar, but keeping original logic as a base
    # removing generic fallbacks that might be NCBI specific if we want strict separation, 
    # but for safety I will leave the broader search but prioritize Medline structure if known.
    # The original code searched article -> main -> jig-ncbi-inpagenav -> #maincontent
    
    content_root = soup.find("article")
    if not content_root:
        content_root = soup.find("main")
    if not content_root:
        content_root = soup.find(id="maincontent") # Common in MedlinePlus
    
    if not content_root:
        # Fallback to the original broad search just in case
        content_root = soup.find(class_="jig-ncbi-inpagenav")

    if not content_root:
        print(f"Main content container not found for {url}")
        return False

    sections = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    # MedlinePlus abstract check
    abstract_div = soup.select_one(".abstract, #abstract, .abstract-content")
    if abstract_div:
        data["sections"].append({
            "section_title": "Abstract",
            "content": [{"type": "paragraph", "text": abstract_div.get_text(strip=True)}]
        })

    for elem in sections:
        if elem.find_parent(class_=["ref-list", "ack", "app-group", "fn-group"]):
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
        data["sections"].append(current_section)

    if not data["sections"]:
        print(f"No structured content extracted for {url}")
        return False

    save_markdown(article_id, title, url, data)
    
    for row in updated_rows:
        if row['link'] == url:
            row['status'] = 'extracted'
            break
    
    return True

def extract_from_ncbi(url, article_id, updated_rows):
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return False
    
    if response.status_code != 200:
        print(f"Failed to fetch {url} (Status: {response.status_code})")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    # User requested specifically: div.main-content lit-style
    # We also keep div.document as fallback or alternative
    content_root = soup.select_one("div.main-content.lit-style")
    
    if not content_root:
        content_root = soup.find("div", class_="document")
    
    if not content_root:
        print(f"Main content container (div.main-content.lit-style or div.document) not found for {url}")
        return False

    title_tag = soup.find("h1")
    if not title_tag:
        title_tag = content_root.find("h1")
        
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    # Extract clean text sections from the specialized root
    # Note: Structure might be flat or nested. We iterate through likely content tags.
    # Looking for direct children or general flow?
    # BS4 extract loop similar to medline
    
    sections = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in sections:
        # Skip reference lists and other non-content machinery
        if elem.find_parent(class_=["ref-list", "ack", "app-group", "fn-group", "back", "reflist"]):
            continue
        
        # Skip if element is inside a table wrapper for now if complicated, but p/ul usually ok.
        
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

    if not data["sections"]:
        print(f"No structured content extracted for {url}")
        return False

    save_markdown(article_id, title, url, data)

    for row in updated_rows:
        if row['link'] == url:
            row['status'] = 'extracted'
            break

    return True

def save_markdown(article_id, title, url, data):
    markdown_filename = f"{article_id}_{sanitize_filename(title)}.md"
    markdown_filepath = os.path.join(STORAGE_DIR, markdown_filename)
    
    with open(markdown_filepath, 'w', encoding='utf-8') as md_file:
        md_file.write(f"# {title}\n\n")
        md_file.write(f"URL: {url}\n\n")
        md_file.write("---\n\n")

        for section in data["sections"]:
            md_file.write(f"## {section['section_title']}\n\n")

            for content in section["content"]:
                if content["type"] == "paragraph":
                    md_file.write(f"{content['text']}\n\n")
                elif content["type"] == "list":
                    for item in content["items"]:
                        md_file.write(f"- {item}\n")

    print(f"Markdown file saved as: {markdown_filepath}")


if __name__ == "__main__":
    formatted_data, updated_rows = convert_csv_to_list(CSV_FILE)

    for article_id, url in formatted_data:
        if "medlineplus.gov" in url:
            extract_from_medline(url, article_id, updated_rows)
        elif "ncbi.nlm.nih.gov" in url:
            extract_from_ncbi(url, article_id, updated_rows)
        else:
            print(f"No specific extractor for URL: {url}, attempting default Medline extractor.")
            extract_from_medline(url, article_id, updated_rows)

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'link', 'status']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(updated_rows)

    print("CSV file updated successfully.")
