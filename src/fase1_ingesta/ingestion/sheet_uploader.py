import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.common.paths import ROOT, KEYS_DIR

load_dotenv(ROOT / ".env")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = KEYS_DIR / "token.json"
CLIENT_SECRET_PATH = KEYS_DIR / "oauth_client_secret.json"


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise SystemExit(f"No existe {CLIENT_SECRET_PATH}")  # TODO: translate in layer 2
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload_csv_as_sheet(csv_path: Path, sheet_name: str) -> dict:
    output = os.getenv("OUTPUT_FOLDER_ID")
    if not output:
        raise SystemExit("Falta OUTPUT_FOLDER_ID en .env")  # TODO: translate in layer 2
    if not csv_path.exists():
        raise SystemExit(f"No existe el CSV: {csv_path}")  # TODO: translate in layer 2

    service = build("drive", "v3", credentials=_get_credentials())

    metadata = {
        "name": sheet_name,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [output],
    }
    media = MediaFileUpload(str(csv_path), mimetype="text/csv", resumable=False)
    return (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )