import os.path
import pickle
import sqlite3
import urllib.parse

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def create_table_if_not_exists(db_filename):
    sqlite_connection = sqlite3.connect(db_filename)
    cursor = sqlite_connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_media (
            id TEXT PRIMARY KEY,
            isChecked BOOL,
            isDeleted BOOL,
            productUrl TEXT,
            mimeType TEXT,
            creationTime TEXT,
            filename TEXT
        )
    ''')

    # Create the 'script_data' table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS script_data (
            last_processed_page TEXT PRIMARY KEY
        )
    ''')

    sqlite_connection.commit()
    cursor.close()


def insert_or_update_media(db_filename, item):
    sqlite_connection = sqlite3.connect(db_filename)
    cursor = sqlite_connection.cursor()
    filename_decoded = urllib.parse.unquote(item["filename"])
    item_data = (
        item["id"],
        item["productUrl"],
        item["mimeType"],
        item["mediaMetadata"]['creationTime'],
        filename_decoded
    )

    # First, try to update the existing row
    cursor.execute(f"""
        UPDATE uploaded_media 
        SET productUrl = ?,  mimeType = ?, creationTime = ?, filename = ? 
        WHERE id = ?
    """, (*item_data[1:], item_data[0]))

    # If no row was updated, insert a new one
    if cursor.rowcount == 0:
        cursor.execute(f"INSERT INTO uploaded_media (id,productUrl,mimeType,creationTime,filename) VALUES (?,?,?,?,?)", item_data)

    cursor.close()
    sqlite_connection.commit()


def new_service():
    credentialsFile = 'credentials.json'  # Please set the filename of credentials.json
    pickleFile = 'token.pickle'  # Please set the filename of pickle file.

    SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
    creds = None
    if os.path.exists(pickleFile):
        with open(pickleFile, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentialsFile, SCOPES)
            creds = flow.run_local_server()
        with open(pickleFile, 'wb') as token:
            pickle.dump(creds, token)

    photos_api = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
    return photos_api

def get_photos_page(photos_api, next_page_token):
    pageSize = 100 # 100 is Max
    items_request = photos_api.mediaItems().list(pageSize=pageSize, pageToken=next_page_token)
    response = items_request.execute()
    items = response.get('mediaItems', [])
    next_page_token = response.get('nextPageToken') or False
    return items, next_page_token

def update_page_token(db_filename, next_page_token):
    sqlite_connection = sqlite3.connect(db_filename)
    cursor = sqlite_connection.cursor()
    
    # Check if the first row exists
    cursor.execute("SELECT ROWID FROM script_data WHERE ROWID = 1")
    row = cursor.fetchone()
    
    if row:
        # Update the existing row
        cursor.execute("UPDATE script_data SET last_processed_page = ? WHERE ROWID = 1", (next_page_token,))
    else:
        # Insert a new row
        cursor.execute("INSERT INTO script_data (ROWID, last_processed_page) VALUES (1, ?)", (next_page_token,))
    
    cursor.close()
    sqlite_connection.commit()


def get_page_token(db_filename):
    sqlite_connection = sqlite3.connect(db_filename)
    cursor = sqlite_connection.cursor()
    cursor.execute("SELECT last_processed_page FROM script_data WHERE ROWID = 1")
    row = cursor.fetchone()
    cursor.close()
    sqlite_connection.close()

    if row:
        return row[0] if row[0] != '0' else None
    else:
        return None

def main():
    photos_api = new_service()
    db_filename = "photos_db.sqlite"
    create_table_if_not_exists(db_filename)
    next_page_token = get_page_token(db_filename)
    while True:
        update_page_token(db_filename, next_page_token)
        items, next_page_token = get_photos_page(photos_api, next_page_token)
        for item in items:
            print(item['filename'])
            insert_or_update_media(db_filename, item)
        if not next_page_token:
            update_page_token(db_filename, next_page_token)
            break


if __name__ == '__main__':
    main()
