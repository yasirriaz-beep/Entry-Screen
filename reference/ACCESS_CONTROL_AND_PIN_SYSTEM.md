# Per-individual PIN access control (2026-10-09)

Reference notes for future sessions. This layers real per-person identity and PINs on top
of the existing 6-role model in `ROLE_MODEL_AND_VARIANCE_SEGREGATION.md`, without replacing
it — `app_users.role` is still what every RLS policy checks. Read that file first for the
role/table permission matrix; this file only covers the new identity layer sitting above it.

## Why this exists

Several `app_users` rows are shared by multiple real people: `S.Manager` (shift_manager)
is used by four different humans (Ahsan/RGM, Hamza, Aqib, Anjum), so the database had no
way to tell them apart — every row they touched was attributed to the same generic
"Shift Manager" identity. Yasir asked for individual accountability: each real person gets
their own name and PIN, and Yasir can grant/revoke each person's access to each screen
individually (e.g. Anjum can get Delivery access but not Payroll, even though he and Ahsan
share the same underlying `shift_manager` app_user row).

## Schema

- **`managers`** — `id, name, app_user_id (FK -> app_users), pin_hash, active`. One row per
  real person. `app_user_id` points at whichever `app_users` row that person acts under —
  several managers can share the same `app_user_id` (the four shift-tier people all point
  at the one `S.Manager` row). `pin_hash` is bcrypt via `pgcrypto` (`crypt()`/`gen_salt('bf')`),
  same pattern as the pre-existing `verify_owner_pin`/`app_secrets` mechanism. RLS is
  enabled with **no policies at all** — nothing can read or write this table directly; every
  access goes through a `SECURITY DEFINER` RPC below. This mirrors `app_secrets`.
- **`manager_page_access`** — `manager_id, page_key, granted (boolean)`, PK on
  `(manager_id, page_key)`. Deliberately a boolean upsert target rather than
  insert/delete-managed rows, to sidestep the session's known destructive-SQL-cancellation
  quirk (`apply_migration`/`execute_sql` silently `cancelled` on some DELETE-shaped
  statements) — granting/revoking always does `ON CONFLICT ... DO UPDATE SET granted = ...`,
  never an actual delete.
- **`entered_by_manager_id`** — added to every table a converted screen writes to
  (`daily_sales`, `expenses`, `daily_issues`, `vendor_payments`, `variance_daily_entries`,
  `purchases`, `food_panda_settlements`, `inventory_snapshots`, `purchase_orders`,
  `pos_upload_batches`, `payroll_entries`, `attendance_entries`, `delivery_km_log`). Nullable
  FK to `managers.id`, alongside the existing `entered_by_user_id` (still the real
  `app_users.id` — unchanged for RLS purposes). This is attribution-only, not used by any
  policy.

## RPCs (all in `public`, callable by `anon` — same posture as `verify_owner_pin`/`delete_record`)

- **`list_managers_for_page(p_page_key text) returns table(id uuid, name text)`** — public,
  no PIN needed. Returns only the managers who (a) are `active` and (b) have
  `manager_page_access.granted = true` for that page. This is what every screen's
  "who are you?" name-grid calls to build its pills — nothing else populates that grid
  anymore (the old `app_users?role=in.(...)` queries are gone from every converted screen).
- **`verify_manager_pin(p_manager_id uuid, p_pin text) returns table(app_user_id uuid, name text, role text)`**
  — the actual login check. Raises `'Incorrect PIN'` on mismatch, or a distinct message if
  no PIN has been set yet for that person. On success returns the real `app_users.id` and
  `role` that the rest of the app (and every RLS policy) keys off, so the rest of a
  converted screen's code is otherwise unchanged — it just gets `state.userId` from here
  instead of directly from a role-filtered `app_users` query.
- **Owner-PIN-gated admin RPCs** (each takes `p_owner_pin` and calls the existing
  `verify_owner_pin()` as its gate — same owner PIN as every other admin action in this
  app): `admin_list_managers`, `admin_upsert_manager` (create/rename/reassign/activate a
  manager), `admin_set_manager_pin`, `admin_set_page_access`.

## UI

- **`manage-access.html`** (Director Home → Overview) — the only screen for adding managers,
  setting PINs, and granting/revoking page access. Deliberately kept on the **old**
  localStorage-role-check + Owner-PIN pattern (not the new name+PIN picker) so it always
  stays reachable to fix a broken PIN, even if every manager's PIN is wrong — this is the
  bootstrap/escape-hatch screen.
- **`home.html`** (2026-10-09, the entry point — `index.html` redirects here) — a single
  login page for everyone, including Directors: pick your name, enter your PIN once, and it
  shows only the pages granted to you as tabbed sections (Directors see every page). This
  replaced `role-select.html` and the five role-based home pages
  (`director-home.html`/`shift-manager-home.html`/`store-man-home.html`/
  `cash-custodian-home.html`/`auditor-home.html`), which are now just redirect stubs to
  `home.html` so old bookmarks still land somewhere sensible.
- **`session.js`** — shared helper (`FNKSession.get/set/clear/hasAccess`) backing the
  "log in once per visit" behavior. It stores `{managerId, userId, userName, role, pages,
  loginAt}` in `sessionStorage` (not `localStorage`) — deliberately so it clears when the
  browser/tab closes, rather than staying "logged in" as whoever last used a shared device.
  Every entry screen checks `FNKSession.get()` on load: if there's a valid session with
  access to that page, it skips straight past the name grid; otherwise it falls back to its
  own `list_managers_for_page` + PIN picker exactly as before (so a direct link/bookmark to
  any screen still works without having gone through `home.html` first).
- **Every other screen**: "who are you?" now shows only the individually-named people
  granted that `page_key` (via `list_managers_for_page`), and picking a name prompts for
  that person's PIN (`verify_manager_pin`) before anything unlocks. This replaced two older
  patterns everywhere: the shared role-pill with no PIN at all, and (on
  `attendance-entry.html` only) a self-typed initials prompt. Directors are **not**
  special-cased anymore — they go through the same manager+PIN flow as everyone else now
  (this was a deliberate later decision; initially Directors stayed PIN-free, then the whole
  app was migrated uniformly, Directors included).

## RPCs added for `home.html` (2026-10-09)

- **`list_all_managers()` returns table(id uuid, name text)`** — public, no PIN, like
  `list_managers_for_page` but with no page filter (the login page doesn't know a page_key
  yet). Lists every active manager.
- **`list_pages_for_manager(p_manager_id uuid) returns text[]`** — public, called right
  after `verify_manager_pin` succeeds, to get the page_keys to show as tabs/links. Kept as a
  separate RPC rather than changing `verify_manager_pin`'s return shape, because
  `CREATE OR REPLACE FUNCTION` refuses to change a function's `OUT`/`TABLE` columns
  (`42P13`) and dropping+recreating it in this session's migration tool got silently
  cancelled (destructive-SQL guard) — easier and non-destructive to just add a second call.

## `page_key` -> screen map (and who currently has each)

| page_key | Screen | Granted to |
|---|---|---|
| `sales_entry` | sales-entry.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `expense_entry` | expense-entry.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `attendance` | attendance-entry.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `issue_entry` | issue-entry.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `vendor_payment` | vendor-payment.html | Zeeshan, + Directors |
| `stock_count` | stock-count.html | Hammad, Imran, + Directors |
| `inventory_balance_sheet` | inventory-balance-sheet.html | Store Person, Hammad, Imran, + Directors (read-only ledger, 2026-10-09) |
| `settlements` | settlements.html | Zeeshan, + Directors |
| `variance_entry` | variance-entry.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `goods_receipt` | goods-receipt.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `pos_upload` | pos-upload.html | Zeeshan, + Directors |
| `purchase_order` | purchase-order.html | Hammad, Imran, + Directors |
| `item_master` | item-master.html | Directors only |
| `variance_items` | variance-items.html | Directors only |
| `moq_setup` | moq-setup.html | Directors only |
| `employee_master` | employee-master.html | Directors only |
| `owner_dashboard` | owner-dashboard.html | Directors only |
| `delivery_km` | delivery-km-entry.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `delivery_ops` | delivery-ops.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `payroll` | payroll-entry.html | Zeeshan, + Directors |
| `manage_access` | (not actually checked — see above) | Directors (nominal only) |

This matrix was built to exactly match each screen's pre-migration role-based access — no
one gained or lost screen access in the migration itself, they just now prove identity with
a personal PIN instead of a shared pill. Changing who can reach a page from here on is done
in `manage-access.html`, not by editing this file or the database directly.

## Managers roster (as of 2026-10-09)

| Manager | Underlying `app_users` role | Notes |
|---|---|---|
| Yasir Riaz | director | own `app_users` row |
| Admin | director | own `app_users` row (also backs the client-side `ADMIN_OVERRIDE_PASSWORD` flow — see role-model doc) |
| Ahsan (RGM) | shift_manager | shares `S.Manager` app_user row with Hamza/Aqib/Anjum |
| Hamza | shift_manager | shares `S.Manager` app_user row |
| Aqib | shift_manager | shares `S.Manager` app_user row |
| Anjum | shift_manager | shares `S.Manager` app_user row |
| Zeeshan | cash_custodian | own `app_users` row |
| Hammad | auditor | own `app_users` row |
| Imran | auditor | own `app_users` row |
| Store Person | store_man | single generic account — if there's more than one real store-department person, split this into additional named managers under the same `app_user_id`, same as the shift-manager group |

All PINs were supplied directly by Yasir in chat and set via `admin_set_manager_pin` — never
invented by Claude. If a PIN needs changing, either ask Yasir for the new value and set it
the same way, or point him to Manage Access to do it himself.

## Honest limitation (say this whenever touching this system)

This is UI/PIN-level accountability layered on the same coarse, role-tier RLS as the rest
of the app (anon key, policies keyed on `app_users.role`). It is not true server-enforced
per-individual authorization — anyone with the app's anon key could still bypass the PIN
check at the API level, exactly as with every other screen in this app (the day-close lock,
`delete_record`, etc.). What it adds is: (a) a real person has to know their own PIN to act
as a given identity in the UI, and (b) every save can be traced to a specific person via
`entered_by_manager_id`, not just to a shared role.
