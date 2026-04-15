import os
import json
from typing import List

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def _get_credentials():
    creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )

    creds_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
    if os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )

    raise ValueError('No Google Drive credentials found')


def list_gdrive_files(folder_id: str) -> List[dict]:
    creds = _get_credentials()
    service = build('drive', 'v3', credentials=creds)

    results = []
    page_token = None

    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='nextPageToken, files(id, name, mimeType, size)',
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token
        ).execute()

        files = response.get('files', [])
        for f in files:
            if f.get('mimeType') == 'video/x-matroska':
                results.append({
                    'id': f.get('id'),
                    'name': f.get('name'),
                    'size': int(f.get('size', 0))
                })

        page_token = response.get('nextPageToken')
        if not page_token:
            break

    print(f'[gdrive] Found {len(results)} files in folder {folder_id}')
    return results


if __name__ == '__main__':
    files = list_gdrive_files('1trhkrfBp94vjWyYO-PUaBDy0T80ErWfi')
    for f in files:
        print(f'{f["name"]} - {f["size"]} bytes')