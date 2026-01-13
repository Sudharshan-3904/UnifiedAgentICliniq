# routine_run.py
import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
import re
from datetime import datetime

# File locations and their purpose
MD_FILE_STORAGE = "md_files"
CSV_STATUS_FILE = r"data\update_progress.csv"
JSON_METADATA_FILE = r"data\url_tracker.json"
SCRAPING_LINKS_DIR = "scrap_links_src"

os.makedirs(MD_FILE_STORAGE, exist_ok=True)

scraper = cloudscraper.create_scraper()

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
                # print(f"Skipping already extracted URL: {link_value}")
                continue
            
            result.append([int(id_value), link_value])
            updated_rows.append(row)
    
    return result, updated_rows

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)

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

def extract_from_medline(soup, url, article_id):
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    # MedlinePlus specific content root
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
        return None

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
        return None

    data["extracted_date"] = datetime.now()
    return data

def extract_from_ncbi_articles(soup, url, article_id):
    # Specific DOM path for /articles
    # article -> section aria-label="Article content" -> section class="body main-article-body"
    content_root = None
    article_tag = soup.find("article")
    if article_tag:
        article_content_section = article_tag.find("section", attrs={"aria-label": "Article content"})
        if article_content_section:
            content_root = article_content_section.find("section", class_="body main-article-body")

    if not content_root:
        print(f"Main content container (article -> section[aria-label='Article content'] -> section.body.main-article-body) not found for {url}")
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    sections = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in sections:
        # Skip reference lists and other non-content machinery
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

    if not data["sections"]:
        print(f"No structured content extracted for {url}")
        return None

    data["extracted_date"] = datetime.now()
    return data

def extract_from_ncbi(soup, url, article_id):
    content_root = soup.select_one("div.main-content.lit-style")
    if not content_root:
        content_root = soup.find("div", class_="document")
    
    if not content_root:
        print(f"Main content container (div.main-content.lit-style or div.document) not found for {url}")
        return None

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
    
    sections = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in sections:
        # Skip reference lists and other non-content machinery
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

    if not data["sections"]:
        print(f"No structured content extracted for {url}")
        return None

    data["extracted_date"] = datetime.now()
    return data

def save_markdown(article_id, title, url, data):
    # Extract the last part of the URL (filename candidate)
    raw_filename = url.split('/')[-1]
    # Remove query parameters if present
    if '?' in raw_filename:
        raw_filename = raw_filename.split('?')[0]
        
    sanitized_name = sanitize_filename(raw_filename)
    markdown_filename = f"{article_id}_{sanitized_name}.md"
    markdown_filepath = os.path.join(STORAGE_DIR, markdown_filename)

    # Avoid repetition: if the file already exists, do not overwrite
    if os.path.exists(markdown_filepath):
        print(f"Markdown file already exists, skipping save: {markdown_filepath}")
        return 'skipped'
    
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
    return 'saved' 


def write_status_csv(file_path, rows):
    """Write the canonical status CSV with only id, link, status, extracted_date columns (overwrite)."""
    fieldnames = ['id', 'link', 'status', 'extracted_date']
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({'id': r.get('id'), 'link': r.get('link'), 'status': r.get('status', ''), 'extracted_date': r.get('extracted_date', '')})
    print(f"CSV file updated successfully: {file_path}")

def append_updates_file(updates_file, updates_rows):
    """Append update rows (may contain extra columns) to a separate updates CSV."""
    if not updates_rows:
        return
    fieldnames = ['id', 'link', 'status', 'status_code', 'status_abbreviation', 'note', 'extracted_date']
    exists = os.path.exists(updates_file)
    with open(updates_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for u in updates_rows:
            writer.writerow({
                'id': u.get('id'),
                'link': u.get('link'),
                'status': u.get('status', ''),
                'status_code': u.get('status_code', ''),
                'status_abbreviation': u.get('status_abbreviation', ''),
                'note': u.get('note', '')
            })
    print(f"Appended {len(updates_rows)} updates to {updates_file}")


if __name__ == "__main__":
    formatted_data, updated_rows = convert_csv_to_list(CSV_STATUS_FILE)

    BATCH_SIZE = 10
    count = 0

    UPDATES_FILE = r"data\url_status_updates.csv"
    pending_updates = []

    # existing markdown files to help detect duplicates
    existing_files = set(os.listdir(STORAGE_DIR))

    for article_id, url in formatted_data:
        # Fetch and perform centralized error/status checks
        try:
            response = scraper.get(url, headers=get_headers(), timeout=30)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            # mark as failed in updated_rows and queue update
            for row in updated_rows:
                if row['link'] == url:
                    row['status'] = 'failed'
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'status': row['status'], 'note': str(e)})
                    break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        if response.status_code != 200:
            print(f"Failed to fetch {url} (Status: {response.status_code})")
            for row in updated_rows:
                if row['link'] == url:
                    row['status'] = 'failed'
                    row['status_code'] = response.status_code
                    row['status_abbreviation'] = getattr(response, 'reason', '')
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'status': row['status'], 'status_code': response.status_code, 'status_abbreviation': getattr(response, 'reason', '')})
                    break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        data = None
        if "medlineplus.gov" in url:
            data = extract_from_medline(soup, url, article_id)
        elif "ncbi.nlm.nih.gov" in url:
            if "/articles" in url:
                data = extract_from_ncbi_articles(soup, url, article_id)
            else:
                data = extract_from_ncbi(soup, url, article_id)
        else:
            print(f"No specific extractor for URL: {url}, attempting default Medline extractor.")
            data = extract_from_medline(soup, url, article_id)

        if data is None:
            # extraction failed
            for row in updated_rows:
                if row['link'] == url:
                    row['status'] = 'failed'
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'status': row['status'], 'note': 'extraction_failed'})
                    break
        else:
            # Try saving; save_markdown returns 'saved' or 'skipped'
            save_result = save_markdown(article_id, data['title'], url, data)
            if save_result in ('saved', 'skipped'):
                # mark as extracted to avoid reprocessing even if we skipped due to duplicate
                for row in updated_rows:
                    if row['link'] == url:
                        row['status'] = 'extracted'
                        pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'status': row['status']})
                        break
                # update existing files set if new file was created
                if save_result == 'saved':
                    existing_files.add(f"{article_id}_{sanitize_filename(url.split('/')[-1].split('?')[0])}.md")
            else:
                for row in updated_rows:
                    if row['link'] == url:
                        row['status'] = 'failed'
                        pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'status': row['status'], 'note': 'save_failed'})
                        break

        count += 1
        if count % BATCH_SIZE == 0:
            write_status_csv(CSV_STATUS_FILE, updated_rows)
            append_updates_file(UPDATES_FILE, pending_updates)
            pending_updates = []
            print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")

    # Final save to ensure any remaining records are updated
    write_status_csv(CSV_STATUS_FILE, updated_rows)
    append_updates_file(UPDATES_FILE, pending_updates)
    print("Final CSV update completed.")
