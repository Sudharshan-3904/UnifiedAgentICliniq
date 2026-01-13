import os
import pandas as pd
import pdfx
from urllib.parse import urlparse, urlunparse

PDF_FILES = [
    "data\\Conditioned Tes - Knowledge Source - Links.pdf",
    "data\\Conditioned Tes - Knowledge Source - Links (1).pdf",
    "data\\Unified Tes - References - Cardiovascular System.pdf"
]

CSV_FILE = "data\\url_status.csv"
MAPPING_FILE = "data\\link_file_status_map.csv"


def normalize_url(url: str) -> list:
    """
    Normalize URL string. Returns a LIST of cleaned URLs (handling concatenated cases).
    - Removes newlines/whitespace.
    - Splist cases like 'url1/http://url2'.
    - Lowercases scheme/netloc.
    - Removes www.
    - Strips trailing slash/backslash.
    """
    if not url:
        return []
        
    # Initial cleanup
    clean_text = url.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    
    # Check for concatenated URLs (e.g. multiple http/https occurrences)
    # We'll split by 'http' but need to preserve the scheme.
    
    urls_to_process = []
    
    # Simple split heuristic: if "http" occurs more than once
    lower_text = clean_text.lower()
    if lower_text.count("http") > 1:
        # Split carefully. 
        # "https://site.com/https://site2.com" -> ["https://site.com/", "https://site2.com"]
        indices = []
        start = 0
        while True:
            idx = lower_text.find("http", start)
            if idx == -1:
                break
            # heuristic: ensure valid start (not just 'http' in a random word, though rare in scraped urls)
            indices.append(idx)
            start = idx + 1
            
        for i in range(len(indices)):
            start_idx = indices[i]
            end_idx = indices[i+1] if i + 1 < len(indices) else len(clean_text)
            segment = clean_text[start_idx:end_idx]
            # remove leading slash/garbage if any (e.g. from "...com/https...")
            # usually the previous url end includes the slash, but the new one starts at 'http'
            urls_to_process.append(segment)
    else:
        urls_to_process.append(clean_text)

    normalized_urls = []
    
    for raw in urls_to_process:
        # Strip trailing slashes/backslashes
        # Also, check if it ends with a weird char
        raw = raw.rstrip('/\\')
        
        try:
            parsed = urlparse(raw)
            # Basic validation: must have scheme and netloc to be useful
            if not parsed.scheme or not parsed.netloc:
                # heuristic: if it looks like a url (contains .com, .gov, etc), maybe try prepending http if missing?
                # For now, simplistic approach: discard if really garbage.
                if "http" in raw:
                     normalized_urls.append(raw)
                continue

            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]

            normalized = urlunparse((
                parsed.scheme.lower(),
                netloc,
                parsed.path.rstrip("/"),
                parsed.params,
                parsed.query,
                ""
            ))
            normalized_urls.append(normalized)
            
        except Exception:
            if "http" in raw:
                 normalized_urls.append(raw)

    return normalized_urls


def extract_urls_from_pdf(pdf_path: str) -> list:
    """Extract and normalize URLs from a single PDF, returning link and source."""
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return []

    try:
        pdf = pdfx.PDFx(pdf_path)
        refs = pdf.get_references_as_dict()
        raw_urls = refs.get("url", [])
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return []

    records = []
    filename = os.path.basename(pdf_path)
    
    for url in raw_urls:
        norm_list = normalize_url(url)
        for norm_url in norm_list:
            if norm_url:  # Filter out empty strings
                records.append({
                    "link": norm_url,
                    "source_file": filename
                })

    print(f"Read '{pdf_path}' - {len(records)} links found")
    return records


def extract_urls_from_pdfs(pdf_files: list) -> list:
    """Extract URLs from multiple PDFs."""
    all_records = []
    
    for pdf_file in pdf_files:
        all_records.extend(extract_urls_from_pdf(pdf_file))

    return all_records


def load_existing_csv(csv_filename: str) -> pd.DataFrame:
    """Load existing CSV or create a new DataFrame."""
    if os.path.exists(csv_filename):
        try:
            return pd.read_csv(csv_filename)
        except Exception as e:
            print(f"Error loading {csv_filename}: {e}")
    return pd.DataFrame(columns=["id", "link", "status"])


def append_new_records(records: list, csv_filename: str):
    """Append new records while avoiding duplicates and continuing IDs."""
    df_existing = load_existing_csv(csv_filename)
    
    # Existing links set for fast lookup
    if not df_existing.empty and "link" in df_existing.columns:
        existing_links = set(df_existing["link"].dropna().astype(str))
    else:
        existing_links = set()

    new_rows = []
    
    # Start ID (handle empty case safely)
    if not df_existing.empty and "id" in df_existing.columns and not df_existing["id"].dropna().empty:
        try:
            next_id = int(df_existing["id"].max()) + 1
        except ValueError:
            next_id = 1
    else:
        next_id = 1

    # Deduplicate input records based on link, keeping first occurrence
    unique_input_records = {} # link -> record
    for r in records:
        if r["link"] not in unique_input_records:
            unique_input_records[r["link"]] = r
    
    # Determine which are truly new
    for link, record in unique_input_records.items():
        if link not in existing_links:
            new_rows.append({
                "id": next_id,
                "link": link,
                "status": "yet"
            })
            existing_links.add(link)
            next_id += 1

    if not new_rows:
        print("No new unique links to add to status CSV.")
    else:
        df_new = pd.DataFrame(new_rows)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
        # Ensure ID is integer
        df_final["id"] = df_final["id"].astype(int)
        df_final.to_csv(csv_filename, index=False)
        print(f"Added {len(df_new)} new links to {csv_filename}. Total records: {len(df_final)}")


def update_mapping_file(records: list, mapping_filename: str):
    """
    Update the mapping file with source information.
    Ensures that every link in records has its 'source_file' recorded.
    """
    if os.path.exists(mapping_filename):
        try:
            df_map = pd.read_csv(mapping_filename)
        except Exception:
            df_map = pd.DataFrame()
    else:
        df_map = pd.DataFrame()

    # Ensure required columns exist
    if "link" not in df_map.columns:
        df_map["link"] = pd.Series(dtype='str')
    if "source_file" not in df_map.columns:
        df_map["source_file"] = pd.Series(dtype='str')

    # Convert records to link -> [sources]
    link_sources = {}
    for r in records:
        l = r["link"]
        s = r["source_file"]
        if l in link_sources:
            if s not in link_sources[l]:
                link_sources[l].append(s)
        else:
            link_sources[l] = [s]
            
    # Prepare update data
    updates = []
    for link, sources in link_sources.items():
        updates.append({
            "link": link,
            "source_file": "; ".join(sources)
        })
    
    if not updates:
        print("No updates for mapping file.")
        return

    df_updates = pd.DataFrame(updates)
    
    if df_map.empty:
        df_final = df_updates
    else:
        # We merge df_updates into df_map
        # If link exists, update source_file. If not, append.
        
        # Set index to link
        df_map = df_map.set_index("link")
        df_updates = df_updates.set_index("link")
        
        # Update existing rows
        df_map.update(df_updates)
        
        # Identify new rows
        # Index difference
        new_links = df_updates.index.difference(df_map.index)
        if not new_links.empty:
            df_to_add = df_updates.loc[new_links]
            df_map = pd.concat([df_map, df_to_add])
            
        df_map.reset_index(inplace=True)
        df_final = df_map

    df_final.to_csv(mapping_filename, index=False)
    print(f"Mapping file {mapping_filename} updated with source files.")


if __name__ == "__main__":
    extracted_records = extract_urls_from_pdfs(PDF_FILES)
    
    # 1. Update status CSV (Unique links only)
    append_new_records(extracted_records, CSV_FILE)
    
    # 2. Update Mapping CSV (Link -> Source File)
    update_mapping_file(extracted_records, MAPPING_FILE)
