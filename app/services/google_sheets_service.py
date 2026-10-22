import re
import csv
import io
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
import httpx
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self._service = None

    def extract_spreadsheet_id(self, url_or_id: str) -> str:
        """Extract Google Spreadsheet ID from URL or raw ID."""
        cleaned = url_or_id.strip()
        # Direct ID check (Google spreadsheet IDs are typically 44 characters of alphanum, hyphens, underscores)
        if re.match(r'^[a-zA-Z0-9-_]{20,60}$', cleaned):
            return cleaned

        # Match https://docs.google.com/spreadsheets/d/<ID>/...
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', cleaned)
        if match:
            return match.group(1)

        raise ValueError("Invalid Google Sheet URL or ID. Please check the URL format.")

    def _get_api_client(self):
        """Build Google Sheets API client if credentials exist."""
        if self._service is not None:
            return self._service

        from googleapiclient.discovery import build

        # 1. Service account file
        if settings.GOOGLE_SERVICE_ACCOUNT_FILE and settings.GOOGLE_SERVICE_ACCOUNT_FILE.strip():
            from google.oauth2 import service_account
            try:
                creds = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                self._service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
                return self._service
            except Exception as e:
                logger.warning(f"Failed to load service account file: {e}")

        # 2. Service account JSON in env
        if settings.GOOGLE_SERVICE_ACCOUNT_JSON and settings.GOOGLE_SERVICE_ACCOUNT_JSON.strip():
            from google.oauth2 import service_account
            try:
                info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                creds = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                self._service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
                return self._service
            except Exception as e:
                logger.warning(f"Failed to load service account JSON: {e}")

        # 3. API Key
        if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY.strip():
            try:
                self._service = build('sheets', 'v4', developerKey=settings.GOOGLE_API_KEY, cache_discovery=False)
                return self._service
            except Exception as e:
                logger.warning(f"Failed to initialize Sheets API with API Key: {e}")

        return None

    def get_spreadsheet_tabs(self, url_or_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Fetch available tabs/sheets in the spreadsheet."""
        spreadsheet_id = self.extract_spreadsheet_id(url_or_id)
        api_client = self._get_api_client()

        if api_client:
            try:
                sheet_metadata = api_client.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                title = sheet_metadata.get('properties', {}).get('title', 'Spreadsheet')
                sheets = sheet_metadata.get('sheets', [])
                tabs = []
                for s in sheets:
                    props = s.get('properties', {})
                    tabs.append({
                        "title": props.get('title', 'Sheet1'),
                        "sheet_id": props.get('sheetId', 0),
                        "row_count": props.get('gridProperties', {}).get('rowCount', 0)
                    })
                if tabs:
                    return title, tabs
            except Exception as e:
                err_str = str(e).lower()
                if "permission" in err_str or "403" in err_str:
                    logger.warning("Google Sheets API 403. Trying public gviz export fallback.")
                else:
                    logger.warning(f"Google Sheets API query failed: {e}. Trying public gviz export fallback.")

        # Fallback: Query public gviz endpoints or fallback to standard tab
        # For public sheets or when service account is not yet configured on server
        tabs = self._fetch_public_tabs(spreadsheet_id)
        return "Connected Spreadsheet", tabs

    def _fetch_public_tabs(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Discover tabs for a shared spreadsheet via edit HTML or gviz endpoint."""
        # 1. Try discovering tabs from Google Sheets public web interface
        try:
            edit_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(edit_url)
                if res.status_code == 200:
                    text = res.text
                    # Extract tab titles rendered by Google Sheets UI
                    titles = re.findall(r'docs-sheet-tab-caption[\x22\x27]>([^<]+)<', text)
                    if titles:
                        unique_titles = []
                        seen = set()
                        for t in titles:
                            t_clean = t.strip()
                            if t_clean and t_clean not in seen:
                                seen.add(t_clean)
                                unique_titles.append(t_clean)
                        if unique_titles:
                            return [
                                {"title": title, "sheet_id": idx, "row_count": 0}
                                for idx, title in enumerate(unique_titles)
                            ]
        except Exception as e:
            logger.warning(f"Public edit page tab discovery failed: {e}")

        # 2. Fallback to gviz discovery endpoint
        try:
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:json"
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200:
                    text = res.text
                    json_str_match = re.search(r'setResponse\((.*)\);', text)
                    if json_str_match:
                        data = json.loads(json_str_match.group(1))
                        return [{"title": "Sheet1", "sheet_id": 0, "row_count": len(data.get("table", {}).get("rows", [])) + 1}]
        except Exception as e:
            logger.warning(f"Gviz discovery failed: {e}")

        # Return default Sheet1 tab if discovery endpoint couldn't resolve
        return [{"title": "Sheet1", "sheet_id": 0, "row_count": 0}]

    def read_sheet_data(self, url_or_id: str, tab_name: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Reads the spreadsheet header row and participant rows.
        Returns (headers, list of row dicts).
        """
        spreadsheet_id = self.extract_spreadsheet_id(url_or_id)
        api_client = self._get_api_client()

        if api_client:
            try:
                range_name = f"'{tab_name}'!A1:ZZ"
                result = api_client.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                rows = result.get('values', [])
                if not rows:
                    return [], []
                
                headers = [str(col).strip() for col in rows[0] if str(col).strip()]
                data_rows = []
                for i, row in enumerate(rows[1:], start=2):
                    # Pad row if shorter than headers
                    padded = row + [""] * (len(headers) - len(row))
                    row_dict = {headers[idx]: str(padded[idx]).strip() for idx in range(len(headers))}
                    row_dict["_row_number"] = i
                    data_rows.append(row_dict)
                return headers, data_rows
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"API read failed: {e}. Trying public CSV export.")
                if "403" in err_str or "permission" in err_str:
                    pass

        # Fallback to public CSV export URL
        # e.g., https://docs.google.com/spreadsheets/d/<ID>/gviz/tq?tqx=out:csv&sheet=<tab_name>
        quoted_tab = urllib.parse.quote(tab_name)
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={quoted_tab}"
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(csv_url)
                if resp.status_code == 200:
                    content = resp.text
                    f = io.StringIO(content)
                    reader = csv.reader(f)
                    all_lines = list(reader)
                    if not all_lines:
                        return [], []
                    headers = [c.strip() for c in all_lines[0] if c.strip()]
                    data_rows = []
                    for i, row in enumerate(all_lines[1:], start=2):
                        if not any(c.strip() for c in row):
                            continue
                        padded = row + [""] * (len(headers) - len(row))
                        row_dict = {headers[idx]: str(padded[idx]).strip() for idx in range(len(headers))}
                        row_dict["_row_number"] = i
                        data_rows.append(row_dict)
                    return headers, data_rows
                elif resp.status_code in (401, 403):
                    raise PermissionError(
                        "Google Sheet access denied (403). Please either:\n"
                        "1. Change Google Sheet sharing to 'Anyone with the link can view', or\n"
                        "2. Share the Google Sheet with your Google Cloud Service Account, or\n"
                        "3. Configure GOOGLE_API_KEY / Service Account credentials in backend settings."
                    )
                else:
                    raise RuntimeError(f"Failed to fetch spreadsheet data (HTTP {resp.status_code}).")
        except PermissionError:
            raise
        except Exception as ex:
            raise RuntimeError(f"Could not read spreadsheet: {str(ex)}")

    def get_demo_participants(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Provides high-quality demo participant data for immediate testing and verification."""
        headers = ["Name", "Competition", "Position", "Year", "Date"]
        demo_rows = [
            {"Name": "Surya Arish", "Competition": "Web Development Hackathon", "Position": "1st Place (Winner)", "Year": "2026", "Date": "October 2026", "_row_number": 2},
            {"Name": "Rahul Kumar", "Competition": "Web Development Hackathon", "Position": "Runner Up", "Year": "2026", "Date": "October 2026", "_row_number": 3},
            {"Name": "Priya Sharma", "Competition": "Web Development Hackathon", "Position": "Outstanding Participant", "Year": "2026", "Date": "October 2026", "_row_number": 4},
            {"Name": "Anita Desai", "Competition": "Web Development Hackathon", "Position": "Special Commendation", "Year": "2026", "Date": "October 2026", "_row_number": 5},
            {"Name": "Vikram Malhotra", "Competition": "Web Development Hackathon", "Position": "Finalist", "Year": "2026", "Date": "October 2026", "_row_number": 6},
            {"Name": "Sneha Patel", "Competition": "Web Development Hackathon", "Position": "Honorable Mention", "Year": "2026", "Date": "October 2026", "_row_number": 7},
            {"Name": "Arjun Das", "Competition": "Web Development Hackathon", "Position": "Participant", "Year": "2026", "Date": "October 2026", "_row_number": 8},
            {"Name": "Kavita Rao", "Competition": "Web Development Hackathon", "Position": "Participant", "Year": "2026", "Date": "October 2026", "_row_number": 9},
        ]
        return headers, demo_rows

google_sheets_service = GoogleSheetsService()
