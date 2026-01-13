import cloudscraper
import requests
from bs4 import BeautifulSoup
import csv
import json
import os
import re
import io
import PyPDF2

STORAGE_DIR = "md_files"
os.makedirs(STORAGE_DIR, exist_ok=True)

CSV_FILE = r"data\failed.csv"

# Initialize cloudscraper
scraper = cloudscraper.create_scraper()

def convert_csv_to_list(input_file):
    result = []
    updated_rows = []

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            id_value = row['id']
            link_value = row['link']
            status_value = row['status']
            
            # Ensure last_updated key exists
            if 'last_updated' not in row:
                row['last_updated'] = 'N/A'

            if status_value.lower() == 'extracted':
                # print(f"Skipping already extracted URL: {link_value}")
                updated_rows.append(row)
                continue
            
            result.append([int(id_value), link_value])
            updated_rows.append(row)
    
    return result, updated_rows, fieldnames


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

def extract_date(soup, url):
    """Extract last updated/published/reviewed date based on the URL domain."""
    date_str = "N/A"
    
    # Try generic meta tags first as they are often very reliable for medical/academic articles
    meta_date = (
        soup.find("meta", {"name": "citation_publication_date"}) or 
        soup.find("meta", {"name": "citation_date"}) or 
        soup.find("meta", {"name": "DC.Date.Modified"}) or
        soup.find("meta", {"name": "dc.date"}) or
        soup.find("meta", {"property": "article:modified_time"}) or
        soup.find("meta", {"property": "og:updated_time"})
    )
    if meta_date:
        date_str = meta_date.get("content", "N/A")
        if date_str and date_str != "N/A":
            return date_str

    if "medlineplus.gov" in url:
        # MedlinePlus uses span#lastupdate
        date_tag = soup.find("span", id="lastupdate")
        if date_tag:
            date_str = date_tag.get_text(strip=True).replace("Last updated ", "").replace("Last updated: ", "")
    
    elif "ncbi.nlm.nih.gov/pmc/articles" in url or "pmc.ncbi.nlm.nih.gov/articles" in url:
        # PMC Articles
        date_tag = soup.select_one(".reporting-year, .article-source-item, .fm-update-date, .article-meta span.date, .pmc-layout__citation")
        if date_tag:
            text = date_tag.get_text(strip=True)
            # Look for year patterns like 2023 or 2023 Jan
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                # Try to capture more context if it looks like a citation (e.g. "2018 Jun")
                extended_match = re.search(r'\b\d{4}\s+[A-Z][a-z]{2}\b', text)
                if extended_match:
                    date_str = extended_match.group(0)
                else:
                    date_str = match.group(0)

    elif "ncbi.nlm.nih.gov/books" in url:
        # NCBI Bookshelf
        date_tag = soup.select_one("span.publish-date")
        if not date_tag:
            small_p = soup.find("p", class_="small")
            if small_p:
                text = small_p.get_text(strip=True)
                if "Last Update:" in text:
                    match = re.search(r"Last Update:\s*([^;.]+)", text)
                    if match:
                        date_str = match.group(1).strip()
        else:
            date_str = date_tag.get_text(strip=True)

    elif "pubmed.ncbi.nlm.nih.gov" in url:
        # PubMed
        date_tag = soup.select_one(".cit, .chapter-contribution-date-value, time")
        if date_tag:
            date_str = date_tag.get_text(strip=True)
            
    elif "rarediseases.info.nih.gov" in url:
        # GARD
        date_tag = soup.select_one("app-bottom-sources-date-information p.text-xl-end")
        if date_tag:
            date_str = date_tag.get_text(strip=True).replace("Last Updated:", "").strip()
            
    elif "genome.gov" in url:
        # Genome.gov
        date_tag = soup.select_one(".last-updated p")
        if date_tag:
            date_str = date_tag.get_text(strip=True).replace("Last updated:", "").strip()

    return date_str

def extract_from_pdf(url, article_id, updated_rows):
    try:
        response = scraper.get(url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            print(f"Failed to fetch PDF {url} (Status: {response.status_code})")
            return False
            
        pdf_file = io.BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        
        title = url.split('/')[-1].replace('.pdf', '')
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        data = {
            "id": article_id,
            "title": title,
            "url": url,
            "sections": [
                {
                    "section_title": "Full PDF Content",
                    "content": [{"type": "paragraph", "text": text.strip()}]
                }
            ]
        }
        
        save_markdown(article_id, title, url, data)
        
        for row in updated_rows:
            if row['link'] == url:
                row['status'] = 'extracted (PDF)'
                row['last_updated'] = 'N/A'
                break
        return True
    except Exception as e:
        print(f"Error extracting PDF {url}: {e}")
        return False

def extract_from_pubmed(url, article_id, updated_rows):
    try:
        response = scraper.get(url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            print(f"Failed to fetch {url} (Status: {response.status_code})")
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.select_one("h1.heading-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown_PubMed_Title"
        
        last_updated = extract_date(soup, url)
        
        data = {
            "id": article_id,
            "title": title,
            "url": url,
            "sections": []
        }
        
        # Abstract is usually the main thing
        abstract_div = soup.select_one("#abstract")
        if abstract_div:
            # PubMed abstracts often have structured sub-sections
            abstract_subsections = abstract_div.find_all("p")
            if not abstract_subsections:
                # Fallback to pure text
                abstract_text = abstract_div.get_text(strip=True)
                data["sections"].append({
                    "section_title": "Abstract",
                    "content": [{"type": "paragraph", "text": abstract_text}]
                })
            else:
                for p_idx, p in enumerate(abstract_subsections):
                    strong = p.find("strong")
                    sec_title = strong.get_text(strip=True) if strong else f"Section {p_idx+1}"
                    p_text = p.get_text(strip=True).replace(sec_title, "", 1).strip()
                    data["sections"].append({
                        "section_title": sec_title if sec_title else "Abstract",
                        "content": [{"type": "paragraph", "text": p_text if p_text else p.get_text(strip=True)}]
                    })
        
        if not data["sections"]:
            # Fallback for full view or other content
            article_details = soup.select_one("#article-details")
            if article_details:
                text = article_details.get_text(separator="\n", strip=True)
                data["sections"].append({
                    "section_title": "Article Details",
                    "content": [{"type": "paragraph", "text": text}]
                })

        if not data["sections"]:
            return False

        save_markdown(article_id, title, url, data)
        for row in updated_rows:
            if row['link'] == url:
                row['status'] = 'extracted'
                row['last_updated'] = last_updated
                break
        return True
    except Exception as e:
        print(f"Error extracting PubMed {url}: {e}")
        return False

def extract_from_medline(url, article_id, updated_rows):
    try:
        # Use scraper instead of requests
        response = scraper.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return False
    
    if response.status_code != 200:
        print(f"Failed to fetch {url} (Status: {response.status_code})")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"
    
    last_updated = extract_date(soup, url)

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    # MedlinePlus specific content root or common fallbacks for other domains
    content_root = soup.find("article")
    if not content_root:
        content_root = soup.find("main")
    if not content_root:
        content_root = soup.find(id="maincontent") # Common in MedlinePlus and NCBI MedGen
    if not content_root:
        content_root = soup.find(id="main-content") # Common in Genome.gov
    if not content_root:
        content_root = soup.find(id="disease") # Common in rarediseases.info.nih.gov
    if not content_root:
        content_root = soup.find("app-disease-about") # Fallback for GARD
    
    if not content_root:
        # Fallback to the original broad search just in case
        content_root = soup.find(class_="jig-ncbi-inpagenav")

    if not content_root:
        print(f"Main content container not found for {url}")
        return False

    sections = content_root.find_all(["h1", "h2", "h3", "h4", "p", "ul", "div", "dd", "dt"])
    current_section = None

    # MedlinePlus abstract check
    abstract_div = soup.select_one(".abstract, #abstract, .abstract-content")
    if abstract_div:
        data["sections"].append({
            "section_title": "Abstract",
            "content": [{"type": "paragraph", "text": abstract_div.get_text(strip=True)}]
        })

    for elem in sections:
        if elem.find_parent(class_=["ref-list", "ack", "app-group", "fn-group", "back", "reflist"]):
            continue

        if elem.name in ["h1", "h2", "h3", "h4"]:
            if current_section and current_section["content"]:
                data["sections"].append(current_section)

            section_title = elem.get_text(strip=True)
            if not section_title: continue
            current_section = {
                "section_title": section_title,
                "content": []
            }
        
        elif elem.name in ["p", "div", "dd"]:
            # Only treat div as paragraph if it has direct text or significant text content and no children headings
            if elem.name == "div" and (elem.find(["h1", "h2", "h3", "h4", "p"])):
                continue
                
            paragraph_text = elem.get_text(strip=True)
            if paragraph_text and len(paragraph_text) > 20: # Filter out noise
                if current_section is None:
                    current_section = {"section_title": "Introduction", "content": []}
                
                # Avoid duplicates
                if not any(c.get("text") == paragraph_text for c in current_section["content"]):
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

    if current_section and current_section["content"]:
        data["sections"].append(current_section)

    if not data["sections"]:
        # Ultimate fallback: Get all text from content_root if no structure found
        print(f"No structured content extracted for {url}, attempting grab-all fallback.")
        all_text = content_root.get_text(separator="\n\n", strip=True)
        if all_text:
            data["sections"].append({
                "section_title": "Main Content",
                "content": [{"type": "paragraph", "text": all_text}]
            })
    
    if not data["sections"]:
        print(f"Completely failed to extract content for {url}")
        return False

    save_markdown(article_id, title, url, data)
    
    for row in updated_rows:
        if row['link'] == url:
            row['status'] = 'extracted'
            row['last_updated'] = last_updated
            break
    
    return True

def extract_from_ncbi_articles(url, article_id, updated_rows):
    try:
        # Use scraper instead of requests
        response = scraper.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return False
    
    if response.status_code != 200:
        print(f"Failed to fetch {url} (Status: {response.status_code})")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

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
        return False

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    last_updated = extract_date(soup, url)

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
        return False

    save_markdown(article_id, title, url, data)

    for row in updated_rows:
        if row['link'] == url:
            row['status'] = 'extracted'
            row['last_updated'] = last_updated
            break

    return True

def extract_from_ncbi(url, article_id, updated_rows):
    try:
        # Use scraper instead of requests
        response = scraper.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return False
    
    if response.status_code != 200:
        print(f"Failed to fetch {url} (Status: {response.status_code})")
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    # User requested specifically: div.main-content lit-style
    # We also keep div.document and #maincontent as fallbacks
    content_root = soup.select_one("div.main-content.lit-style")
    
    if not content_root:
        content_root = soup.find("div", class_="document")
    
    if not content_root:
        content_root = soup.find(id="maincontent") # Often used in MedGen
    
    if not content_root:
        print(f"Main content container (div.main-content.lit-style, div.document, or #maincontent) not found for {url}")
        return False

    title_tag = soup.find("h1")
    if not title_tag:
        title_tag = content_root.find("h1")
        
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    last_updated = extract_date(soup, url)

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
            row['last_updated'] = last_updated
            break

    return True

def save_markdown(article_id, title, url, data):
    markdown_filename = f"{article_id}_{sanitize_filename(title)}.md"
    markdown_filepath = os.path.join(STORAGE_DIR, markdown_filename)
    
    with open(markdown_filepath, 'w', encoding='utf-8') as md_file:
        md_file.write(f"# {title}\n\n")
        md_file.write(f"URL: {url}\n")
        md_file.write(f"Last Updated: {data.get('last_updated', 'N/A')}\n\n")
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
    formatted_data, updated_rows, fieldnames = convert_csv_to_list(CSV_FILE)

    if 'last_updated' not in fieldnames:
        fieldnames.append('last_updated')

    for article_id, url in formatted_data:
        # Handle PDF files
        if url.lower().endswith(".pdf") or "/download/" in url.lower():
            print(f"Processing PDF/Download URL: {url}")
            extract_from_pdf(url, article_id, updated_rows)
            continue

        if "medlineplus.gov" in url:
            extract_from_medline(url, article_id, updated_rows)
        elif "pubmed.ncbi.nlm.nih.gov" in url:
            extract_from_pubmed(url, article_id, updated_rows)
        elif "ncbi.nlm.nih.gov" in url or "pmc.ncbi.nlm.nih.gov" in url:
            if "/articles" in url:
                extract_from_ncbi_articles(url, article_id, updated_rows)
            else:
                extract_from_ncbi(url, article_id, updated_rows)
        elif "rarediseases.info.nih.gov" in url:
            extract_from_medline(url, article_id, updated_rows)
        elif "genome.gov" in url:
            extract_from_medline(url, article_id, updated_rows)
        else:
            print(f"No specific extractor for URL: {url}, attempting default extractor.")
            extract_from_medline(url, article_id, updated_rows)

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(updated_rows)

    print("CSV file updated successfully.")
