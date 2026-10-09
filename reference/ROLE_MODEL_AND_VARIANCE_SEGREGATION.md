# Role model & variance-entry segregation of duties

Reference notes for future sessions working on this codebase. Covers two related changes
made on 2026-10-08: the 6-role model migration, and the Added/Closing split on the
drinks/bakery daily usage entry.

## Role model (replaces the earlier owner/inventory/purchasing/store_person/cash_expense set)

`app_users.role` values now in use: `director`, `shift_manager`, `store_man`,
`cash_custodian`, `auditor`. A row named "Admin" with `role='director'` also exists
specifically to back a password-gated "Admin override" UI flow on Item Master and the
Drinks/Bakery Item List (for add/delete access when no real Director is available) — it's
not a separate role value, just a director-role identity gated by a client-side password
(`ADMIN_OVERRIDE_PASSWORD` constant near the top of each of those two files' `<script>`).

Permission table (source of truth = live `pg_policies`, not this doc — re-check with SQL
if this file and the database ever disagree):

| Table / action | Allowed roles |
|---|---|
| attendance_entries insert/update | director, shift_manager |
| daily_issues (issue to kitchen/floor) insert | store_man, shift_manager, director |
| employees insert/update | director |
| expenses insert | store_man, shift_manager, director |
| food_panda_settlements insert/update | director, cash_custodian |
| inventory_snapshots (stock count) insert/update | director, auditor |
| payroll_entries insert/update | director |
| pos_upload_batches / pos_sale_lines insert/update | director, cash_custodian |
| products (item master) insert/update | director |
| purchase_orders: create Demand | auditor, director |
| purchase_orders: authorize / cancel | director |
| purchase_orders: place order | director |
| purchase_orders: receive goods | store_man, shift_manager |
| purchases (goods receipt) insert/select | store_man, shift_manager |
| variance_items insert | director |
| variance_pos_product_map insert/update | director, cash_custodian |
| vendor_payments insert | cash_custodian, director |
| variance_daily_entries insert | director, store_man (see below) |
| variance_daily_entries update | director, shift_manager (see below) |

Front-end pages: `role-select.html` is the entry point (picks a name, stores
`{id,name,role}` in `localStorage.fnk_user`, routes to a role-scoped home page).
`director-home.html` / `shift-manager-home.html` / `store-man-home.html` /
`cash-custodian-home.html` / `auditor-home.html` each list only that role's screens.
`index.html` just redirects to `role-select.html`.

**2026-10-09 update — this role model is now a coarse layer, not the login itself.** Every
entry screen's "who are you?" step was migrated from a role-pill (pick your shared role,
no further check) to per-individual name + PIN, so that e.g. the four humans sharing the
`S.Manager` row are now distinguishable. The `app_users.role` values and the whole
permission table above are unchanged and still what RLS actually checks — the PIN layer
just resolves "which real person is this" down to the right `app_users.id`/`role` before
handing off to the same code paths described here. Full detail, the new tables/RPCs, and
the per-screen access matrix: see `ACCESS_CONTROL_AND_PIN_SYSTEM.md` in this same folder.

## Drinks/Bakery usage entry — Added/Closing split (2026-10-08)

Yasir's words: "any number that was input by store man as issuance would be added in the
daily usage screen. all manager would input is the closing balance. he cannot change the
added amount as they can show misleading amounts to match their inventory." Confirmed:
Discard still belongs to Shift Manager (not Store Man), and Opening auto-carries-forward
from yesterday's Closing rather than being typed by anyone.

**Schema** (`variance_daily_entries`): added columns `added_by_user_id`,
`closing_by_user_id`, `last_updated_by_user_id` (uuid, references `app_users`). The client
must send `last_updated_by_user_id` on every PATCH — both the RLS policy and the
segregation trigger key off it to know who's acting.

**Opening is trigger-computed, never client-supplied**: `trg_variance_entries_compute_opening`
(BEFORE INSERT) sets `opening_qty` = the most recent prior day's `closing_qty` for the same
`location_id` + `variance_item_id` (0 if no prior row). Any client-sent `opening_qty` is
overwritten.

**Column-level segregation lives in a trigger, not RLS alone** — Postgres RLS can't compare
OLD vs NEW across a single policy, so this needed `trg_variance_entries_enforce_segregation`
(BEFORE UPDATE), which also re-pins `opening_qty := old.opening_qty` on every update
(nobody can change it after creation, including Director):
- actor role (via `last_updated_by_user_id`) = `shift_manager` → blocks any change to
  `added_qty`.
- actor role = `store_man` → blocks any change to `added_qty`, `closing_qty`, or
  `discard_qty` — Store Man's only legitimate write is the original INSERT; they should
  never be able to UPDATE this table at all.
- `director` → exempt from both checks (but still can't move `opening_qty`).

**RLS**: insert policy requires the inserting user (`entered_by_user_id`) to be
`director` or `store_man`, AND requires `closing_qty = 0 and discard_qty = 0` at insert
time (Store Man can't pre-seed a misleading closing value before Shift Manager even sees
the row). Update policy requires `last_updated_by_user_id` to resolve to `director` or
`shift_manager`.

**Tested and confirmed working** (2026-10-08, via `begin; set local role anon; ...;
rollback;` against the real Gulberg location and a real variance_item): Store Man insert
succeeds with Opening auto-computed as 0; a Shift Manager update that also tries to sneak
in a changed `added_qty` is rejected with a clear Postgres exception; a legitimate Shift
Manager Closing/Discard update succeeds and `usage_qty` computes correctly; a Store Man
attempt to update Closing after the fact is rejected.

**UI** (`variance-entry.html`): the "who are you" role determines what's editable per item
— Store Man sees only an editable Added field (locked once saved); Shift Manager sees
Opening/Added as read-only and Closing/Discard editable (locked until Store Man's entry
exists); Director sees everything editable and the save flow does an INSERT followed by an
immediate PATCH so a Director can do a full one-shot entry without being blocked by the
`closing_qty = 0`-at-insert rule.
