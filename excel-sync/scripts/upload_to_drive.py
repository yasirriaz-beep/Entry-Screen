#!/usr/bin/env python3
"""CLI wrapper: upload a file to Google Drive (create-or-overwrite by name).
Usage: python upload_to_drive.py path/to/file.xlsx [mimetype]
The optional second argument lets other backup jobs (e.g. a zipped source
backup) tag the upload correctly instead of inheriting the xlsx default.
See sync_excel_backup.upload_to_drive() for the required env vars.
"""
import sys

from sync_excel_backup import upload_to_drive

if __name__ == "__main__":
    mimetype = sys.argv[2] if len(sys.argv) > 2 else None
    upload_to_drive(sys.argv[1], mimetype=mimetype)
