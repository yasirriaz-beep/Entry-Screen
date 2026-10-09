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
