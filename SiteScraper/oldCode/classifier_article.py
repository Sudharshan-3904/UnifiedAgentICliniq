import requests
import csv
import os
from typing import List, Dict

CSV_FILE = r"data\url_status.csv"
CLASSIFIED_FILE = r"data\url_status_classified.csv"


def get_headers():
    """Return HTTP headers to avoid 403 errors from user-agent blocking."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }


def get_status_abbreviation(status_code: int) -> str:
    """Get human-readable status code abbreviation."""
    status_map = {
        200: "OK",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        408: "Request Timeout",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        0: "Connection Error",
        -1: "Unknown Error"
    }
    return status_map.get(status_code, f"HTTP {status_code}")


def read_url_status_csv() -> List[Dict]:
    """Read all URLs from url_status.csv."""
    urls = []
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found")
        return urls
    
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            urls.append(row)
    
    return urls


def check_link_status(url: str) -> int:
    """Check the HTTP status code of a URL."""
    try:
        response = requests.head(url, headers=get_headers(), timeout=10, allow_redirects=True)
        return response.status_code
    except requests.exceptions.Timeout:
        return 408  # Request Timeout
    except requests.exceptions.ConnectionError:
        return 0  # Connection error
    except Exception as e:
        print(f"Error checking {url}: {str(e)}")
        return -1  # Unknown error


def classify_articles():
    """
    Check all URLs in url_status.csv and classify them as 'article' (200) or 'Non-article' (other codes).
    Saves results to url_status_classified.csv with working status and status code.
    """
    print("Reading URLs from url_status.csv...")
    urls = read_url_status_csv()
    
    if not urls:
        print("No URLs found in url_status.csv")
        return
    
    classified_links = []
    total_urls = len(urls)
    article_count = 0
    non_article_count = 0
    
    print(f"Checking {total_urls} URLs...\n")
    
    for idx, url_entry in enumerate(urls, 1):
        link = url_entry['link']
        print(f"[{idx}/{total_urls}] Checking: {link}", end=" ... ")
        
        status_code = check_link_status(link)
        status_abbr = get_status_abbreviation(status_code)
        
        # Classify as article (200) or Non-article (other codes)
        if status_code == 200:
            working_status = "article"
            article_count += 1
        else:
            working_status = "Non-article"
            non_article_count += 1
        
        print(f"Status: {status_code} ({status_abbr})")
        
        classified_links.append({
            'id': url_entry['id'],
            'link': link,
            'status': url_entry['status'],
            'working': working_status,
            'status_code': status_code,
            'status_abbreviation': status_abbr
        })
    
    # Save classified results to url_status_classified.csv
    print(f"\nSaving results to {CLASSIFIED_FILE}...")
    
    os.makedirs(os.path.dirname(CLASSIFIED_FILE), exist_ok=True)
    
    with open(CLASSIFIED_FILE, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'link', 'status', 'working', 'status_code', 'status_abbreviation']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified_links)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Classification Complete!")
    print(f"{'='*60}")
    print(f"Total URLs checked:        {total_urls}")
    print(f"Working links (200):       {article_count}")
    print(f"Non-working links (other): {non_article_count}")
    print(f"{'='*60}")
    print(f"✓ Results saved to {CLASSIFIED_FILE}")


if __name__ == "__main__":
    classify_articles()
