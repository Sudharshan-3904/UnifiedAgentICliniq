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


def normalize_url(url: str) -> str:
    """
    Normalize URLs to avoid duplicate entries caused by formatting differences.
    - lowercases scheme and hostname
    - removes www
    - removes fragments
    - strips trailing slash
    """
    parsed = urlparse(url)

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

    return normalized


def extract_urls_from_pdf(pdf_path: str) -> list:
    """Extract and normalize URLs from a single PDF."""
    pdf = pdfx.PDFx(pdf_path)
    refs = pdf.get_references_as_dict()
    raw_urls = refs.get("url", [])

    records = []
    for url in raw_urls:
        records.append({
            "link": normalize_url(url)
        })

    print(f"Read '{pdf_path}' - {len(records)} links found")
    return records


def extract_urls_from_pdfs(pdf_files: list) -> list:
    """Extract URLs from multiple PDFs."""
    all_records = []

    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            all_records.extend(extract_urls_from_pdf(pdf_file))
        else:
            print(f"File not found: {pdf_file}")

    return all_records


def load_existing_csv(csv_filename: str) -> pd.DataFrame:
    """Load existing CSV or create a new DataFrame."""
    if os.path.exists(csv_filename):
        return pd.read_csv(csv_filename)
    return pd.DataFrame(columns=["id", "link", "status"])


def append_new_records(records: list, csv_filename: str):
    """Append new records while avoiding duplicates and continuing IDs."""
    df_existing = load_existing_csv(csv_filename)
    existing_links = set(df_existing["link"]) if not df_existing.empty else set()

    new_records = [
        r for r in records
        if r["link"] not in existing_links
    ]

    if not new_records:
        print("No new links to add.")
        return

    start_id = df_existing["id"].max() + 1 if not df_existing.empty else 1

    rows = []
    for i, record in enumerate(new_records):
        rows.append({
            "id": start_id + i,
            "link": record["link"],
            "status": "yet"
        })

    df_new = pd.DataFrame(rows)
    df_final = pd.concat([df_existing, df_new], ignore_index=True)

    df_final.to_csv(csv_filename, index=False)
    print(f"Added {len(df_new)} new links. Total records: {len(df_final)}")


if __name__ == "__main__":
    extracted_records = extract_urls_from_pdfs(PDF_FILES)
    append_new_records(extracted_records, CSV_FILE)
