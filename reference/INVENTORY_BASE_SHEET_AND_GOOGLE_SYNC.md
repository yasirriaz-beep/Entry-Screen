# Inventory BASE balance sheet & Google Sheets sync (2026-10-10)

Reference notes for future sessions. Covers the rework of `stock-count.html` to
show an explicit Beginning/Add/Sub/Ending breakdown "like Excel" (Yasir's
words), the physical-count cadence rule, and the automatic push into a Google
Sheet in his Drive.

## The BASE formula (already computed before this change, now also displayed)

`stock-count.html`'s `expectedQty(productId, date)` has always computed, per
item, per date:

- **Beginning** = the most recent prior physical count's `closing_qty` for
  that item (0 if it has never been counted)
- **+ Add** = `purchases.qty` (Goods Receipt) summed since that prior count,
  up to the selected date
- **− Sub** = `daily_issues.qty` (Issue Entry) summed over the same window
- **= Ending** = Beginning + Add − Sub

This was always saved to `inventory_snapshots` (`opening_qty`, `purchases_qty`,
`issues_qty`, `closing_qty`) on every save. Before 2026-10-10 the screen only
*displayed* two columns, "Expected" and "Counted" — the four-part breakdown
existed in the data but not on screen. The 2026-10-10 change added explicit
**Beg / Add / Sub / End** columns to the item list (plus the existing Count
input and a variance tag), matching the layout Yasir used in Excel. No new
math was introduced — this was a display change over the same formula.

## Physical-count cadence banner

Yasir's rule: the physical balance must be checked **every 2 days by Store
Person**, and **biweekly (14 days) by Auditor**. `stock-count.html` now shows
a banner (`renderCadenceBanner()`) right after login, keyed off
`state.userRole` (returned by `verify_manager_pin`, see
`ACCESS_CONTROL_AND_PIN_SYSTEM.md`):

- `store_man` role → cadence = 2 days
- `auditor` role → cadence = 14 days
- any other role → no banner

It looks at the most recent `snapshot_date` across *any* item for the
location and compares it to today. This is a **reminder only** — it does not
block counting early or late, and it does not track per-item cadence, only
"has anyone counted anything recently."

## Google Sheet: "Gulberg (C-5) Inventory Balance Sheet"

A live-sync target was created in Yasir's Google Drive (not a template match —
he confirmed there was no pre-existing item-level BASE sheet to mirror; the
old monthly C-5 files only had a branch-level inventory rollup). Columns:
`Category, Item, Unit, Beginning, Add (Purchases), Sub (Issuance), Ending
(Calculated), Physical Count, Variance, Last Synced` — one row per active
product (665 rows as of creation), seeded from a one-time SQL snapshot.

## Automatic sync: Supabase Edge Function + pg_cron

Yasir asked for **true automatic sync**, not just an on-demand export button.

- **Edge Function `sync-inventory-to-sheets`** (deployed, `verify_jwt:
  false`) — recomputes the same BASE formula server-side for every active
  product at the Gulberg location, then authenticates to the Google Sheets
  API as a service account (builds and signs its own JWT with Web Crypto,
  exchanges it for an OAuth access token) and overwrites the sheet's data
  range with the fresh values.
- **pg_cron job `sync-inventory-to-sheets-nightly`** (migration
  `schedule_inventory_sheet_sync`) — fires at 20:00 UTC (≈01:00 AM PKT, after
  the business day's close) and calls the function via `net.http_post`
  (`pg_cron` + `pg_net` extensions, enabled in the same migration).

### One-time setup still needed from Yasir before this actually syncs

The function is deployed and scheduled, but it has **no credentials yet** —
Supabase Edge Function secrets are entered by the user directly in the
Supabase dashboard, never through Claude, so this step cannot be done by an
AI session. Three secrets need values (Supabase Dashboard → Edge Functions →
`sync-inventory-to-sheets` → Secrets, or project-level Secrets):

1. **Create a Google Cloud service account** (console.cloud.google.com → a
   project → APIs & Services → enable "Google Sheets API" → IAM & Admin →
   Service Accounts → Create → download its JSON key).
2. **Share the Google Sheet** ("Gulberg (C-5) Inventory Balance Sheet") with
   that service account's email (from the JSON, `client_email`) as **Editor**
   — a service account only sees sheets explicitly shared with it.
3. Set the three secrets from that JSON key / sheet URL:
   - `GOOGLE_SERVICE_ACCOUNT_EMAIL` = the JSON's `client_email`
   - `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` = the JSON's `private_key`, pasted
     exactly as-is (including the `-----BEGIN/END PRIVATE KEY-----` lines)
   - `GOOGLE_SHEET_ID` = the id segment of the sheet's URL
     (`…/spreadsheets/d/<THIS PART>/edit`)

Once those are set, the nightly cron run will populate the sheet, and it can
also be triggered on demand from the Supabase dashboard ("Invoke function")
for an immediate refresh without waiting for the nightly run.

## Honest limitation

Same posture as the rest of this app: the sync function uses the
`service_role` key server-side (bypassing RLS by design, since it's a trusted
backend job, not a user-facing anon call) and a Google service account with
Editor access to one specific sheet. If the three secrets above are ever
rotated or revoked, the sync silently stops (the cron job keeps firing, but
the function returns an error) — there is no alerting on that failure in this
build.

## Excel master workbook — automatic backup sync (2026-10-10)

Yasir's separate, earlier ask: keep **`FNK_Gulberg_Master_Workbook.xlsx`** (the
real Excel file he built by hand, with real September 2026 data and live
formulas across 14 sheets — README, Dashboard, P&L Summary, Sales, Food
Panda, Expense Entry, Purchase Orders, Payables, Issue Log, Inventory,
Directors, Payroll, Cash Book, Lists) automatically updated in parallel with
the app, as a data-security backup, while his own daily work stays on the
app's HTML pages. He uploaded the actual file this session (it was never in
Google Drive, which is why earlier Drive searches never found it).

**This is a real, pre-built formula-driven workbook, not a blank template.**
The design actually in the file (confirmed by opening it with `openpyxl`):
Sales/Expense Entry/Purchase Orders/Issue Log are the four input sheets;
everything else (Inventory, Payables, Directors, Payroll's "Charges This
Month", Cash Book, P&L Summary, Dashboard) is 100% formulas (mostly
`SUMIFS`/`VLOOKUP` keyed on a 481-row **Item Code** list like `FD-001`,
`PK-014`) that recompute automatically in Excel from those four sheets — this
is exactly the same BASE-formula idea as `stock-count.html`, just already
built out across the whole P&L, not only inventory.

Google Sheets' API can't write cells into a binary `.xlsx` file directly, so
this needed a different mechanism than the inventory-sheet sync above:

### What was built

1. **`excel-sync/template/FNK_Gulberg_Master_Workbook.xlsx`** — the uploaded
   workbook, with one fix applied: its `SUMIFS`/`VLOOKUP` row-bounds (e.g.
   `Expense Entry!$E$5:$E$954`) were originally sized for ~1 year of data at
   most. Widened to 3,000–6,000 rows per sheet (verified via LibreOffice
   recalc that every Dashboard KPI and every Inventory closing-stock value
   comes out byte-for-byte identical to the original — nothing was changed
   mathematically, only the headroom). The two sheets' own "TOTAL:" formulas
   (`Sales!G406`, `Cash Book!D37`) were relocated to row 3010 so the wider
   ranges don't loop back and sum themselves.
2. **`excel-sync/scripts/sync_excel_backup.py`** — pulls from four read-only
   Supabase views (`v_excel_sync_sales`, `v_excel_sync_expenses`,
   `v_excel_sync_purchase_orders`, `v_excel_sync_issue_log`, all Gulberg-only,
   granted to `service_role` only), fully rewrites rows 5+ of the four input
   sheets from that data (every run is a clean regenerate, not an append —
   simpler and can't double-count), fills in each row's own per-row formulas
   (Item Name/Unit/Rate lookups, Cash Impact, etc.) by copying row 5's formula
   pattern down, and saves the result. Tested locally against real Gulberg
   rows pulled via SQL — recalculates with 0 formula errors and the numbers
   roll up correctly (verified Dashboard total, Inventory closing stock for a
   few items by hand).
3. **`excel-sync/scripts/recalc.py`** — same LibreOffice recalculation step
   the rest of this project's Excel work uses, so the uploaded copy always
   has baked-in values, not just formula text.
4. **`excel-sync/scripts/upload_to_drive.py`** — creates (first run) or
   overwrites (every run after) one file in Google Drive via a service
   account, so the shareable link never changes, and shares it with Yasir's
   email if `EXCEL_BACKUP_NOTIFY_EMAIL` is set.
5. **`.github/workflows/sync-excel-backup.yml`** — runs the three steps above
   nightly at 20:05 UTC (5 minutes after the Google Sheet sync, so the two
   jobs never collide on the same service-account token), and can also be
   triggered on demand from the GitHub Actions tab ("Run workflow").

### Known, real limitation — item code mismatch (not yet resolved)

The app's own product catalog (`products.code`, 787 products) and this
workbook's Item Code list (481 codes like `FD-001`) are **two different,
partially-reconciled numbering schemes**. Checking real Gulberg data:
some products already carry the workbook's own codes (`FD-205`, `CL-008`,
`PK-014`) — those sync perfectly and show up correctly on the Inventory tab.
Others still carry the app's original seed codes (`1.1.00`, `1.3.09`,
`2.3.03`) — those rows still get written into Expense Entry / Purchase
Orders / Issue Log in full (**nothing is ever silently dropped — no data is
lost**, which was the actual point of this backup), but because the code
doesn't match anything in the workbook's own 481-item list, the per-row Item
Name/Unit/Rate lookups show blank and the Inventory/Payables/Directors/
Payroll `SUMIFS` formulas won't count that row. Every synced Expense Entry
sheet gets a note in cell `S1` saying this plainly, so it's visible, not
silent.

**Fix, when Yasir wants to do it:** either (a) re-code the ~300 unmigrated
`products` rows to the workbook's `FD-`/`PK-`/`CL-`/... scheme (cleanest,
makes the two catalogs genuinely the same list), or (b) add a mapping table
(`product_id -> workbook_item_code`) so the sync can translate without
touching `products.code` itself. Neither has been done yet — this is a
pre-existing data-quality gap in the app's product catalog, not something
introduced by this sync.

### One-time setup needed from Yasir (shares the service account above)

Same Google Cloud service account as the inventory-sheet sync can be reused
— just needs two more things:
1. Enable the **Google Drive API** on the same GCP project (Sheets API is
   already enabled for the other sync).
2. In the GitHub repo (`yasirriaz-beep/Entry-Screen` → Settings → Secrets and
   variables → Actions), add:
   - `SUPABASE_URL` = `https://wuezcjvmftbkkwfawhtu.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = from Supabase Dashboard → Project Settings
     → API → `service_role` key (**keep this secret** — it bypasses every
     RLS rule in the database)
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = the service account's JSON key file,
     base64-encoded (`base64 -w0 key.json`)
   - `EXCEL_BACKUP_NOTIFY_EMAIL` = `yasir.riaz@gmail.com` (optional — shares
     the Drive file with this address automatically)

No `GDRIVE_FILE_ID` secret is needed — the first run creates the file
("FNK_Gulberg_Master_Workbook_LIVE.xlsx") and every run after that finds and
overwrites the same one by name, so the Drive link stays stable.
