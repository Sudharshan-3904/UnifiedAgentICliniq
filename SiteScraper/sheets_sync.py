import pygsheets
import config

def get_sheets_client():
    """
    Authenticates with Google Sheets API using service account credentials via pygsheets.
    """
    try:
        # pygsheets.authorize handles the service account file directly
        client = pygsheets.authorize(service_file=config.SERVICE_ACCOUNT_FILE)
        return client
    except Exception as e:
        print(f"Error authenticating with Google Sheets: {e}")
        return None

def get_worksheet():
    """
    Helper to get the worksheet object.
    """
    client = get_sheets_client()
    if not client:
        return None

    try:
        sh = client.open_by_key(config.GOOGLE_SHEET_ID)
        try:
            wks = sh.worksheet_by_title(config.SHEET_NAME)
        except pygsheets.WorksheetNotFound:
            print(f"Worksheet '{config.SHEET_NAME}' not found. Using the first worksheet.")
            wks = sh[0]
        return wks
    except Exception as e:
        print(f"Error accessing worksheet: {e}")
        return None

def get_all_rows():
    """
    Fetches all rows from the Google Sheet.
    Returns a list of dictionaries (using the first row as headers).
    """
    wks = get_worksheet()
    if not wks:
        return []
    
    try:
        # get_all_records returns a list of dictionaries
        return wks.get_all_records()
    except Exception as e:
        print(f"Error fetching rows: {e}")
        return []

def update_status(row_index, status):
    """
    Updates the status column for a specific row index (1-based, but accounting for header).
    Args:
        row_index (int): The row number in the spreadsheet (1-based).
        status (str): The new status value.
    """
    wks = get_worksheet()
    if not wks:
        return

    try:
        # Assuming 'Status' is the 3rd column (C)
        # You might want to find the column index dynamically if headers change
        wks.update_value((row_index, 3), status)
        print(f"Updated row {row_index} status to '{status}'")
    except Exception as e:
        print(f"Error updating status for row {row_index}: {e}")

def update_sheet_with_csv_data(csv_data):
    """
    Updates the entire Google Sheet with data from the CSV file.
    Args:
        csv_data (list of dict): List of rows from the CSV file.
    """
    wks = get_worksheet()
    if not wks:
        return

    try:
        # Prepare data for upload
        # Headers: Index, Article URL, Status
        headers = ["Index", "Article URL", "Status"]
        matrix = [headers]
        
        for row in csv_data:
            matrix.append([row['id'], row['link'], row['status']])
            
        # Clear existing content and update with new data
        wks.clear()
        wks.update_values('A1', matrix)
        print("Google Sheet updated successfully.")
        
    except Exception as e:
        print(f"Error updating Google Sheet: {e}")
