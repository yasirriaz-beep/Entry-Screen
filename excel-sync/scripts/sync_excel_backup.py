#!/usr/bin/env python3
"""
Nightly Excel backup sync — Gulberg (C-5).

Regenerates the four data sheets (Sales, Expense Entry, Purchase Orders,
Issue Log) of the master workbook from Supabase, starting from the template's
own row 5 (the template's baked-in September-2026 rows are treated as the
starting example only — once this sync is live, Supabase is the single
source of truth, so each run fully replaces rows 5+ in those four sheets),
leaving every other sheet's formulas (Inventory, Payables, Directors,
Payroll, Cash Book, P&L Summary, Dashboard) completely untouched — they
recalculate on their own, in Excel, from the rows this script writes.

Env vars required:
  SUPABASE_URL                 e.g. https://wuezcjvmftbkkwfawhtu.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    service-role key (bypasses RLS; read-only views only)
  GOOGLE_SERVICE_ACCOUNT_JSON  base64-encoded service-account key JSON
  GDRIVE_TARGET_FILE_NAME      (optional) defaults to the workbook's own name
  NOTIFY_EMAIL                 (optional) share the Drive file with this address

Known limitation (see reference/INVENTORY_BASE_SHEET_AND_GOOGLE_SYNC.md):
Supabase's `products.code` is a different numbering scheme (e.g. "1.3.14")
than this workbook's own Item Code list (e.g. "FD-001"). Every row is still
written in full (so nothing is ever silently dropped / no data is lost —
that was the whole point of this backup), but a row whose Item Code doesn't
match anything in the workbook's own Item List won't be picked up by the
Inventory / Payables / Directors / Payroll SUMIFS formulas (their Item Name
will just show blank). A "Sync Notes" banner is written into each synced
sheet to make this visible rather than silently missing.
"""
import base64
import json
import os
import re
import sys
from datetime import datetime, date

import requests
import openpyxl

TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "template", "FNK_Gulberg_Master_Workbook.xlsx")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "out", "FNK_Gulberg_Master_Workbook_LIVE.xlsx")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def fetch(view, order):
    url = f"{SUPABASE_URL}/rest/v1/{view}?select=*&order={order}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def as_date(v):
    if not v:
        return None
    if isinstance(v, (date, datetime)):
        return v
    return datetime.strptime(v[:10], "%Y-%m-%d").date()


def fill_down_formula(template_formula: str, target_row: int) -> str:
    """Re-point a row-5 formula's relative row refs ($COL5 -> $COLn) to a new row."""
    return re.sub(r"\$([A-Z]{1,2})5\b", lambda m: f"${m.group(1)}{target_row}", template_formula)


def write_sheet(ws, start_row, rows, column_formula_sources, set_input_cells, note_cell=None, note_text=None):
    """
    Clears everything from start_row down to the sheet's previous max data row,
    then writes `rows` starting at start_row.
    column_formula_sources: {col_letter: formula_string_from_row5} to fill down
      for formula columns that must exist per-row (e.g. Item Name lookups).
    set_input_cells(ws, row, record) -> None: writes the raw input columns.
    """
    # Never clear past row 3000 - the Sales/Cash Book "TOTAL" formulas were
    # deliberately relocated to row 3010 (see excel-sync/template's one-time
    # extend_ranges pass) specifically so a full-range rewrite never touches them.
    old_max = min(ws.max_row, 3000)
    for r in range(start_row, max(old_max, start_row) + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).value = None

    for i, record in enumerate(rows):
        r = start_row + i
        set_input_cells(ws, r, record)
        for col, formula in column_formula_sources.items():
            ws[f"{col}{r}"] = fill_down_formula(formula, r)

    if note_cell and note_text:
        ws[note_cell] = note_text

    print(f"  {ws.title}: wrote {len(rows)} rows starting at {start_row}")


def main():
    wb = openpyxl.load_workbook(TEMPLATE, data_only=False)

    # Capture row-5 per-row formula patterns BEFORE we clear anything.
    sales_formula = {"G": wb["Sales"]["G5"].value}
    expense_formula = {
        "B": wb["Expense Entry"]["B5"].value,
        "G": wb["Expense Entry"]["G5"].value,
        "I": wb["Expense Entry"]["I5"].value,
        "J": wb["Expense Entry"]["J5"].value,
        "P": wb["Expense Entry"]["P5"].value,
        "Q": wb["Expense Entry"]["Q5"].value,
    }
    po_formula = {
        "A": wb["Purchase Orders"]["A5"].value,
        "E": wb["Purchase Orders"]["E5"].value,
        "G": wb["Purchase Orders"]["G5"].value,
        "H": wb["Purchase Orders"]["H5"].value,
        "I": wb["Purchase Orders"]["I5"].value,
    }
    issue_formula = {
        "C": wb["Issue Log"]["C5"].value,
        "D": wb["Issue Log"]["D5"].value,
        "F": wb["Issue Log"]["F5"].value,
        "G": wb["Issue Log"]["G5"].value,
        "J": wb["Issue Log"]["J5"].value,
    }

    print("Fetching from Supabase...")
    sales = fetch("v_excel_sync_sales", "sale_date")
    expenses = fetch("v_excel_sync_expenses", "expense_date")
    pos = fetch("v_excel_sync_purchase_orders", "date_ordered")
    issues = fetch("v_excel_sync_issue_log", "issue_date")
    print(f"  sales={len(sales)} expenses={len(expenses)} pos={len(pos)} issues={len(issues)}")

    # ---- Sales ----
    def sales_set(ws, r, rec):
        ws[f"A{r}"] = as_date(rec["sale_date"])
        ws[f"B{r}"] = rec["dine_in"]
        ws[f"C{r}"] = rec["takeaway"]
        ws[f"D{r}"] = rec["delivery"]
        ws[f"E{r}"] = rec["food_panda"]
        ws[f"F{r}"] = rec["third_party"]

    write_sheet(wb["Sales"], 5, sales, sales_formula, sales_set)

    # ---- Expense Entry ----
    def expense_set(ws, r, rec):
        ws[f"A{r}"] = as_date(rec["expense_date"])
        ws[f"C{r}"] = rec["vendor_or_payee"]
        ws[f"D{r}"] = rec["description"]
        ws[f"E{r}"] = rec["category"]
        ws[f"F{r}"] = rec["item_code"]
        ws[f"H{r}"] = rec["qty"]
        ws[f"K{r}"] = rec["amount"]
        ws[f"M{r}"] = rec["charged_to"]
        ws[f"N{r}"] = rec["entered_by"]
        ws[f"O{r}"] = rec["notes"]

    write_sheet(
        wb["Expense Entry"], 5, expenses, expense_formula, expense_set,
        note_cell="S1",
        note_text=(
            "Auto-synced nightly from the app. Rows whose Item Code shows blank in "
            "column G used a product the app's catalog hasn't matched to this "
            "sheet's Item Code list yet — the transaction amount is still here, "
            "it just won't be counted on the Inventory tab until that's fixed."
        ),
    )

    # ---- Purchase Orders ----
    def po_set(ws, r, rec):
        ws[f"B{r}"] = as_date(rec["date_ordered"])
        ws[f"C{r}"] = rec["vendor"]
        ws[f"D{r}"] = rec["item_code"]
        ws[f"F{r}"] = rec["qty"]
        ws[f"J{r}"] = rec["requested_by"]
        ws[f"K{r}"] = rec["authorized_by"]
        ws[f"L{r}"] = rec["status"]
        ws[f"M{r}"] = as_date(rec["date_received"])

    write_sheet(wb["Purchase Orders"], 5, pos, po_formula, po_set)

    # ---- Issue Log ----
    def issue_set(ws, r, rec):
        ws[f"A{r}"] = as_date(rec["issue_date"])
        ws[f"B{r}"] = rec["item_code"]
        ws[f"E{r}"] = rec["qty"]
        ws[f"H{r}"] = rec["issued_by"]
        ws[f"I{r}"] = rec["issued_to"]

    write_sheet(wb["Issue Log"], 5, issues, issue_formula, issue_set)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    wb.save(OUT_PATH)
    print(f"Saved {OUT_PATH}")
    print(
        "NOTE: formulas are not yet recalculated (openpyxl never caches results) - "
        "run scripts/recalc.py on this file before uploading it anywhere."
    )


def upload_to_drive(local_path):
    """Create-or-overwrite the Drive copy, keeping the same file id (and
    therefore the same shareable link) across every run. Needs:
      GOOGLE_SERVICE_ACCOUNT_JSON  base64 of the service-account key JSON
      GDRIVE_FILE_ID                (optional) reuse a specific existing file
      NOTIFY_EMAIL                  (optional) share with this address as writer
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    key_json = json.loads(base64.b64decode(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]))
    creds = service_account.Credentials.from_service_account_info(
        key_json, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = build("drive", "v3", credentials=creds)

    file_name = os.environ.get(
        "GDRIVE_TARGET_FILE_NAME", "FNK_Gulberg_Master_Workbook_LIVE.xlsx"
    )
    media = MediaFileUpload(
        local_path,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )

    file_id = os.environ.get("GDRIVE_FILE_ID")
    if not file_id:
        existing = drive.files().list(
            q=f"name='{file_name}' and trashed=false",
            fields="files(id,name)",
            spaces="drive",
        ).execute().get("files", [])
        file_id = existing[0]["id"] if existing else None

    if file_id:
        drive.files().update(fileId=file_id, media_body=media).execute()
        print(f"Updated existing Drive file {file_id}")
    else:
        created = drive.files().create(
            body={"name": file_name}, media_body=media, fields="id"
        ).execute()
        file_id = created["id"]
        print(f"Created new Drive file {file_id}")

    notify = os.environ.get("NOTIFY_EMAIL")
    if notify:
        try:
            drive.permissions().create(
                fileId=file_id,
                body={"type": "user", "role": "writer", "emailAddress": notify},
                sendNotificationEmail=False,
            ).execute()
        except Exception as e:  # already shared, or similar - non-fatal
            print(f"  (permission share skipped/failed: {e})")

    print(f"Drive file link: https://drive.google.com/file/d/{file_id}/view")


if __name__ == "__main__":
    main()
