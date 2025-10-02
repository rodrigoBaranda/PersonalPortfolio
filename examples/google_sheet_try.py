import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def read_google_sheet(credentials_file, spreadsheet_id, sheet_name):
    """
    Read a Google Sheet and return data as a pandas DataFrame

    Args:
        credentials_file (str): Path to your service account JSON credentials file
        spreadsheet_id (str): The ID of your Google Spreadsheet (from the URL)
        sheet_name (str): Name of the sheet/tab to read

    Returns:
        pd.DataFrame: DataFrame containing the sheet data
    """

    # Define the scopes needed for Google Sheets API
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    try:
        # Authenticate using service account credentials
        credentials = Credentials.from_service_account_file(
            credentials_file,
            scopes=SCOPES
        )

        # Build the Google Sheets API service
        service = build('sheets', 'v4', credentials=credentials)

        # Call the Sheets API to get data
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()

        values = result.get('values', [])

        if not values:
            print(f'No data found in sheet: {sheet_name}')
            return pd.DataFrame()

        # Convert to DataFrame (first row as headers)
        df = pd.DataFrame(values[1:], columns=values[0])

        print(f"Successfully loaded {len(df)} rows from sheet '{sheet_name}'")
        return df

    except HttpError as error:
        print(f'An error occurred: {error}')
        return None
    except Exception as e:
        print(f'Error: {e}')
        return None


# Example usage
if __name__ == "__main__":
    # Configuration
    CREDENTIALS_FILE = "/Users/r.baranda.castrillo/PycharmProjects/PersonalPortfolio/credentials.json"  # Update this path
    SPREADSHEET_ID = "1RM2XfdHkKu0ayjZIxZeEHi7Ck6xuOXlWba_m0i_Rg6A"  # Extract from Google Sheets URL
    SHEET_NAME = "Copia de Transactions"  # Name of the sheet/tab

    # Read the Google Sheet
    df = read_google_sheet(CREDENTIALS_FILE, SPREADSHEET_ID, SHEET_NAME)

    if df is not None:
        # Display the first few rows
        print("\nDataFrame Preview:")
        print(df.head())

        # Display basic info
        print(f"\nShape: {df.shape}")
        print(f"Columns: {list(df.columns)}")