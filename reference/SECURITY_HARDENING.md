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

## October 23 follow-up — cross-branch access fix

While scoping the multi-branch plan (6 branch mirrors + Bakery + FNK Grill,
one shared Supabase backend), found that `app_users.location_id = NULL` is
the existing convention for "this person isn't tied to one branch" — several
policies (`daily_sales`, `cash_transfers`, `purchase_orders`) already allow
`u.location_id = <row>.location_id OR u.location_id IS NULL`. Yasir's own
`app_users` row already has `location_id = NULL` under `role = 'director'`,
on the assumption this is how his own full-access login works.

Two policies hadn't been given that same escape hatch — `anon_insert_expenses`
/ `anon_update_expenses` and `anon_insert_purchases` / `anon_update_purchases`
required a *strict* `u.location_id = <row>.location_id` match even though
`director` is already in the allowed-roles list for both. Since
`NULL = anything` is never true in SQL, this meant a director with
`location_id = NULL` (i.e. Yasir's own account) could not actually submit or
edit an expense or a purchase at C-5 — a real, live bug, not a future one.
Fixed by adding `OR u.location_id IS NULL` to both tables' INSERT/UPDATE
`WITH CHECK`, matching the pattern already used elsewhere. Verified the
`EXISTS` clause now resolves `true` for Yasir's `app_users.id` against a C-5
expense/purchase.

Any director or cash_custodian/auditor account that should operate across
branches (not just Yasir's) just needs `app_users.location_id` set to `NULL`
— no schema change — once there's more than one branch to actually test
against.

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

## October 23 follow-up — edits/voids by someone other than the original author were blocked

Found via a real failure: a manager tried to correct a shift mistake on an
existing expense entry (`expense-edit.html`, PKR 2,180 "Burger Bun for
kitchen") and got `42501 new row violates row-level security policy for
table "expenses"` on save.

**Root cause:** `anon_update_expenses` and `anon_update_purchases` had their
`WITH CHECK` copy-pasted from the matching `anon_insert_*` policy, which
requires `current_session_app_user_id() = entered_by_user_id`. That's
correct for an *insert* (you can only attribute a brand-new row to
yourself) but wrong for an *update* — it meant **only the original author
of a row could ever edit or void it**, and made it permanently impossible
to edit/void any older row where `entered_by_user_id` is `null` (a lot of
migrated historical data has this). Both `expense-edit.html` (a dedicated
edit flow with a mandatory `edit_reason` audit note, clearly meant for
correcting entries regardless of who made them) and `goods-receipt.html`'s
void flow (voids any of *today's* purchases at your location, not just
your own) are built around one authorized person correcting another's
entry — so the check needs to authorize the **current editor**, not match
the row's original author.

**Fix:** `ALTER POLICY` on both, replacing the `entered_by_user_id` equality
check with an authorization check on the acting session itself —
`current_session_app_user_id()` must resolve to an active user with an
allowed role (`store_man`, `shift_manager`, `cash_custodian`, `director`)
at that row's location (or `location_id IS NULL`, same cross-branch
escape hatch as everywhere else). Verified directly: the exact scenario
that failed (Store Person editing an expense entered by S.Manager, same
C-5 location) now evaluates `true` against the new check; it evaluated
`false` before. `entered_by_user_id` itself is untouched by this — it still
correctly records who *originally* entered the row; it's just no longer
used as an edit permission gate.

**Same bug, not yet hit in practice:** no other table currently has an
edit/void UI like these two, so no other `anon_update_*` policy was
checked or changed in this pass — but if one gets built later, check it
isn't carrying the same copy-pasted mistake.

**Update, same day:** the identical mistake was in `anon_update_daily_sales`
too, on *both* `USING` and `WITH CHECK` (not just `WITH CHECK` as on the
two above) — hit live by `sales-entry.html`'s "Shift Sales & Cash Entry"
save, which upserts via `POST .../daily_sales?on_conflict=location_id,
sale_date,shift`, falling through to this UPDATE policy whenever that
shift was already saved. Confirmed against real data: today's C-5 morning
entry was entered by S.Manager, so anyone else (the director included)
saving over it hit the same 401. Fixed the same way — authorize the
current session's role/location/active status, not a match against
`entered_by_user_id` — and kept the one genuinely separate rule this table
has: only a director may save a row whose `sale_date` isn't today
(`current_business_date()`), which stays in `WITH CHECK` unchanged.
Checked `anon_select_daily_sales` and `anon_select_purchases` too, since
they have a superficially similar `EXISTS (... u.id = <table>.
entered_by_user_id ...)` shape — but those only verify the row's
*recorded* author is some legitimate active user, they don't compare
against the current session, so they're not the same bug and were left
alone.

## October 23, continued — director override + "same shift only" for shift managers, and 4 more tables with the same bug

Imran (role `director`, but with a concrete `location_id` set to C-5 rather
than the cross-branch `NULL` convention Yasir's account uses) hit the same
class of error on a different table. You then gave an explicit rule to
apply everywhere this pattern shows up: **a director can always make
changes; shift managers can only make changes within the shift that's
live right now.**

**Searched for every table with this same copy-pasted ownership mistake**
(`WITH CHECK` requiring `current_session_app_user_id() = entered_by_user_id`)
and found it in four more, none of which have `shift_manager` in their
allowed-role list at all (so "same shift" doesn't apply to them — the
ownership gate was simply removed, same as before):
`attendance_entries`, `food_panda_settlements` (policy
`anon_update_fp_settlements`), `inventory_snapshots`, `payroll_entries`.
`attendance_entries` already had the right role shape (director
unconditional, shift manager same-day-only) — it just had the ownership
gate wrongly AND'd on top, cancelling it out even for directors.

**Director access no longer depends on location at all.** The earlier Oct
23 fix used `(u.location_id = row.location_id OR u.location_id IS NULL)`
for every allowed role, treating a `NULL` location as the only way to get
cross-branch access. Imran's account proves that's not reliable — a
director can have a real location on file and still need to act anywhere.
So on every table touched today, `role = 'director'` is now its own
unconditional branch with no location check at all; the location-scoped
branch is only for the other roles (`store_man`, `cash_custodian`,
`shift_manager`).

**Added a `current_shift()` helper**, mirroring `expense-entry.html`'s own
`defaultShift()` logic server-side: 9am–6pm Asia/Karachi is `morning`,
everything else is `evening` — same shape as the existing
`current_business_date()` helper. Used it to tighten `shift_manager`'s
edit window on the two tables that actually have a `shift` column:

- **`expenses`, `daily_sales`**: a `shift_manager` may now only edit a row
  where `expense_date`/`sale_date = current_business_date()` **and**
  `shift = current_shift()` — i.e. only the shift happening right now, not
  an earlier shift from today and not any past day. `store_man` /
  `cash_custodian` keep the location-scoped, no-time-restriction access
  from the earlier fix (not part of this instruction, left as-is).
- **`purchases`**: no `shift` column exists, so `shift_manager` is scoped
  to `purchase_date = current_business_date()` instead — the closest
  equivalent, same idea as `attendance_entries` already used.

Verified: Imran's account (`director`, location = C-5) is now
unconditionally authorized on every one of these seven tables regardless
of which location or date a row belongs to, since the director branch of
each `WITH CHECK` has no location or date clause left to fail.

## October 23/24, same night — "same shift" walked back to "same day"

The `shift = current_shift()` match added above was wrong and broke a real
shift close within hours of shipping it. `current_shift()` tracks the
wall clock (9am–6pm Asia/Karachi = morning, else evening) — but closing a
shift's paperwork routinely happens well outside that shift's own clock
window, since the evening shift runs until 3am and people often catch up
on Save/Close after it ends. Reproduced exactly: today's (business-date
Oct 23) C-5 morning shift — still Draft, entered earlier that evening by
S.Manager — got a silent-feeling RLS rejection on Close Shift at 1:05am,
because `current_shift()` had already flipped to `evening` while the row
being closed was `shift = 'morning'`.

Dropped the `shift = current_shift()` clause from `anon_update_expenses`
and `anon_update_daily_sales`, keeping just the `expense_date` /
`sale_date = current_business_date()` check that was already there. A
shift manager still can't touch a different business day's entries (the
part of "same shift" that actually matters — no backdating); they're no
longer blocked from closing out today's own shifts late. Director access
is unchanged either way. The `current_shift()` function itself is left in
place (unused for now) in case a better-scoped use for it comes up later.

## For anyone touching this later

- A client calling `verify_manager_pin` gets back `session_token` now —
  store it (`AppSession.set` already does) and send it as `x-fnk-session` on
  every subsequent call (`AppSession.authHeaders()` already does).
- Any *new INSERT policy* on a table that records "who did this" should
  include `current_session_app_user_id() = <that column>` from the start,
  not just the role/location check. **For an UPDATE policy on the same
  table, do not reuse that same check** — matching the row's original
  author blocks any legitimate correction made by someone else. An update
  policy should authorize the *current* session against role/location
  (and `active`), the same shape without the `= entered_by_user_id` part.
  This exact copy-paste mistake is what broke expense/purchase edits on
  Oct 23 (see above) — don't repeat it on a future table.
- `DROP FUNCTION` and plain `DELETE` occasionally time out against this
  project through the Supabase MCP tool even though they succeed almost
  instantly server-side (confirmed via `pg_stat_activity` — nothing was
  actually blocking). `ALTER FUNCTION ... RENAME`, `CREATE OR REPLACE
  FUNCTION` (same signature), and `ALTER POLICY` were all reliable; prefer
  those over `DROP` where there's a choice.
