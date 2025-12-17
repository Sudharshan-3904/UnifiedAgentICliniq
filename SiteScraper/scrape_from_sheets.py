import sheets_sync
import fetch_articles
import time

def process_sheet_rows():
    """
    Fetches rows from Google Sheets, scrapes content for unextracted links,
    and updates the sheet status.
    """
    print("Fetching rows from Google Sheets...")
    rows = sheets_sync.get_all_rows()
    
    if not rows:
        print("No rows found or error fetching rows.")
        return

    print(f"Found {len(rows)} rows to process.")

    # Iterate through rows with index to allow updating the sheet
    for i, row in enumerate(rows):
        # row is a dictionary with keys matching the sheet headers
        # Expected headers: "Index", "Article URL", "Status"
        
        # Handle potential key variations (case-insensitive or slightly different names)
        # We'll normalize to lowercase keys for checking
        normalized_row = {k.lower(): v for k, v in row.items()}
        
        article_id = normalized_row.get('index') or normalized_row.get('id')
        url = normalized_row.get('article url') or normalized_row.get('link') or normalized_row.get('url')
        status = normalized_row.get('status', '').lower()
        
        if not article_id or not url:
            print(f"Skipping row {i+2}: Missing ID or URL")
            continue

        if status == 'extracted':
            print(f"Skipping row {i+2}: Already extracted - {url}")
            continue

        print(f"Processing row {i+2}: {url}")
        
        # Perform extraction
        # We pass an empty list for updated_rows because we are managing status updates directly via sheets
        success = fetch_articles.extract_medlineplus_page(url, article_id, [])

        if success:
            # Update status in Google Sheets
            # Row index is i + 2 (1-based index, +1 because data starts at row 2)
            sheets_sync.update_status(i + 2, "extracted")
            print(f"Successfully scraped and updated status for row {i+2}")
        else:
            print(f"Failed to scrape content for row {i+2}")
            # Optionally update status to 'failed' if desired, or leave as 'yet'
            # sheets_sync.update_status(i + 2, "failed")

        # Sleep briefly to be nice to the server
        time.sleep(1)

if __name__ == "__main__":
    process_sheet_rows()
