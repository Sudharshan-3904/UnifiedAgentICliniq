import requests
from bs4 import BeautifulSoup
import html2text


def scrape_article_as_markdown(url):
    # Step 1: Fetch the HTML content
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64)"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    # Step 2: Parse HTML
    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("article")

    # Fallback to article-content-scroll if article tag not found
    if not article:
        article = soup.find(id="article-content-scroll")

    if not article:
        raise ValueError(
            "No <article> tag or #article-content-scroll element found on this page")

    # Step 3: Extract page title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Step 4: Convert HTML → Markdown
    converter = html2text.HTML2Text()
    converter.ignore_links = False     # Keep links
    converter.ignore_images = False    # Keep image markdown
    converter.ignore_emphasis = False  # Keep bold/italic
    converter.body_width = 0           # Prevent line wrapping

    markdown = converter.handle(str(article))

    # Step 5: Return both markdown and title
    return markdown.strip(), title


scrape_article_as_markdown("https://pmc.ncbi.nlm.nih.gov/articles/PMC6020195")