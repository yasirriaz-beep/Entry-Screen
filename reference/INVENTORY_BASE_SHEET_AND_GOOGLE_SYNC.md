# Inventory BASE balance sheet & Google Sheets sync (2026-10-10)

Reference notes for future sessions. Covers the rework of `stock-count.html` to
show an explicit Beginning/Add/Sub/Ending breakdown "like Excel" (the owner's
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
input and a variance tag), matching the layout the owner used in Excel. No new
math was introduced — this was a display change over the same formula.

## Physical-count cadence banner

The owner's rule: the physical balance must be checked **every 2 days by Store
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

## Google Sheet: "C-5 (C-5) Inventory Balance Sheet"

A live-sync target was created in the owner's Google Drive (not a template match —
he confirmed there was no pre-existing item-level BASE sheet to mirror; the
old monthly C-5 files only had a branch-level inventory rollup). Columns:
`Category, Item, Unit, Beginning, Add (Purchases), Sub (Issuance), Ending
(Calculated), Physical Count, Variance, Last Synced` — one row per active
product (665 rows as of creation), seeded from a one-time SQL snapshot.

## Automatic sync: Supabase Edge Function + pg_cron

The owner asked for **true automatic sync**, not just an on-demand export button.

- **Edge Function `sync-inventory-to-sheets`** (deployed, `verify_jwt:
  false`) — recomputes the same BASE formula server-side for every active
  product at the C-5 location, then authenticates to the Google Sheets
  API as a service account (builds and signs its own JWT with Web Crypto,
  exchanges it for an OAuth access token) and overwrites the sheet's data
  range with the fresh values.
- **pg_cron job `sync-inventory-to-sheets-nightly`** (migration
  `schedule_inventory_sheet_sync`) — fires at 20:00 UTC (≈01:00 AM PKT, after
  the business day's close) and calls the function via `net.http_post`
  (`pg_cron` + `pg_net` extensions, enabled in the same migration).

### One-time setup still needed from the owner before this actually syncs

The function is deployed and scheduled, but it has **no credentials yet** —
Supabase Edge Function secrets are entered by the user directly in the
Supabase dashboard, never through Claude, so this step cannot be done by an
AI session. Three secrets need values (Supabase Dashboard → Edge Functions →
`sync-inventory-to-sheets` → Secrets, or project-level Secrets):

1. **Create a Google Cloud service account** (console.cloud.google.com → a
   project → APIs & Services → enable "Google Sheets API" → IAM & Admin →
   Service Accounts → Create → download its JSON key).
2. **Share the Google Sheet** ("C-5 (C-5) Inventory Balance Sheet") with
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

The owner's separate, earlier ask: keep **`FNK_Gulberg_Master_Workbook.xlsx`** (the
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
   `v_excel_sync_purchase_orders`, `v_excel_sync_issue_log`, all C-5-only,
   granted to `service_role` only), fully rewrites rows 5+ of the four input
   sheets from that data (every run is a clean regenerate, not an append —
   simpler and can't double-count), fills in each row's own per-row formulas
   (Item Name/Unit/Rate lookups, Cash Impact, etc.) by copying row 5's formula
   pattern down, and saves the result. Tested locally against real C-5
   rows pulled via SQL — recalculates with 0 formula errors and the numbers
   roll up correctly (verified Dashboard total, Inventory closing stock for a
   few items by hand).
3. **`excel-sync/scripts/recalc.py`** — same LibreOffice recalculation step
   the rest of this project's Excel work uses, so the uploaded copy always
   has baked-in values, not just formula text.
4. **`excel-sync/scripts/upload_to_drive.py`** — creates (first run) or
   overwrites (every run after) one file in Google Drive via a service
   account, so the shareable link never changes, and shares it with the owner's
   email if `EXCEL_BACKUP_NOTIFY_EMAIL` is set.
5. **`.github/workflows/sync-excel-backup.yml`** — runs the three steps above
   nightly at 20:05 UTC (5 minutes after the Google Sheet sync, so the two
   jobs never collide on the same service-account token), and can also be
   triggered on demand from the GitHub Actions tab ("Run workflow").

### Known, real limitation — item code mismatch (not yet resolved)

The app's own product catalog (`products.code`, 787 products) and this
workbook's Item Code list (481 codes like `FD-001`) are **two different,
partially-reconciled numbering schemes**. Checking real C-5 data:
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

**Fix, when the owner wants to do it:** either (a) re-code the ~300 unmigrated
`products` rows to the workbook's `FD-`/`PK-`/`CL-`/... scheme (cleanest,
makes the two catalogs genuinely the same list), or (b) add a mapping table
(`product_id -> workbook_item_code`) so the sync can translate without
touching `products.code` itself. Neither has been done yet — this is a
pre-existing data-quality gap in the app's product catalog, not something
introduced by this sync.

### One-time setup needed from the owner (shares the service account above)

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

## October 24 — flour "BAG" and fries "PKT" unit-of-measure correction

The owner flagged a real mismatch: the store had been treating **1 flour
BAG = 50 kg**, but the kitchen has always actually used **10 kg bags**. He
also wanted the fries line items switched from packet-counting to
kilograms outright, since **1 fries PKT = 2.5 kg**.

Investigated before touching anything:

- `products.unit` is just a free-text label (varchar, no CHECK constraint,
  37 distinct values in use) — there is no central "conversion factor"
  column anywhere in the schema for BAG→KG or PKT→KG (the existing
  `floor_count_unit`/`floor_count_factor` pair on `products` is a
  *different* mechanism entirely — it converts a floor-count unit like PCS
  back into the ledger unit like PKT, e.g. "52 wings PCS = 1 PKT"; it is
  unrelated to kg conversion and wasn't touched).
- A `grep` across every `.html` page for `unit === 'PKT'`/`'BAG'`-style
  branching found nothing — `unit` is purely a display string, never used
  in client-side logic, so switching it is safe.
- Checked actual recorded quantities for the flour items (`FD-041`
  MARINATED FRIED FLOUR, `FD-077` PIZZA FLOUR, `1.4.05` AL TAYYAB BREADING
  FLOUR, all unit=BAG/BEG): daily issue quantities are small integers
  (1-4/day) consistent with someone physically counting bags out of the
  store, **not** a kg figure back-computed from an assumed 50 kg/bag. So
  the recorded bag *counts* were never wrong — only the mental "a bag =
  50 kg" conversion was. **No historical quantity data needed rescaling
  for flour.** Fixed only a pre-existing data-entry typo, "BEG" → "BAG"
  (found on `1.4.05`'s product record and on one historical `purchases`
  row for `FD-077`), purely cosmetic, zero $ impact.
  - **Follow-up, same day — this alone wasn't the actual fix the owner
    needed.** He came back saying "flour didn't work" after this first
    pass, because nothing above actually changes anything visible in the
    app — it was pure data-consistency/documentation. The real lever was
    sitting right there in `products`: `floor_count_unit` /
    `floor_count_factor`, the same mechanism already used for ~25 other
    items (e.g. WINGS/DRUMMETTE at "52 PCS = 1 PKT", COLA bottles at
    "6/12 BOTTLE = 1 PET") to let `floor-inventory.html`'s Kitchen tab
    show Beginning/Addition/Ending Count/Usage in a finer physical
    counting unit than the ledger unit, converting both ways
    automatically (see that file's count-unit comment block, ~line 671).
    It was `NULL` for all three BAG flour items, so Kitchen's floor count
    was just showing raw bag counts with no kg option at all. Set
    `floor_count_unit = 'KG'`, `floor_count_factor = 10` on `FD-077`
    PIZZA FLOUR, `FD-041` MARINATED FRIED FLOUR, and `1.4.05` AL TAYYAB
    BREADING FLOUR. Now on the Kitchen tab those three show Beginning /
    Addition / Ending Count / Usage in **KG**, converted at the correct
    10 kg = 1 bag — finally the actual, visible fix. By existing design
    (not touched here), **Par Qty and Reorder for Store stay in BAG** on
    that same screen — those feed Issue Entry's ledger-unit suggestions
    directly and were deliberately left in packets/bags for every other
    count-unit item too, so this isn't a units mismatch, just the
    established pattern.
  - `1.4.07` VITAL FRIED FLOUR 50 KG was deliberately left alone — it's
    inactive, and its name already states its own real bag size (50 kg),
    so it reads as a genuinely different product line, not part of this
    mix-up.
  - Flagged, not changed: `FD-077` PIZZA FLOUR's `min_stock_level`/
    `reorder_qty` (10 / 50 bags). If those thresholds were ever set with a
    kg target in mind (e.g. "keep ~500 kg on hand"), they now mean far
    less physical flour (10 bags × 10 kg = 100 kg) than originally
    intended and are worth revisiting. Left as-is since there's no way to
    tell from the data whether the number was a bag-count decision or a
    kg-target decision.
- For fries, this **was** a real unit-of-record change, so every
  historical row was rescaled by the conversion factor (×2.5 for
  quantities, ÷2.5 for rates — money amounts are the product of the two,
  so every `amount`/`closing_amount`/etc. column was deliberately left
  untouched and still ties out exactly) across `products`, `purchases`
  (incl. `original_qty`/`original_rate`), `purchase_orders`,
  `daily_issues`, `inventory_snapshots`, `floor_par_levels`,
  `inventory_balance_adjustments`, and the `excel_inventory_staging`
  reference table. Covered: `FD-043` GOLDEN BROWN FRIES, `1.4.02` MAC
  FRIES, `FD-045` OPA FRIES, `FD-138` ZESTY FRIES BLEND. `product_floor_overrides`
  was left untouched — it only overrides a display label, no quantity.
  - One $0.25 cosmetic rounding artifact: a single `purchases` row for
    OPA FRIES had rate 950.02/PKT; divided by 2.5 that's 380.008, but the
    `rate` column only stores 2 decimal places, so it rounded to 380.01.
    The row's `amount` (what actually drives financial totals) was never
    touched and is still exactly correct (47501.00) — only the
    *reconstructed* qty×rate for that one row is 25 paisa off from it.
  - Verified post-migration: per-product sums of rescaled `daily_issues`
    quantities match (old total)×2.5 exactly, and every `amount` column
    checked still equals (new qty)×(new rate) to the cent (except the one
    row above).
