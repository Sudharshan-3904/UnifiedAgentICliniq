import requests
from bs4 import BeautifulSoup
import csv
import json
import os
import re


CSV_FILE = r"data\url_status.csv"
JSON_FILE = r"data\extracted_articles.json"


def get_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.5",
    }


def load_existing_json(json_file):
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_to_json(json_file, records):
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def convert_csv_to_list(input_file):
    to_process = []
    updated_rows = []

    with open(input_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["status"].lower() == "extracted":
                print(f"Skipping already extracted URL: {row['link']}")
                updated_rows.append(row)
                continue

            to_process.append((int(row["id"]), row["link"]))
            updated_rows.append(row)

    return to_process, updated_rows


def extract_article(url, article_id):
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
    except Exception as e:
        print(f"Request error for {url}: {e}")
        return None

    if response.status_code != 200:
        print(f"Failed to fetch {url} (status {response.status_code})")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    content_root = (
        soup.find("article")
        or soup.find("main")
        or soup.find(class_="jig-ncbi-inpagenav")
        or soup.find(id="maincontent")
    )

    if not content_root:
        print(f"No main content found for {url}")
        return None

    # Abstract (if present)
    abstract_div = soup.select_one(
        ".abstract, #abstract, .abstract-content, .editor-summary"
    )
    if abstract_div:
        data["sections"].append({
            "section_title": "Abstract",
            "content": [{
                "type": "paragraph",
                "text": abstract_div.get_text(strip=True)
            }]
        })

    elements = content_root.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in elements:
        if elem.find_parent(class_=["ref-list", "ack", "app-group", "fn-group"]):
            continue

        if elem.name in ["h2", "h3"]:
            if current_section:
                data["sections"].append(current_section)
            current_section = {
                "section_title": elem.get_text(strip=True),
                "content": []
            }

        elif elem.name == "p":
            text = elem.get_text(strip=True)
            if not text:
                continue

            if current_section is None:
                current_section = {
                    "section_title": "Introduction",
                    "content": []
                }

            current_section["content"].append({
                "type": "paragraph",
                "text": text
            })

        elif elem.name == "ul":
            items = [li.get_text(strip=True) for li in elem.find_all("li")]
            if items:
                if current_section is None:
                    current_section = {
                        "section_title": "Introduction",
                        "content": []
                    }

                current_section["content"].append({
                    "type": "list",
                    "items": items
                })

    if current_section:
        data["sections"].append(current_section)

    if not data["sections"]:
        print(f"No structured content extracted for {url}")
        return None

    return data


def update_csv(csv_file, rows):
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "link", "status"])
        writer.writeheader()
        writer.writerows(rows)


def process_urls(batch_size=10):
    articles = load_existing_json(JSON_FILE)
    existing_ids = {a["id"] for a in articles}

    formatted_data, updated_rows = convert_csv_to_list(CSV_FILE)

    for i in range(0, len(formatted_data), batch_size):
        batch = formatted_data[i:i + batch_size]

        for article_id, url in batch:
            if article_id in existing_ids:
                continue

            article_data = extract_article(url, article_id)
            if article_data:
                articles.append(article_data)

                for row in updated_rows:
                    if row["link"] == url:
                        row["status"] = "extracted"
                        break

        save_to_json(JSON_FILE, articles)
        update_csv(CSV_FILE, updated_rows)

        print(f"Batch {i // batch_size + 1} processed.")

    print("Processing complete.")


if __name__ == "__main__":
    process_urls(batch_size=10)
