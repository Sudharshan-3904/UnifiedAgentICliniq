from importlib.metadata import files
import os
import pandas as pd
import pdfx
import hashlib
import pathlib
from urllib.parse import urlparse, urlunparse

CSV_FILE = "data\\url_status.csv"
MAPPING_FILE = "data\\link_file_status_map.csv"
LINKS_SRC_DIR = "src_lib"


def normalize_url(url: str) -> list:
    """
    Normalize URL string. Returns a LIST of cleaned URLs (handling concatenated cases).
    - Removes newlines/whitespace and invisible characters (soft hyphen, zero-width spaces).
    - Removes enclosing brackets/quotes like <...>, (...), or "...".
    - Fixes common PDF-extraction artifacts (leading missing 'h' in 'https'/'http').
    - Splits concatenated cases like 'url1/http://url2'.
    - Lowercases scheme/netloc.
    - Removes www.
    - Strips trailing slash/backslash and common punctuation.
    """
    if not url:
        return []
        
    # initial cleanup: preserve original characters until we've removed invisible/hyphenation artifacts
    clean_text = url.strip()

    # remove soft-hyphen and zero-width / BOM / non-breaking space characters that often come from PDFs
    for ch in ['\u00ad', '\u200b', '\ufeff', '\u200c', '\u200d', '\xa0']:
        clean_text = clean_text.replace(ch, '')

    # remove line breaks and surrounding whitespace within the URL text
    clean_text = clean_text.replace('\n', '').replace('\r', '').replace(' ', '')

    # trim common trailing punctuation that may be adjacent to links in text
    clean_text = clean_text.rstrip('.,;:)]}\'"')

    # strip enclosing angle brackets, parentheses or quotes that sometimes wrap links
    if (clean_text.startswith('<') and clean_text.endswith('>')) or (clean_text.startswith('(') and clean_text.endswith(')')) or (clean_text.startswith('"') and clean_text.endswith('"')):
        clean_text = clean_text[1:-1]

    # fix common missing leading 'h' (e.g., 'ttps://...') introduced by PDF extraction
    if clean_text.lower().startswith(('ttp://', 'ttps://')):
        clean_text = 'h' + clean_text

    urls_to_process = []
    
    lower_text = clean_text.lower()
    if lower_text.count("http") > 1:
        indices = []
        start = 0
        while True:
            idx = lower_text.find("http", start)
            if idx == -1:
                break
            indices.append(idx)
            start = idx + 1
            
        for i in range(len(indices)):
            start_idx = indices[i]
            end_idx = indices[i+1] if i + 1 < len(indices) else len(clean_text)
            segment = clean_text[start_idx:end_idx]
            urls_to_process.append(segment)
    else:
        urls_to_process.append(clean_text)

    normalized_urls = []
    
    for raw in urls_to_process:
        raw = raw.rstrip('/\\')
        
        try:
            parsed = urlparse(raw)
            if not parsed.scheme or not parsed.netloc:
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


def _filter_truncated_urls(urls: list) -> list:
    """Remove URLs that are strict prefixes of other (longer) URLs from the same host.
    Heuristic: if url A is a strict prefix of url B, B has same scheme+netloc and len(B)-len(A) >= 3, drop A.
    """
    from urllib.parse import urlparse
    if not urls:
        return []

    # sort by length descending so we consider longest URLs first
    urls_sorted = sorted(set(urls), key=len, reverse=True)
    kept = []
    for u in urls_sorted:
        parsed_u = urlparse(u)
        is_prefix_of_kept = False
        for v in kept:
            parsed_v = urlparse(v)
            if parsed_u.scheme == parsed_v.scheme and parsed_u.netloc == parsed_v.netloc and v.startswith(u) and (len(v) > len(u)):
                is_prefix_of_kept = True
                break
        if not is_prefix_of_kept:
            kept.append(u)
    # return in original-ish order (longest-first is fine)
    return kept


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

    filename = os.path.basename(pdf_path)
    norm_links = []

    for url in raw_urls:
        norm_list = normalize_url(url)
        for norm_url in norm_list:
            if norm_url:
                norm_links.append(norm_url)

    # filter out truncated prefixes that are likely artifacts
    filtered_links = _filter_truncated_urls(norm_links)

    records = []
    for link in filtered_links:
        records.append({
            "link": link,
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
    return pd.DataFrame(columns=["id", "link", "progress", "status_code", "status_abbreviation"])

def append_new_records(records: list, csv_filename: str):
    """Append new records while avoiding duplicates and continuing IDs. Returns (new_count, duplicate_count)."""
    df_existing = load_existing_csv(csv_filename)
    
    if not df_existing.empty and "link" in df_existing.columns:
        existing_links = set(df_existing["link"].dropna().astype(str))
    else:
        existing_links = set()

    new_rows = []
    
    if not df_existing.empty and "id" in df_existing.columns and not df_existing["id"].dropna().empty:
        try:
            next_id = int(df_existing["id"].max()) + 1
        except ValueError:
            next_id = 1
    else:
        next_id = 1

    unique_input_records = {}
    for r in records:
        if r["link"] not in unique_input_records:
            unique_input_records[r["link"]] = r
    
    for link, record in unique_input_records.items():
        if link not in existing_links:
            new_rows.append({
                "id": next_id,
                "link": link,
                "progress": "yet"
            })
            existing_links.add(link)
            next_id += 1

    duplicate_count = max(0, len(unique_input_records) - len(new_rows))

    if not new_rows:
        print("No new unique links to add to status CSV.")
        return 0, duplicate_count
    else:
        df_new = pd.DataFrame(new_rows)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
        df_final["id"] = df_final["id"].astype(int)
        df_final.to_csv(csv_filename, index=False)
        print(f"Added {len(df_new)} new links to {csv_filename}. Total records: {len(df_final)}")
        return len(df_new), duplicate_count


def update_mapping_file(records: list, mapping_filename: str):
    """
    Update the mapping file with source information.
    Ensures that every link in records has its 'id', 'source_file', 'link_hash', and 'category' recorded.
    If possible, the 'id' is obtained from the status CSV (`CSV_FILE`).
    """
    if os.path.exists(mapping_filename):
        try:
            df_map = pd.read_csv(mapping_filename)
        except Exception:
            df_map = pd.DataFrame()
    else:
        df_map = pd.DataFrame()

    link_to_id = {}
    if os.path.exists(CSV_FILE):
        try:
            df_status = pd.read_csv(CSV_FILE, dtype={"id": object, "link": object})
            link_to_id = dict(zip(df_status['link'].astype(str), df_status['id'].astype(str)))
        except Exception:
            link_to_id = {}

    required_cols = ["link", "id", "source_file", "link_hash", "category"]
    for c in required_cols:
        if c not in df_map.columns:
            df_map[c] = pd.Series(dtype='str')

    link_sources = {}
    for r in records:
        l = r["link"]
        s = r["source_file"]
        if l in link_sources:
            if s not in link_sources[l]:
                link_sources[l].append(s)
        else:
            link_sources[l] = [s]
            
    updates = []
    for link, sources in link_sources.items():
        link_hash = hashlib.sha256(link.encode('utf-8')).hexdigest()
        first_source = sources[0] if sources else ''
        category = 'uncategorized'
        if first_source:
            base = os.path.splitext(os.path.basename(first_source))[0]
            if '-' in base:
                category = base.split('-')[0].strip()

        id_val = link_to_id.get(link, '')

        updates.append({
            "id": id_val,
            "link": link,
            "source_file": "; ".join(sources),
            "link_hash": link_hash,
            "category": category
        })
    
    if not updates:
        print("No updates for mapping file.")
        return

    df_updates = pd.DataFrame(updates)
    
    if df_map.empty:
        df_final = df_updates
    else:
        df_map = df_map.set_index("link")
        df_updates = df_updates.set_index("link")
        
        df_map.update(df_updates)
        
        new_links = df_updates.index.difference(df_map.index)
        if not new_links.empty:
            df_to_add = df_updates.loc[new_links]
            df_map = pd.concat([df_map, df_to_add])
            
        df_map.reset_index(inplace=True)
        df_final = df_map

    df_final.to_csv(mapping_filename, index=False)
    print(f"Mapping file {mapping_filename} updated with source files.")

def get_files_list(path:str=""):
    files_list = []

    for item in pathlib.Path(path).iterdir():
        files_list.append(str(item.absolute()))

    return files_list


def remove_truncated_links(csv_filename: str, mapping_filename: str = MAPPING_FILE) -> dict:
    """Clean up existing CSV/mapping by removing links that are strict prefixes of longer links on same host.
    Returns a summary dict: {'removed': int, 'before': int, 'after': int}.

    Note: This will reassign sequential IDs starting at 1 for the CSV and update mapping file IDs accordingly.
    """
    if not os.path.exists(csv_filename):
        print(f"CSV file not found: {csv_filename}")
        return {"removed": 0, "before": 0, "after": 0}

    try:
        df = pd.read_csv(csv_filename, dtype={"id": object, "link": object})
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return {"removed": 0, "before": 0, "after": 0}

    before = len(df)
    links = df["link"].astype(str).tolist()

    # detect truncated prefixes
    from urllib.parse import urlparse
    to_remove = set()
    for i, a in enumerate(links):
        pa = urlparse(a)
        for j, b in enumerate(links):
            if i == j:
                continue
            pb = urlparse(b)
            if pa.scheme == pb.scheme and pa.netloc == pb.netloc and b.startswith(a) and len(b) > len(a):
                to_remove.add(a)
                break

    if not to_remove:
        print("No truncated-prefix links detected to remove.")
        return {"removed": 0, "before": before, "after": before}

    df_clean = df[~df["link"].isin(to_remove)].copy()

    # reassign sequential ids
    df_clean = df_clean.reset_index(drop=True)
    df_clean["id"] = (df_clean.index + 1).astype(int)

    try:
        df_clean.to_csv(csv_filename, index=False)
    except Exception as e:
        print(f"Error writing cleaned CSV: {e}")
        return {"removed": 0, "before": before, "after": before}

    # update mapping file: drop rows with removed links
    if os.path.exists(mapping_filename):
        try:
            df_map = pd.read_csv(mapping_filename, dtype={"link": object, "id": object})
            df_map = df_map[~df_map["link"].isin(list(to_remove))].copy()
            # update ids in mapping based on cleaned csv
            link_to_id = dict(zip(df_clean['link'].astype(str), df_clean['id'].astype(str)))
            df_map['id'] = df_map['link'].map(link_to_id).fillna('')
            df_map.to_csv(mapping_filename, index=False)
        except Exception as e:
            print(f"Warning: could not update mapping file cleanly: {e}")

    after = len(df_clean)
    removed = before - after
    print(f"Removed {removed} truncated links from {csv_filename}. Rows: {before} -> {after}")
    return {"removed": removed, "before": before, "after": after}

if __name__ == "__main__":
    pdf_files_list = get_files_list(LINKS_SRC_DIR)

    extracted_records = extract_urls_from_pdfs(pdf_files_list)
    
    new_count, dup_count = append_new_records(extracted_records, CSV_FILE)
    print(f"Links added: {new_count} | duplicates: {dup_count}")
    
    update_mapping_file(extracted_records, MAPPING_FILE)
