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


def extract_medlineplus_page(url, article_id, updated_rows):
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"

    data = {
        "id": article_id,
        "title": title,
        "url": url,
        "sections": []
    }

    article_tag = soup.find("article")
    if not article_tag:
        print("Main article content not found.")
        return

    sections = article_tag.find_all(["h2", "h3", "p", "ul"])
    current_section = None

    for elem in sections:
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
            if current_section:
                current_section["content"].append({
                    "type": "paragraph",
                    "text": paragraph_text
                })

        elif elem.name == "ul":
            list_items = [li.get_text(strip=True) for li in elem.find_all("li")]
            if current_section and list_items:
                current_section["content"].append({
                    "type": "list",
                    "items": list_items
                })

    if current_section:
        data["sections"].append(current_section)

    if not data["sections"]:
        print(f"No content extracted for {url}")
        return

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

    for row in updated_rows:
        if row['link'] == url:
            row['status'] = 'extracted'
            break


def update_csv_in_batches(input_file, batch_size=10):
    formatted_data, updated_rows = convert_csv_to_list(input_file)

    for i in range(0, len(formatted_data), batch_size):
        batch = formatted_data[i:i + batch_size]

        # Process each URL in the batch
        for article_id, url in batch:
            extract_medlineplus_page(url, article_id, updated_rows)

        # Update CSV after each batch
        with open(input_file, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['id', 'link', 'status']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"CSV file updated after processing batch {i // batch_size + 1}.")

    print("CSV file updated successfully.")


# Run the batch update
update_csv_in_batches(CSV_FILE)
