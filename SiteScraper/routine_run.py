import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
import re
import json
import hashlib
import io
import PyPDF2
from datetime import datetime
from links_to_csv import extract_urls_from_pdfs, append_new_records, update_mapping_file, get_files_list, MAPPING_FILE

MD_FILE_STORAGE = "md_files"
CSV_STATUS_FILE = r"data\update_progress.csv"
RUN_TRACKER_FILE = r"data\run_tracker.json"
MD_FILES_METADATA_FILE = r"data\md_files_metadata.json"
MAPPING_FILE = r"data\link_file_status_map.csv"
SCRAPING_LINKS_DIR = "src_lib"
PDF_FILES = get_files_list(SCRAPING_LINKS_DIR)

os.makedirs(MD_FILE_STORAGE, exist_ok=True)
os.makedirs(os.path.dirname(CSV_STATUS_FILE), exist_ok=True)

scraper = cloudscraper.create_scraper()

def convert_csv_to_list(input_file):
    result = []
    updated_rows = []

    if not os.path.exists(input_file):
        write_status_csv(input_file, [])
        return result, updated_rows

    with open(input_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            id_value = row.get('id')
            link_value = row.get('link')
            progress_value = (row.get('progress') or row.get('status') or '').strip()

            if not id_value or not link_value:
                continue

            try:
                id_int = int(id_value)
            except Exception:
                continue

            if progress_value.lower() == 'extracted':
                continue

            result.append([id_int, link_value])
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

def ensure_data_files():
    os.makedirs(MD_FILE_STORAGE, exist_ok=True)
    os.makedirs(os.path.dirname(CSV_STATUS_FILE), exist_ok=True)
    if not os.path.exists(RUN_TRACKER_FILE):
        with open(RUN_TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)
    if not os.path.exists(MD_FILES_METADATA_FILE):
        with open(MD_FILES_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)


def load_json_file(path, default=None):
    if default is None:
        if path == MD_FILES_METADATA_FILE:
            default = {}
        elif path == RUN_TRACKER_FILE:
            default = []
        else:
            default = {}
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def get_link_source(link: str):
    if not os.path.exists(MAPPING_FILE):
        return None
    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('link') == link:
                    return row.get('source_file')
    except Exception:
        pass
    return None


def get_category_from_source(source_file: str) -> str:
    if not source_file:
        return 'uncategorized'
    base = os.path.splitext(os.path.basename(source_file))[0]
    if '-' in base:
        return base.split('-')[0].strip()
    return 'uncategorized'


def update_md_metadata(id_val, link, source_file, save_path, category, extraction_date, file_hash):
    data = dict(load_json_file(MD_FILES_METADATA_FILE, {}))
    data[str(id_val)] = {
        'id': id_val,
        'link_source': source_file,
        'extraction_date': extraction_date.isoformat() if isinstance(extraction_date, datetime) else str(extraction_date),
        'save_path': save_path,
        'category': category,
        'file_hash': file_hash,
        'link': link
    }
    save_json_file(MD_FILES_METADATA_FILE, data)


def update_run_tracker(**kwargs):
    runs = list(load_json_file(RUN_TRACKER_FILE, []))
    entry = {
        'run_id': datetime.now().isoformat(),
        'last_run_date': datetime.now().isoformat(),
        'pdf_files': kwargs.get('pdf_files', []),
        'new_links_identified_count': kwargs.get('new_links', 0),
        'duplicate_links_count': kwargs.get('duplicates', 0),
        'unsuccessful_links_from_prev_run_count': kwargs.get('prev_failed', 0),
        'total_links_to_be_scraped_count': kwargs.get('total', 0),
        'failed_links_count': kwargs.get('failed', 0),
        'successful_links_count': kwargs.get('succeeded', 0),
        'stages': kwargs.get('stages', {})
    }

    # Only append to run tracker when meaningful changes occur.
    # Compare numeric counts and pdf list; ignore stage timestamps but treat added/removed stage keys as meaningful.
    last = runs[-1] if runs else None
    if last:
        numeric_keys = [
            'new_links_identified_count', 'duplicate_links_count',
            'unsuccessful_links_from_prev_run_count', 'total_links_to_be_scraped_count',
            'failed_links_count', 'successful_links_count'
        ]
        same_counts = all(last.get(k) == entry.get(k) for k in numeric_keys)
        same_pdfs = list(last.get('pdf_files', [])) == list(entry.get('pdf_files', []))
        last_stage_keys = set(last.get('stages', {}).keys() or [])
        entry_stage_keys = set(entry.get('stages', {}).keys() or [])
        same_stage_keys = last_stage_keys == entry_stage_keys

        if same_counts and same_pdfs and same_stage_keys:
            # No meaningful changes; skip writing run tracker.
            return None

    runs.append(entry)
    save_json_file(RUN_TRACKER_FILE, runs)
    return entry


def extract_from_pdf(url, article_id):
    """Extract text content from PDF files."""
    try:
        response = scraper.get(url, headers=get_headers(), timeout=30)
        if response.status_code != 200:
            print(f"Failed to fetch PDF {url} (Status: {response.status_code})")
            return None
            
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
            ],
            "extracted_date": datetime.now()
        }
        
        return data
    except Exception as e:
        print(f"Error extracting PDF {url}: {e}")
        return None


def extract_from_pubmed(soup, url, article_id):
    """Extract content from PubMed articles."""
    try:
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
            return None

        data["extracted_date"] = datetime.now()
        return data
    except Exception as e:
        print(f"Error extracting PubMed {url}: {e}")
        return None


def extract_from_medline(soup, url, article_id):
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
        return None

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
            if not section_title:
                continue
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
        return None

    data["extracted_date"] = datetime.now()
    return data

def extract_from_ncbi_articles(soup, url, article_id):
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
    raw_filename = url.split('/')[-1] or ''
    if '?' in raw_filename:
        raw_filename = raw_filename.split('?')[0]

    sanitized_name = sanitize_filename(raw_filename) or sanitize_filename(title)[:50]
    base_name = f"{article_id}_{sanitized_name}"
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
    content_hash = compute_sha256(content)

    suffix = 1
    while os.path.exists(markdown_filepath):
        try:
            with open(markdown_filepath, 'r', encoding='utf-8') as f:
                existing = f.read()
            if compute_sha256(existing) == content_hash:
                print(f"Markdown already exists and is identical, skipping: {markdown_filepath}")
                return 'skipped', markdown_filepath, content_hash
        except Exception:
            pass
        markdown_filename = f"{base_name}_{suffix}.md"
        markdown_filepath = os.path.join(MD_FILE_STORAGE, markdown_filename)
        suffix += 1

    with open(markdown_filepath, 'w', encoding='utf-8') as md_file:
        md_file.write(content)

    print(f"Markdown file saved as: {markdown_filepath}")
    return 'saved', markdown_filepath, content_hash


def write_status_csv(file_path, rows):
    """Write canonical update_progress CSV with id, link, progress, status_code, status_abbreviation, extracted_date (overwrite)."""
    fieldnames = ['id', 'link', 'progress', 'status_code', 'status_abbreviation', 'extracted_date']
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                'id': r.get('id'),
                'link': r.get('link'),
                'progress': r.get('progress', r.get('status', '')),
                'status_code': r.get('status_code', ''),
                'status_abbreviation': r.get('status_abbreviation', ''),
                'extracted_date': r.get('extracted_date', '')
            })
    print(f"CSV file updated successfully: {file_path}")

def append_updates_file(updates_file, updates_rows):
    """Append update rows (may contain extra columns) to a separate updates CSV."""
    if not updates_rows:
        return
    fieldnames = ['id', 'link', 'progress', 'status_code', 'status_abbreviation', 'note', 'extracted_date']
    exists = os.path.exists(updates_file)
    with open(updates_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for u in updates_rows:
            writer.writerow({
                'id': u.get('id'),
                'link': u.get('link'),
                'progress': u.get('progress', u.get('status', '')),
                'status_code': u.get('status_code', ''),
                'status_abbreviation': u.get('status_abbreviation', ''),
                'note': u.get('note', ''),
                'extracted_date': u.get('extracted_date', '')
            })
    print(f"Appended {len(updates_rows)} updates to {updates_file}")


if __name__ == "__main__":
    ensure_data_files()

    extracted_records = extract_urls_from_pdfs(PDF_FILES)
    if extracted_records:
        new_count, dup_count = append_new_records(extracted_records, CSV_STATUS_FILE)
        update_mapping_file(extracted_records, MAPPING_FILE)
    else:
        new_count, dup_count = 0, 0

    update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, stages={'links_extracted': datetime.now().isoformat()})

    formatted_data, updated_rows = convert_csv_to_list(CSV_STATUS_FILE)

    # Build cache of links already extracted (from saved metadata) to skip re-fetching
    md_meta = load_json_file(MD_FILES_METADATA_FILE, {})
    extracted_links = set()
    if isinstance(md_meta, dict):
        for v in md_meta.values():
            link_val = v.get('link')
            if link_val:
                extracted_links.add(link_val)

    prev_failed_count = sum(1 for r in updated_rows if (r.get('progress') or r.get('status') or '').lower() == 'failed')

    BATCH_SIZE = 10
    count = 0

    UPDATES_FILE = r"data\url_status_updates.csv"
    pending_updates = []

    existing_files = set(os.listdir(MD_FILE_STORAGE))

    for article_id, url in formatted_data:
        # If this link is already present in metadata, skip fetching and mark as extracted.
        if url in extracted_links:
            for row in updated_rows:
                if row.get('link') == url:
                    row['progress'] = 'extracted'
                    row['status_code'] = ''
                    row['status_abbreviation'] = ''
                    md_entry = {}
                    if isinstance(md_meta, dict):
                        md_entry = next((v for v in md_meta.values() if v.get('link') == url), {})
                    row['extracted_date'] = md_entry.get('extraction_date') or datetime.now().isoformat()
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': 'already_extracted'})
                    break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
                failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
                total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
                update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'batch_saved': datetime.now().isoformat()})
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        # Handle PDF files
        if url.lower().endswith(".pdf") or "/download/" in url.lower():
            print(f"Processing PDF/Download URL: {url}")
            data = extract_from_pdf(url, article_id)
            if data is None:
                for row in updated_rows:
                    if row.get('link') == url:
                        row['progress'] = 'failed'
                        pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': 'pdf_extraction_failed'})
                        break
            else:
                save_result, md_path, file_hash = save_markdown(article_id, data['title'], url, data)
                if save_result in ('saved', 'skipped'):
                    for row in updated_rows:
                        if row.get('link') == url:
                            row['progress'] = 'extracted'
                            row['extracted_date'] = datetime.now().isoformat()
                            pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress']})
                            break
                    if save_result == 'saved':
                        existing_files.add(os.path.basename(md_path))
                        source_file = get_link_source(url)
                        category = get_category_from_source(str(source_file or ''))
                        update_md_metadata(article_id, url, source_file, md_path, category, datetime.now(), file_hash)
                else:
                    for row in updated_rows:
                        if row.get('link') == url:
                            row['progress'] = 'failed'
                            pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': 'pdf_save_failed'})
                            break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
                failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
                total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
                update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'batch_saved': datetime.now().isoformat()})
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        try:
            response = scraper.get(url, headers=get_headers(), timeout=30)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            for row in updated_rows:
                if row.get('link') == url:
                    row['progress'] = 'failed'
                    row['status_code'] = ''
                    row['status_abbreviation'] = ''
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': str(e)})
                    break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
                failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
                total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
                update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'batch_saved': datetime.now().isoformat()})
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        if response.status_code != 200:
            print(f"Failed to fetch {url} (Status: {response.status_code})")
            for row in updated_rows:
                if row.get('link') == url:
                    row['progress'] = 'failed'
                    row['status_code'] = response.status_code
                    row['status_abbreviation'] = getattr(response, 'reason', '')
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'status_code': response.status_code, 'status_abbreviation': getattr(response, 'reason', '')})
                    break
            count += 1
            if count % BATCH_SIZE == 0:
                write_status_csv(CSV_STATUS_FILE, updated_rows)
                append_updates_file(UPDATES_FILE, pending_updates)
                succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
                failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
                total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
                update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'batch_saved': datetime.now().isoformat()})
                pending_updates = []
                print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        data = None
        if "medlineplus.gov" in url:
            data = extract_from_medline(soup, url, article_id)
        elif "pubmed.ncbi.nlm.nih.gov" in url:
            data = extract_from_pubmed(soup, url, article_id)
        elif "ncbi.nlm.nih.gov" in url or "pmc.ncbi.nlm.nih.gov" in url:
            if "/articles" in url:
                data = extract_from_ncbi_articles(soup, url, article_id)
            else:
                data = extract_from_ncbi(soup, url, article_id)
        elif "rarediseases.info.nih.gov" in url:
            data = extract_from_medline(soup, url, article_id)
        elif "genome.gov" in url:
            data = extract_from_medline(soup, url, article_id)
        else:
            print(f"No specific extractor for URL: {url}, attempting default Medline extractor.")
            data = extract_from_medline(soup, url, article_id)

        if data is None:
            for row in updated_rows:
                if row.get('link') == url:
                    row['progress'] = 'failed'
                    pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': 'extraction_failed'})
                    break
        else:
            save_result, md_path, file_hash = save_markdown(article_id, data['title'], url, data)
            if save_result in ('saved', 'skipped'):
                for row in updated_rows:
                    if row.get('link') == url:
                        row['progress'] = 'extracted'
                        row['status_code'] = getattr(response, 'status_code', '')
                        row['status_abbreviation'] = getattr(response, 'reason', '')
                        row['extracted_date'] = datetime.now().isoformat()
                        pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'status_code': row.get('status_code')})
                        break
                if save_result == 'saved':
                    existing_files.add(os.path.basename(md_path))
                    source_file = get_link_source(url)
                    category = get_category_from_source(str(source_file or ''))
                    update_md_metadata(article_id, url, source_file, md_path, category, datetime.now(), file_hash)
            else:
                for row in updated_rows:
                    if row.get('link') == url:
                        row['progress'] = 'failed'
                        pending_updates.append({'id': row.get('id'), 'link': row.get('link'), 'progress': row['progress'], 'note': 'save_failed'})
                        break

        count += 1
        if count % BATCH_SIZE == 0:
            write_status_csv(CSV_STATUS_FILE, updated_rows)
            append_updates_file(UPDATES_FILE, pending_updates)
            succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
            failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
            total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
            update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'batch_saved': datetime.now().isoformat()})
            pending_updates = []
            print(f"Batch of {BATCH_SIZE} reached. CSV saved and updates appended.")

    write_status_csv(CSV_STATUS_FILE, updated_rows)
    append_updates_file(UPDATES_FILE, pending_updates)

    succeeded = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'extracted')
    failed = sum(1 for r in updated_rows if (r.get('progress') or '').lower() == 'failed')
    total = len([r for r in updated_rows if (r.get('progress') or '').lower() != 'extracted'])
    update_run_tracker(pdf_files=[os.path.basename(p) for p in PDF_FILES], new_links=new_count, duplicates=dup_count, prev_failed=prev_failed_count, total=total, failed=failed, succeeded=succeeded, stages={'scraping_completed': datetime.now().isoformat()},)

    print("Final CSV update completed.")
