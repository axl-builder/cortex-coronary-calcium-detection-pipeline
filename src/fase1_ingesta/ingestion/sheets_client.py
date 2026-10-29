import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

from src.common.paths import ROOT, KEYS_DIR

load_dotenv(ROOT / ".env")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = KEYS_DIR / "totemic-fact-512412-b2-0b22c81830ff.json"


def _build_service():
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def fetch_selected_sheets(reciente: str, antigua: str) -> tuple[dict, list[str]]:
    """
    Devuelve (result, selected_sheets).
    result es el dict crudo de batchGet; selected_sheets son los nombres en orden.
    """
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise SystemExit("Missing SPREADSHEET_ID in .env")

    service = _build_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_names = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

    idx_reciente = sheet_names.index(reciente)
    idx_antigua = sheet_names.index(antigua)

    if idx_reciente <= idx_antigua:
        scope = sheet_names[idx_reciente : idx_antigua + 1]
    else:
        scope = sheet_names[idx_antigua : idx_reciente + 1][::-1]

    selected = [s for s in scope if s.isnumeric() or s == antigua]

    ranges = [f"'{name}'!A:O" for name in selected]
    result = (
        service.spreadsheets()
        .values()
        .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
        .execute()
    )
    return result, selected