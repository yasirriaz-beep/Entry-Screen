# Per-individual PIN access control (2026-10-09)

Reference notes for future sessions. This layers real per-person identity and PINs on top
of the existing 6-role model in `ROLE_MODEL_AND_VARIANCE_SEGREGATION.md`, without replacing
it — `app_users.role` is still what every RLS policy checks. Read that file first for the
role/table permission matrix; this file only covers the new identity layer sitting above it.

## Why this exists

Several `app_users` rows are shared by multiple real people: `S.Manager` (shift_manager)
is used by four different humans (Ahsan/RGM, Hamza, Aqib, Anjum), so the database had no
way to tell them apart — every row they touched was attributed to the same generic
"Shift Manager" identity. The owner asked for individual accountability: each real person gets
their own name and PIN, and the owner can grant/revoke each person's access to each screen
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
- **`session.js`** — shared helper (`AppSession.get/set/clear/hasAccess`) backing the
  "log in once per visit" behavior. It stores `{managerId, userId, userName, role, pages,
  loginAt}` in `sessionStorage` (not `localStorage`) — deliberately so it clears when the
  browser/tab closes, rather than staying "logged in" as whoever last used a shared device.
  Every entry screen checks `AppSession.get()` on load: if there's a valid session with
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
| `inventory_balance_sheet_monthly` | inventory-balance-sheet.html (Monthly view toggle) | Directors by default; granted per-manager via Manage Access, same page, restricted monthly view, 2026-10-16 |
| `settlements` | settlements.html | Zeeshan, + Directors |
| `variance_entry` | variance-entry.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `goods_receipt` | goods-receipt.html | Store Person, Ahsan, Hamza, Aqib, Anjum, + Directors |
| `pos_upload` | pos-upload.html | Zeeshan, + Directors |
| `purchase_order` | purchase-order.html | Hammad, Imran, + Directors |
| `po_authorize` | purchase-order.html (Authorize stage) | Imran, + Directors (Admin, Yasir Riaz) — undocumented until 2026-10-17; directors do NOT get this automatically from `role==='director'`, they need the same explicit `manager_page_access` row as anyone else |
| `fast_track_demand` | fast-track-demand.html | Ahsan, Hamza, Aqib, Anjum, Store Person, Imran, + Directors (2026-10-17 — new page; lets a shift manager send a pre-authorized order straight to `purchase_orders.status='Ordered'` for vendors flagged `vendors.fast_track=true` only, skipping the Authorize stage. Built for overnight perishables — FNK Bakery, FNK Grill — where the demand is phoned in and delivered before the store opens, i.e. before the store person or Zeeshan come on duty. Receive and Vendor Payment stages are untouched: whoever opens the store receives it normally on Goods Receipt, and since both vendors run on `payment_terms='credit'`, it becomes a payable Zeeshan clears later through the existing running-balance logic in vendor-payment.html. Gated in RLS by policy `anon_fast_track_order_po`, which requires BOTH `manager_has_page_access(..., 'fast_track_demand')` AND the target vendor's `fast_track=true` flag, plus `requested_by = ordered_by` = the logged-in user. Redesigned 2026-10-17 from a one-item-at-a-time form into a single demand sheet — picks a vendor tab, lists every product tagged to that vendor via `products.fast_track_vendor_id`/`fast_track_group`/`fast_track_sort` (grouped and ordered to match the paper demand sheets FNK Bakery/Grill already use), and submits all non-zero quantities as one batched `purchase_orders` insert — same list-everything-and-bulk-save pattern as floor-inventory.html's per-floor item grid.) |
| `item_master` | item-master.html | Directors only |
| `variance_items` | variance-items.html | Directors only |
| `moq_setup` | moq-setup.html | Directors only |
| `employee_master` | employee-master.html | Directors only |
| `owner_dashboard` | owner-dashboard.html | Directors only |
| `delivery_km` | delivery-km-entry.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `delivery_ops` | delivery-ops.html | Ahsan, Hamza, Aqib, Anjum, + Directors |
| `payroll` | payroll-entry.html | Zeeshan, + Directors |
| `manage_access` | (not actually checked — see above) | Directors (nominal only) |
| `reports` | reports.html | Directors only (2026-10-12) |
| `activity_log` | activity-log.html | Directors only (2026-10-12) |
| `rgm_tasks` | rgm-tasks.html ("Tasks") | Ahsan, Hammad, Store Person, Hamza, Aqib, Anjum, + Directors (2026-10-15 — broadened from Ahsan-only when the page grew Charge to Restaurant approvals and per-role to-do lists, see OPERATIONS-GUIDE.md) |
| `bar_items` | bar-items.html | Store Person, + Directors (2026-10-17 — new page, tags which products count as Bar stock; `products.is_bar_item` feeds Floor Inventory's Bar tab so it has something to track before any issuance exists) |
| `floor_inventory` | floor-inventory.html | Store Person, Ahsan, Anjum, Aqib, Hamza, Imran, + Directors (was missing from this table pre-2026-10-17 — not a new grant, just undocumented) |

This matrix was built to exactly match each screen's pre-migration role-based access — no
one gained or lost screen access in the migration itself, they just now prove identity with
a personal PIN instead of a shared pill. Changing who can reach a page from here on is done
in `manage-access.html`, not by editing this file or the database directly.

## Managers roster (as of 2026-10-09)

| Manager | Underlying `app_users` role | Notes |
|---|---|---|
| The owner | director | own `app_users` row |
| Admin | director | own `app_users` row (also backs the client-side `ADMIN_OVERRIDE_PASSWORD` flow — see role-model doc) |
| Ahsan (RGM) | shift_manager | shares `S.Manager` app_user row with Hamza/Aqib/Anjum |
| Hamza | shift_manager | shares `S.Manager` app_user row |
| Aqib | shift_manager | shares `S.Manager` app_user row |
| Anjum | shift_manager | shares `S.Manager` app_user row |
| Zeeshan | cash_custodian | own `app_users` row |
| Hammad | auditor | own `app_users` row |
| Imran | auditor | own `app_users` row |
| Store Person | store_man | single generic account — if there's more than one real store-department person, split this into additional named managers under the same `app_user_id`, same as the shift-manager group |

All PINs were supplied directly by the owner in chat and set via `admin_set_manager_pin` — never
invented by Claude. If a PIN needs changing, either ask the owner for the new value and set it
the same way, or point him to Manage Access to do it himself.

## 2-letter login codes (2026-10-10) — replaces typed full name

The owner asked for the login name to be a 2-letter code instead of a typed full
name, and asked Claude to suggest and show new PINs (since the existing
PINs are bcrypt-hashed and genuinely unrecoverable — there was no way to
"show" the old ones). This is a one-time, explicitly-authorized exception
to the rule above: for this change only, Claude generated the codes and new
PINs and wrote them straight into the database (direct `UPDATE ... SET
pin_hash = crypt(...)` via migration access, not through
`admin_set_manager_pin`, since that RPC itself requires an owner PIN to
authorize — which Claude doesn't have or ask for). From here on, new PINs
should go back to being supplied by the owner, not invented by Claude, unless
he says otherwise again.

- **Schema**: additive `managers.login_code` column (2 letters, unique),
  alongside the existing `name`/`pin_hash`. Nothing was removed — `name` is
  unchanged and still shown wherever the app already displayed it after
  login (e.g. "Logged in as the owner").
- **New RPCs** (additive, mirroring the existing ones without touching
  them): `list_all_managers_with_code()` and
  `list_managers_for_page_with_code(p_page_key)`, both returning
  `(id, name, login_code)`. `verify_manager_pin` is unchanged.
- **Current codes and PINs** (as of 2026-10-10 — share these with each
  person individually; this table should be updated, not left stale, if
  anyone's code or PIN changes later):

  | Name | Code | PIN |
  |---|---|---|
  | The owner | YR | 7142 |
  | Admin | AD | 3059 |
  | Ahsan (RGM) | AH | 6284 |
  | Hamza | HZ | 9173 |
  | Aqib | AQ | 4826 |
  | Anjum | AN | 5391 |
  | Zeeshan | ZE | 8047 |
  | Hammad | HM | 2658 |
  | Imran | IM | 7935 |
  | Store Person | SP | 1462 |

- **Front end**: every login form (home.html + all 20 entry screens) now
  takes a 2-letter code instead of a name (`maxlength="2"`,
  uppercased client-side), matched against `login_code` rather than
  `name`. The generic "Incorrect code or PIN." error is unchanged in spirit
  — still no roster shown, still identical wording for both failure modes.

## Honest limitation (say this whenever touching this system)

This is UI/PIN-level accountability layered on the same coarse, role-tier RLS as the rest
of the app (anon key, policies keyed on `app_users.role`). It is not true server-enforced
per-individual authorization — anyone with the app's anon key could still bypass the PIN
check at the API level, exactly as with every other screen in this app (the day-close lock,
`delete_record`, etc.). What it adds is: (a) a real person has to know their own PIN to act
as a given identity in the UI, and (b) every save can be traced to a specific person via
`entered_by_manager_id`, not just to a shared role.
