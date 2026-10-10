#!/usr/bin/env python3
"""CLI wrapper: upload an already-recalculated workbook to Google Drive.
Usage: python upload_to_drive.py path/to/file.xlsx
See sync_excel_backup.upload_to_drive() for the required env vars.
"""
import sys

from sync_excel_backup import upload_to_drive

if __name__ == "__main__":
    upload_to_drive(sys.argv[1])
