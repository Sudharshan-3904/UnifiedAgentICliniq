# SiteScraper

---

A Python-based web scraper designed to extract, process, and organize medical articles from PubMed Central (PMC) and other web sources. The tool automates the extraction of URLs from PDF documents, scrapes article content, converts it to Markdown format, and trims unnecessary sections for cleaner output.

---

## Features

- **URL Extraction**: Extracts and normalizes URLs from PDF files containing medical knowledge sources.
- **Web Scraping**: Uses cloudscraper to bypass anti-bot measures and scrape article content from various medical websites, with a focus on PMC articles.
- **Content Processing**: Converts scraped HTML content into structured Markdown files.
- **Markdown Trimming**: Removes references, acknowledgments, and footer content to produce clean, readable Markdown files.
- **Progress Tracking**: Maintains detailed logs and metadata for all processed articles and runs.
- **Duplicate Handling**: Checks for duplicate content and avoids re-processing existing files.

---

## Project Structure

```structure
SiteScraper/
├── routine_run.py              # Main script to run the full scraping pipeline
├── links_to_csv.py             # Handles URL extraction from PDFs
├── process_pmc_fulltext.py     # Processes PMC-specific article content
├── trim_md_files.py            # Trims Markdown files to remove unwanted sections
├── data/                       # Data storage directory
│   ├── link_file_status_map.csv # Mapping of links to files and status
│   ├── md_files_metadata.json  # Metadata for all processed Markdown files
│   ├── run_tracker.json        # Logs of scraping runs and statistics
│   ├── update_progress.csv     # Progress tracking for URL processing
│   └── url_status_updates.csv  # Status updates for URLs
├── md_files/                   # Raw scraped Markdown files
├── md_files_trimmed/           # Trimmed and cleaned Markdown files
├── src_lib/                    # Source PDF files containing URLs
├── src_lib_test/               # Test PDF files
├── oldCode/                    # Legacy code versions
└── __pycache__/                # Python bytecode cache
```

---

## Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd SiteScraper
   ```

2. **Install Python dependencies**:

   ```bash
   pip install cloudscraper beautifulsoup4 pdfx PyPDF2 pandas
   ```

3. **Ensure required directories exist** (they will be created automatically by the scripts):
   - `md_files/`
   - `md_files_trimmed/`
   - `data/`

---

## Usage

### Running the Full Pipeline

Execute the main scraping routine:

```bash
python routine_run.py
```

This script will:

1. Extract URLs from all PDF files in the `src_lib/` directory
2. Scrape content from the extracted URLs
3. Convert articles to Markdown format
4. Trim the Markdown files to remove references and footers
5. Update progress tracking and metadata

### Individual Components

- **Extract URLs from PDFs**:

  ```python
  from links_to_csv import extract_urls_from_pdfs
  extract_urls_from_pdfs()
  ```

- **Process specific PMC articles**:

  ```python
  from process_pmc_fulltext import save_markdown
  # Use within the scraping workflow
  ```

- **Trim existing Markdown files**:
  ```python
  from trim_md_files import trim_markdown_files
  trim_markdown_files("md_files", "md_files_trimmed")
  ```

---

## Configuration

### Stop Headers and Phrases

The trimming process removes content after certain headers and phrases. These are defined in `trim_md_files.py` and `routine_run.py`:

- Headers like "References", "Bibliography", "Acknowledgments"
- Phrases like "If you would like to reproduce some or all of this content"

Modify the `STOP_HEADERS` and `STOP_PHRASES` lists to customize trimming behavior.

### Directories

- `MD_FILE_STORAGE`: Directory for raw Markdown files (default: "md_files")
- `MD_FILES_TRIMMED`: Directory for trimmed Markdown files (default: "md_files_trimmed")
- `SCRAPING_LINKS_DIR`: Directory containing source PDF files (default: "src_lib")

---

## Data Files

- **link_file_status_map.csv**: Maps URLs to their processing status and associated files
- **md_files_metadata.json**: Contains metadata for each processed Markdown file including ID, source, extraction date, and file hash
- **run_tracker.json**: Logs each scraping run with statistics on processed PDFs, links, successes, and failures
- **update_progress.csv**: Tracks the progress of URL processing with status updates

---

## Dependencies

- `cloudscraper`: For bypassing anti-bot measures during web scraping
- `beautifulsoup4`: For HTML parsing and content extraction
- `pdfx`: For extracting URLs from PDF files
- `PyPDF2`: For PDF processing
- `pandas`: For data manipulation and CSV handling
- `hashlib`: For file integrity checking

---

## Output

- **Raw Markdown Files**: Stored in `md_files/` with filenames like `{id}_{title}.md`
- **Trimmed Markdown Files**: Cleaned versions in `md_files_trimmed/`
- **Metadata**: JSON file with detailed information about each processed article

---

## Notes

- The scraper is specifically optimized for PMC (PubMed Central) article structures
- Handles various URL formats and normalizes them during extraction
- Implements batch processing to manage memory and provide progress updates
- Uses file hashing to detect duplicate content

---
