# Security hardening — October 2026

Why this exists: the app is a static HTML/JS site that talks directly to
Supabase using the public `anon` key, which is embedded in every page's
source code. That's a normal, supported Supabase pattern **only if** the
database's row-level security (RLS) is doing the real enforcement — the
PIN screen on every page is a UI convenience, not a security boundary, since
anyone can read the anon key out of the page source and call the REST API
directly.

Running Supabase's own security advisor turned up several real gaps. This
file records what was found, what was fixed, and what's intentionally left
for a later pass.

## What was actually wrong

1. **Every write was forgeable.** Policies like "allow this insert if a row
   exists in `app_users` with this id and role" only checked that *some*
   user with that role existed — not that the person making the request was
   actually authenticated as them. Since `app_users` (names, emails, roles,
   location) was itself fully public to read, anyone could look up e.g. a
   director's id and submit a fake expense, cash count, payroll entry, or PO
   approval attributing it to that director — without ever knowing their PIN.
2. **PIN checks had no rate limit.** `verify_owner_pin` / `verify_manager_pin`
   were plain database functions callable directly over the REST API. A
   scripted brute-force attempt against a 4-6 digit PIN was realistic.
3. **Two tables had RLS disabled entirely**: `expense_categories`,
   `expense_subcategories` — no protection at all, by anyone, for any
   operation.
4. **Four `SECURITY DEFINER` views** (`v_excel_sync_*`, built for the nightly
   Excel-backup GitHub Action, which uses the `service_role` key) were also
   grant-accessible to `anon`/`authenticated`, which would have let anyone
   read sales/expense/purchase-order/issue data for C-5 through them,
   bypassing RLS on the underlying tables entirely.
5. **23 functions** had a mutable `search_path` (a schema-hijacking vector)
   and several `SECURITY DEFINER` functions were executable by `anon` with
   no real need.

## What was fixed

- **RLS enabled** on `expense_categories` / `expense_subcategories`, with
  policies requiring a real session for writes (see below).
- **`search_path` pinned** (`public, extensions`) on every flagged function.
- **PIN brute-force lockout**: `pin_attempt_throttle` table +
  `register_pin_attempt()` / `check_pin_not_locked()`. 5 wrong PINs against
  the same manager (or the owner PIN) locks that one target out for 15
  minutes. Verified end-to-end, including that a *correct* PIN is still
  rejected while locked.
- **Real session identity**, closing the write-forgery hole:
  - `login_sessions` table + `issue_login_session()` issue a random,
    SHA-256-hashed bearer token on every successful `verify_manager_pin()`
    call (16-hour expiry).
  - `current_session_claims()` reads that token back from the
    `x-fnk-session` request header (via Postgres's standard
    `request.headers` GUC that PostgREST populates on every request — no
    special server config needed) and resolves it to the real
    `app_user_id` / `role` / `location_id` / `manager_id`.
  - Every one of the app's 32 write policies (across `attendance_entries`,
    `cash_safe_ledger`, `daily_issues`, `daily_sales`, `employees`,
    `expenses`, `food_panda_settlements`, `inventory_snapshots`,
    `payroll_entries`, `products`, `purchase_orders`, `purchases`,
    `role_todos`, `vendor_payments`, `vendors`) now ALSO requires
    `current_session_app_user_id() = <the column claiming "who did this">`,
    on top of the existing role/location checks. A request with no session,
    an expired session, or someone else's claimed identity is rejected.
  - **Frontend**: `session.js` exposes `AppSession.authHeaders()`; every
    page's `sb()`/`sbRpc()` helper now spreads it into its fetch headers, and
    every page's login flow stores the `session_token` `verify_manager_pin`
    now returns. All 35 pages were patched (mechanically, then syntax- and
    pattern-verified) in one pass, so there's no partial rollout to track.
  - Verified directly against the live database by impersonating the `anon`
    role and simulating the request header: a legitimate write (matching
    session) succeeds; a write with no session is rejected; a write where an
    authenticated shift manager tries to claim a director's identity is
    rejected. All three behaved as intended.
- **Revoked `anon`/`authenticated` access** to the four `v_excel_sync_*`
  views — they're only ever queried by the nightly backup job, which uses
  the `service_role` key and was never affected by this change.
- **Retired** the short-lived `verify_manager_pin_v2` helper created mid-way
  through this work (superseded by adding the token straight onto
  `verify_manager_pin` itself) — left in place but with execute revoked, so
  it's inert rather than another function to track.

## Deliberately left for a separate pass

- **Read exposure.** Anon can still `SELECT` nearly everything (sales, cash,
  payroll, employees, expenses). Writes are now provably tied to a real
  session; reads are not. Closing that fully means auditing what each page
  actually needs to read and moving the sensitive ones behind session-gated
  RPCs instead of open table grants — a bigger, separate piece of work, not
  done here to avoid breaking page loads blind.
- **`auth_leaked_password_protection`**: a Supabase Auth dashboard toggle
  (Authentication → Policies). This app doesn't use Supabase Auth for login
  (the PIN system is custom), so it's low-stakes, but it's a 30-second
  manual toggle in the dashboard, not something fixable from SQL.
- **`extension_in_public`** (pgcrypto, pg_graphql installed in the `public`
  schema): cosmetic/best-practice, but moving an extension's schema is a
  real migration with its own risk for modest benefit. Every new function
  added here already sets `search_path = public, extensions` in
  anticipation of that move happening later.
- Two short-lived test sessions (one director, one shift manager) were
  created in `login_sessions` while verifying this work; they expire on
  their own within 16 hours and grant nothing beyond what those two people
  already have.

## For anyone touching this later

- A client calling `verify_manager_pin` gets back `session_token` now —
  store it (`AppSession.set` already does) and send it as `x-fnk-session` on
  every subsequent call (`AppSession.authHeaders()` already does).
- Any *new* write policy on a table that records "who did this" should
  include `current_session_app_user_id() = <that column>` from the start,
  not just the role/location check — that's the whole lesson of this pass.
- `DROP FUNCTION` and plain `DELETE` occasionally time out against this
  project through the Supabase MCP tool even though they succeed almost
  instantly server-side (confirmed via `pg_stat_activity` — nothing was
  actually blocking). `ALTER FUNCTION ... RENAME`, `CREATE OR REPLACE
  FUNCTION` (same signature), and `ALTER POLICY` were all reliable; prefer
  those over `DROP` where there's a choice.
