
"""
╔══════════════════════════════════════════════════════════════╗
║         SHAAYARI AUTO-BACKUP — Google Drive Sync             ║
║         Runs every Sunday, downloads all shaayaris           ║
║         from your Google Drive → Laptop automatically        ║
╚══════════════════════════════════════════════════════════════╝

FIRST TIME SETUP:
  pip install google-auth google-auth-oauthlib google-api-python-client

Then follow GOOGLE_SETUP.txt to get your credentials.json file.
"""

import os
import io
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ──────────────────────────────────────────────
# ⚙️  CONFIGURATION — Edit these if needed
# ──────────────────────────────────────────────

# Your Google Drive folder name (exact name)
DRIVE_FOLDER_NAME = "Shaayari"

# Where to save backups on your laptop
BACKUP_ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Shaayari_Backups")

# Google API scope — read only, we don't touch your Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Credentials file (you'll get this from Google Cloud Console)
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")

# ──────────────────────────────────────────────
# 🔧 FUNCTIONS
# ──────────────────────────────────────────────

def log(msg, emoji=""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {emoji}  {msg}")

def authenticate():
    """Login to Google Drive. Only asks permission on first run."""
    creds = None

    # Load saved token if exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, ask user to login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                log("credentials.json not found!", "❌")
                log("Please follow GOOGLE_SETUP.txt to get your credentials.", "")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next time (no login needed again)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        log("Google account connected! Won't ask again.", "✅")

    return creds

def get_shaayari_folder_id(service):
    """Find the Shaayari folder in Google Drive."""
    results = service.files().list(
        q=f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()

    folders = results.get("files", [])
    if not folders:
        log(f"Folder '{DRIVE_FOLDER_NAME}' not found in your Google Drive!", "❌")
        log("Make sure the folder name matches exactly (capital S in Shaayari)", "")
        return None

    log(f"Found folder: {folders[0]['name']}", "📁")
    return folders[0]["id"]

def get_all_files(service, folder_id):
    """Get list of all .txt files in the Shaayari folder."""
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, modifiedTime, size)",
        pageSize=500
    ).execute()

    files = results.get("files", [])
    log(f"Found {len(files)} shaayaris in Drive", "📝")
    return files

def download_file(service, file_id, file_name, save_dir):
    """Download a single file from Drive."""
    request = service.files().get_media(fileId=file_id)
    filepath = os.path.join(save_dir, file_name)

    with io.FileIO(filepath, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return filepath

def sync_shaayaris():
    """Main sync function — downloads all shaayaris from Drive."""

    print("\n" + "═" * 55)
    print("   🌙  SHAAYARI BACKUP — Google Drive Sync")
    print("═" * 55 + "\n")

    # Step 1: Authenticate
    log("Connecting to Google Drive...", "🔐")
    creds = authenticate()
    if not creds:
        return

    service = build("drive", "v3", credentials=creds)
    log("Connected!", "✅")

    # Step 2: Find Shaayari folder
    folder_id = get_shaayari_folder_id(service)
    if not folder_id:
        return

    # Step 3: Get all files
    files = get_all_files(service, folder_id)
    if not files:
        log("No files found in Shaayari folder!", "⚠️")
        return

    # Step 4: Create dated backup directory
    date_str = datetime.now().strftime("%Y-%m-%d")
    backup_dir = os.path.join(BACKUP_ROOT, date_str, "Shaayari")
    os.makedirs(backup_dir, exist_ok=True)

    # Step 5: Download all files
    log(f"Downloading shaayaris to: {backup_dir}", "💾")
    downloaded = 0
    skipped = 0

    for file in files:
        try:
            download_file(service, file["id"], file["name"], backup_dir)
            downloaded += 1
            print(f"  ✓ {file['name']}")
        except Exception as e:
            skipped += 1
            print(f"  ✗ {file['name']} — {e}")

    # Step 6: Save sync log
    save_sync_log(backup_dir, files, downloaded, skipped)

    print("\n" + "═" * 55)
    log("BACKUP COMPLETE! 🎉", "")
    log(f"Downloaded : {downloaded} shaayaris", "📥")
    if skipped:
        log(f"Skipped    : {skipped} files", "⚠️")
    log(f"Saved to   : {backup_dir}", "📁")
    print("═" * 55 + "\n")

def save_sync_log(backup_dir, files, downloaded, skipped):
    """Save a log of what was synced."""
    log_path = os.path.join(backup_dir, "_SYNC_LOG.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("╔══════════════════════════════════════╗\n")
        f.write("║       SHAAYARI SYNC LOG              ║\n")
        f.write("╚══════════════════════════════════════╝\n\n")
        f.write(f"Sync Date  : {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n")
        f.write(f"Downloaded : {downloaded}\n")
        f.write(f"Skipped    : {skipped}\n")
        f.write(f"Total      : {len(files)}\n\n")
        f.write("FILES:\n")
        f.write("─" * 40 + "\n")
        for file in files:
            f.write(f"  • {file['name']}\n")

# ──────────────────────────────────────────────
# 🚀 RUN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    sync_shaayaris()
    input("\nPress Enter to exit...")
