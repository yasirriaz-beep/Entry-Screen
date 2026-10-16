# Gulberg System — Operations Guide

A living reference for how this system works day to day. Grows as the system grows — every
time a new screen, rule, or control gets added, a note goes here so new staff (and future-us)
don't have to reverse-engineer it from the code.

---

## 1. Where things live (quick index)

| What | Page | Who uses it |
|---|---|---|
| Record a sale (dine-in/takeaway/delivery/etc.) | `sales-entry.html` | Shift manager |
| Record an expense (cash out) | `expense-entry.html` | Store man / shift manager |
| Fix a miscategorized/incorrect expense | `expense-edit.html` | Zeeshan / Imran / Yasir |
| Add/edit/retire an expense category or subcategory | `expense-categories.html` | Director only |
| Demand → Authorize → Order a purchase (before it's received) | `purchase-order.html` | Any manager (Demand) / Director (Authorize, Order) |
| Authorize a purchase demand only (standalone page) | `po-authorize.html` | Anyone granted the "Purchase Order — Authorize" page in Manage Access |
| Record goods received from a vendor | `goods-receipt.html` | Store man |
| Record stock issued to kitchen/floor/delivery | `issue-entry.html` | Store man |
| Pay a vendor | `vendor-payment.html` | Zeeshan |
| Daily cash safe reconciliation | `cash-reconciliation.html` | Cash custodian |
| Attendance | `attendance-entry.html` | — |
| Item / product master (names, units, categories) | `item-master.html` | Director |
| Reports (all of the above, by day or by month, Excel export) | `reports.html` | Director / Owner |
| Owner's daily audit dashboard | `owner-dashboard.html` | Owner |

---

## 2. Expense categories & subcategories

Categories are **not hardcoded** — they live in the `expense_categories` table and are
editable from `expense-categories.html` (director access only). Each category carries:

- **`code`** — a 2-digit income-statement code (10s = Cost of Sales, 20s = Payroll & Benefits,
  30 = Occupancy, 40s = Operating Expenses, 50s = Marketing & Delivery, 60s = G&A/Other,
  90s = Below-the-line / non-operating).
- **`group_name`** — which section of the Income Statement it rolls up into.
- **`is_below_the_line`** — true for cash movements that aren't real revenue/expense
  (Director Draw, Payable Payment, Interstore Transfers). These show as a separate memo on
  the Income Statement and are never netted into Net Income.
- **`requires_rgm_approval`** — **turned off as of Oct 14, 2026.** Was true only for
  "Charge to Restaurant": an entry under that head couldn't be saved without sign-off first
  (enforced both in the UI and by a database trigger, `validate_expense_category()` — it
  would fail even if someone bypassed the app and hit the database directly). Removed at
  Yasir's request — the column still exists (`UPDATE expense_categories SET
  requires_rgm_approval = false WHERE name = 'Charge to Restaurant'`), so the RGM-sign-off
  block, PIN field, and database trigger check all come back automatically if it's ever
  flipped back to `true` for this or any other category; nothing else needs to change.
  The Owner Dashboard's daily audit panel still exists but will simply have nothing to show
  for new entries going forward.

  History, for context: **who could approve**, as of Oct 13, 2026 (one day before this was
  removed): the configured RGM (PIN entry, same as before), OR **any director** — a director
  logged in under their own PIN self-approves instantly, no separate PIN needed, on both
  `expense-entry.html` (new entry) and `expense-edit.html` (fixing an existing one). Before
  that, a director correcting a miscategorized entry into "Charge to Restaurant" was stuck
  behind the same RGM gate as everyone else, including being fully blocked on days no RGM
  was configured.

  **The RGM Tasks page (added Oct 15, 2026)** puts the security back, but as a next-day
  review rather than an entry-time block: `rgm-tasks.html`, originally granted only to Ahsan
  (the one flagged `is_rgm` on `managers`). For every date without a complete review (oldest
  first, looking back 10 days), it shows three tasks — **Attendance**, **Expenses**, and
  **Charge to Restaurant** — each with the actual underlying records inline (attendance
  counts by status vs. the active employee count; the expense list with amounts and
  details) so the RGM reviews real data, not a blind checkbox. Clicking **Confirm reviewed**
  calls the RPC `confirm_rgm_task_v1`, which records a `rgm_task_confirmations` row (unique
  per location/date/task — confirming twice just updates the timestamp). This is a
  **checklist, not a gate**: confirming doesn't touch the underlying attendance/expense
  records, and nothing elsewhere is blocked by it.
  - **Escalation:** `check_daily_task_completion()` (the same 15-minute cron job that flags
    unclosed shifts and missing issuance) now also checks, for each of the three tasks, 2
    full days after the task's date (9am Karachi, the same business-day cutover used
    everywhere) — if still unconfirmed, it opens an `audit_alerts` row
    (`task_rgm_review_missing`), which shows up on the Owner Dashboard's Alerts tab like any
    other open alert. Confirming late immediately resolves the alert itself (the RPC calls
    `resolve_task_alert` directly), rather than waiting for the next cron pass.

  **Grown into a general "Tasks" page (Oct 15, 2026 — same day):** the page (still
  `rgm-tasks.html`/page_key `rgm_tasks`, relabeled "Tasks" on Home) now does three things,
  stacked top to bottom, each shown or hidden based on who's logged in:

  1. **Charge to Restaurant — needs approval** (visible to Hammad/auditor and Directors).
     Managers still enter Charge to Restaurant freely on `expense-entry.html` — nothing
     blocks the save. A `BEFORE INSERT` trigger (`expenses_set_review_status()`) stamps
     every new row in that category `review_status = 'pending_review'`. This section lists
     every pending row (amount, date, who entered it, detail) with **Approve**/**Reject**
     buttons that call `review_charge_to_restaurant_v1(expense_id, manager_id, approve,
     notes)` — gated to `role IN ('auditor','director')` inside the RPC itself, not just by
     page access. Approving/rejecting only ever changes `review_status` +
     `reviewed_by_manager_id`/`reviewed_at`/`review_notes` on the expense row; the amount,
     category, and everything else about the expense is untouched, and it already counted
     in every report from the moment it was entered — this is a review trail, not a
     financial control.
  2. **Charge to Restaurant — for your review** (visible to Directors only). Once Hammad (or
     a director) approves an entry, it shows up here for Yasir — amount, date, who entered
     it, when it was approved. No action is required; a **Got it** button
     (`mark_charge_to_restaurant_seen_v1`) just clears it off the list by stamping
     `owner_seen_at`, director-only, purely for the owner's own tidiness.
  3. **To-Do Lists** — a running, manually-maintained checklist per role (Store Man, Shift
     Manager, RGM, Auditor, Director), meant to grow over time as new standing
     responsibilities come up, rather than anything auto-generated. Backed by a new table,
     `role_todos` (`role_key, text, status, created_by_manager_id, created_at,
     done_by_manager_id, done_at`). Anyone with access to this page can add an item to any
     role's list or check one off — there's no per-role write restriction, since in practice
     Yasir is usually the one adding items for other roles. Adding goes through
     `add_role_todo_v1`, checking off through `set_role_todo_status_v1` — both
     `SECURITY DEFINER` RPCs that verify the caller is an active manager granted the
     `rgm_tasks` page (reads of the table go straight through PostgREST, since
     `role_todos`'s own `SELECT` policy is just `USING (true)`).

  - **Access** was broadened the same day from Ahsan-only to also include Hammad, Store
    Person, Hamza, Aqib, and Anjum (via `manager_page_access`, page_key `rgm_tasks`) — still
    not tied to the `is_rgm`/`auditor` role flags themselves, just individual grants, so
    access can be adjusted later with no code change. Directors see every section regardless
    (same universal-access rule as every other page).
  - **Why RPCs, not raw table policies, for the new writes:** `managers` has RLS enabled
    with zero policies (see the JazzCash/RGM-tasks note elsewhere in this doc), so any RLS
    `WITH CHECK` on another table that joins `managers` to verify the caller — which is what
    a first attempt at `role_todos`'s own insert/update policies did — silently evaluates to
    false for the `anon` key, because `anon` can't see any rows in `managers` either, even
    inside someone else's policy. `confirm_rgm_task_v1` already sidesteps this by writing as
    a `SECURITY DEFINER` function instead of a raw REST call; `add_role_todo_v1` and
    `set_role_todo_status_v1` follow the same pattern. The table's own insert/update RLS
    policies are left in place but are effectively dead code — real writes only ever go
    through the RPCs.

**Subcategories** are managed inside the same page (expand a category → Subcategories
section). A category with no subcategories just skips that dropdown on the entry form.

**If a new category is added**, give it a `code`/`group_name` right away — an expense
category without one shows up on the Income Statement under a red "Uncategorized / Needs
Review" banner until it's fixed. That banner is deliberate: it's the system catching an
unclassified expense before it quietly skews a financial statement.

### Catching the wrong head picked (e.g. a salary charge booked under "Food")

Two layers, both powered by the same AI classifier (`classify-expense-category` edge
function, Claude Haiku, reads the Description and picks the best-fitting head from the fixed
list — also used by the "Head suggest karwayen" helper on the entry form):

- **At entry time (`expense-entry.html`), as of Oct 13, 2026**: "Check & Save" now runs this
  classifier against whatever was typed in Description, alongside the existing statistical
  check (duplicates, outlier amounts, suspiciously round numbers). If the AI's best guess
  doesn't match the category actually selected — or thinks the whole thing belongs on Goods
  Receipt instead — it's added to the same "This entry looks unusual" warning the statistical
  check already uses, and has to be acknowledged before saving. A low-confidence AI guess is
  not flagged (too noisy to be useful).
- **After the fact (`expense-edit.html`)**: a **"Check This Day for Miscategorized Entries
  (AI)"** button on the entry list runs the same classifier against every already-saved entry
  for the selected date that has a description, and marks any mismatch with an amber ⚠ flag
  right on that entry — tap it to open and fix. This is the catch-up tool for anything entered
  before this existed, or saved anyway over the warning. It's an explicit button (not automatic
  on every page load) since it's one AI call per entry and can take a few seconds on a busy day.

Neither layer blocks saving — they're a second opinion, not a hard rule. The category is still
whatever the human picks.

**Viewing a receipt photo for today's entries**: on `expense-entry.html`, any entry in "Today's
Entries" that has a photo attached shows a "📷 View photo" line — tap the entry to open it in a
new tab (same signed-URL pattern as the monthly reports photo links and the Cash
Reconciliation safe photo). `expense-edit.html`'s entry list works the same way. Added Oct 13,
2026 — before this, a photo could only be viewed from the monthly report, not from the entry
screen itself on the same day.

---

## 3. Income Statement (Reports → Income Statement)

Built from `expenses` + `daily_sales` + `purchases` — **not** from the `chart_of_accounts` /
`journal_entries` tables that exist in the database. Those were set up at some point but
nothing in the app posts to them; they're dead schema, not the source of truth. Don't wire
new reporting to them without rebuilding the posting logic first.

Structure: Revenue → Cost of Sales → Gross Profit → Operating Expenses (grouped, each
category/subcategory expandable) → Net Operating Income → Net Income, with a % of Revenue
column throughout. Below-the-line items sit in a separate memo box, excluded from Net Income.

**Cost of Sales** is three things added together:
1. Expenses tagged with a "Cost of Sales" category (Inventory Purchase, Food, Packaging).
2. **Goods Receipt** — every vendor delivery logged in `purchases`, broken down by vendor.
   This was missing until Oct 12, 2026 — Cost of Sales was understating real cost by
   whatever had been received but not separately expensed.
3. **Bakery (Intercompany)** — `daily_sales.bakery_sale` is deducted here as what Gulberg
   owes its sister bakery entity, compared against FNK Bakery's actual Goods Receipt total
   for the same period. The two should converge to ~0 variance at month end; a red flag means
   either FNK Bakery hasn't logged its deliveries yet, or the numbers genuinely don't match
   and need a look.

   `bakery_sale` is a **memo** figure already counted inside Dine-In/Takeaway/Delivery/etc. —
   it must never be added again as its own revenue line. (It was, until Oct 12, 2026 — that
   inflated total revenue by the full bakery amount. Fixed.)

**Known gap (as of Oct 12, 2026):** 3 purchase entries for ONION, PKR 24,750 total, have no
vendor assigned (`vendor_id` is null) — they'll show up under "No Vendor Assigned" in the
Goods Receipt breakdown. Worth tracking down who that vendor actually was.

---

## 4. Monthly reports (Reports page)

Every tab (Sales, Expenses, Goods Receipt, Issue Entry, Vendor Payments, Cash Reconciliation)
now runs over a date range, not just one day — pick a range or tap This Month / Last Month /
This Year, and it shows one row per calendar day with the relevant breakdown as columns and a
Total on the right, plus a Download Excel button. A day with literally nothing entered shows
faded/italic — that's intentional, it's the fastest way to spot a day someone forgot to do
their entry.

- **Sales**: Dine In / Takeaway / Delivery / 3rd Party / Food Panda as real columns; Bakery
  and Card are shown too but marked with `*` and excluded from the Total — they're memo
  breakdowns of money already in the other columns, not separate revenue.
- **Expenses**: columns are whatever categories actually had spend in the period.
- **Goods Receipt / Vendor Payments**: columns are whatever vendors were actually used.
- **Issue Entry**: columns are the issue destinations (BOH/FOH/DEL etc.) seen in the data.
- **Cash Reconciliation**: fixed columns (Opening, Cash In, Cash Out, Expected, Counted,
  Variance) since it's a reconciliation, not a disbursement journal — no row Total.
- **Payables (Monthly)** stayed as-is — it's already a vendor-by-month view, not a daily one.

**To view a receipt photo**: on Expenses, Goods Receipt, or Vendor Payments, run the monthly
report, then tap the date you want — a panel opens below the table with that day's itemized
entries and a "View Photo" link on each one that has a receipt attached. Cash Reconciliation
shows its safe photo directly as a column in the monthly table (one row per day already, so
no drill-down needed there). Photos auto-delete after 40 days — the underlying numbers stay
forever, only the image goes.

---

## 5. Cash flow — two safes

As of Oct 13, 2026 the cash model is explicitly **two safes**, matching who is actually
responsible for the cash at each stage:

- **Safe 1 — the till.** Shift Manager's responsibility, one per shift, entered on
  `sales-entry.html`.
- **Safe 2 — the main safe.** Zeeshan's responsibility, one per day, entered on
  `cash-reconciliation.html`, which now also shows a read-only **Safe 1 summary** at the top
  (both shifts, pulled live — nothing to enter there) so the two safes are visible together.

### Viewing/editing a past date on Sales Entry (added Oct 14, 2026)

Logging in to `sales-entry.html` always opens **today's** entry (Gulberg's business day, with
the usual 9am PKT cutoff). Only a **director** sees an editable **Date** field after logging
in; everyone else (shift manager, etc.) is locked to today with no way to drift onto another
day. A director changes the date there to review or correct a past day's shift — the two shift
panels reload for that date exactly as they do for today.

This is enforced at the database level, not just hidden in the UI: `daily_sales`'s RLS insert/
update policies require either `sale_date = current_business_date()` (the same 9am-PKT-cutoff
function used elsewhere) or the acting user's role to be `director`. A shift manager's save
request for a non-today date is rejected by the database itself, the same way the Purchase
Order role checks are (see section on `manager_has_page_access`) — a client-side-only lock was
deliberately not relied on. `public.current_business_date()` already existed from earlier work
and is reused here rather than duplicated.

### Safe 1 — Till Cash Reconciliation (Sales Entry)

This is an **audit check**, not a data-entry chore — almost everything fills in on its own.
Each shift's till always opens — and is expected to close — at the standard **PKR 40,000**
float (set server-side by a DB trigger on insert; no longer carried forward from whatever the
previous shift's physical count happened to be, so a miscount can't silently compound into the
next shift). The shift manager's only required input is the **actual physical cash count**
at the end of the shift. Everything else:

- **Cash sales this shift** — computed from the sale amounts already on the form.
- **Cash expenses this shift** — pulled live from Daily Expense entries tied to this same
  shift and date, cash payment method only, **excluding any entry marked "Paid From: Safe 2"**
  (see "Paid From: Safe 1 vs Safe 2" below — that cash never came out of this till, so it
  shouldn't reduce the handover here). (This is scoped to ONE shift — the "Today's
  Entries" total on Expense Entry covers both shifts combined, so the two numbers are not
  meant to match; see note below.)
- **Cash to give cash custodian** — auto-generated, read-only: Cash Sales − Cash Expenses,
  i.e. whatever keeps the till at the 40,000 float.
- **Actual cash handover to custodian** — what the shift manager actually hands over,
  pre-filled from the auto-generated figure above but editable if reality differs. Editing it
  once stops the auto-fill for the rest of that shift. This is the number that gets saved and
  feeds Safe 2's Cash In on `cash-reconciliation.html` — i.e. it "maps to the cash custodian
  page." A mismatch against the auto-generated figure shows a flag but never blocks saving.
- **Expected cash left in the till** (shown under the physical-count field) = Opening + Cash
  Sales − Cash Expenses − Actual Handover. This is what the physical count is checked
  against — if the actual handover was correct, it should land back on PKR 40,000.

The equivalent calculated-vs-actual check also runs server-side
(`recheck_shift_cash_discrepancy`, fired after every insert/update on `daily_sales`) and opens
an `audit_alerts` row when calculated and actual cash expenses are off by more than PKR 1,
auto-resolving once they match. The Owner Dashboard's cash-recon audit list and the evening
manager's "Morning shift" recap use the same formula.

**Why Today's Entries and a single shift's "Cash expenses this shift" can look different**:
Today's Entries (Expense Entry) totals **both shifts** for the day; Till Cash Reconciliation is
scoped to **one shift**. E.g. PKR 5,565 (morning) + PKR 23,787 (evening) = PKR 29,352 (today's
combined total) is expected, not a bug — confirmed Oct 13, 2026.

### Paid by JazzCash / Mobile Wallet, and Cash Short/Over (added Oct 13, 2026)

Each shift has a **"Paid by JazzCash / Mobile Wallet"** field right under "Paid by Card" —
same idea as Card: it doesn't change the total sale, it just flags how much of it is sitting in
a wallet (pending clearance) rather than physical cash in the till right now. Both Card and
JazzCash get subtracted out of Cash Sales before the auto-handover and expected-till-balance
math runs. Without entering today's JazzCash figure here, the till math assumes that money is
physical cash that should be in the drawer or handed to the custodian — it isn't, so the shift
will show a false "off by" warning and a false Short/Over until it's entered.

Once Card and JazzCash are accounted for, whatever gap is left between the physical count and
the expected till balance is a real **Cash Short / Over** — shown as its own labeled, colored
box (red = short, green = over) under the physical-count field, not just a sentence. A free-text
**Note (optional)** field is always available for context (e.g. "till was busy, recount
confirmed") — saved as `daily_sales.cash_short_over` / `daily_sales.variance_reason`, a permanent
record either way.

**Every shift has to net to zero before it can close (redesigned Oct 15, 2026):** when the
variance is more than PKR 1, the box also shows a resolution step, and **Close Shift is blocked**
until it's completed — not just logged with a reason. An earlier version of this feature
auto-booked every variance blind the moment a shift closed; the owner corrected that design
(Oct 15, 2026) to require an explicit choice instead:

- **Short (till came in under):** pick one —
  - **Charge to a person** — a dropdown of every active employee at the location (deliberately
    *not* filtered to the "Cashier" designation, since whoever actually handled cash that shift —
    a manager covering the till, say — needs to be pickable too). Clicking **Resolve shortage**
    books it as a `Payroll`-category expense with `employee_id`/`charged_to` set, reusing the
    exact same payroll-advance mechanism Expense Entry already uses: it deducts from that
    person's pay this month, the same as a cash advance would.
  - **Charge to owner (expense)** — books it as a regular **"Till Cash Shortage"** expense
    (code 64, G&A/Other, no RGM approval) that **reduces Net Income** on the Income Statement.
    This is deliberately a normal P&L expense, *not* a below-the-line Director Draw — the owner
    was explicit that a till shortage should hit profitability, not be treated as a personal
    withdrawal.
  - Either choice calls the RPC `resolve_till_variance_v1`, which saves the shift first if it
    hasn't been saved yet (to get a `daily_sales.id`), then books the expense, then records the
    resolution in `till_variance_postings` (keyed on that shift's `daily_sales.id`, unique) so a
    page reload recognizes it's already resolved instead of prompting — or double-booking —
    again. Resolving is idempotent: calling it twice for the same shift and the same variance
    amount books the expense only once.
- **Over (till came in over):** one button, **"Add excess to handover"** — no choice needed.
  Clicking it folds the excess straight into that shift's custodian handover (`custodianAmount`),
  which is already what flows into Safe 2's cash in, so the excess simply becomes extra cash for
  Safe 2 — no separate expense or receivable row. This naturally brings the Short/Over figure
  back to zero (that *is* the resolution), and the shift is then free to close. A best-effort
  `resolve_till_variance_v1` call with `resolution_type = 'over_handed'` logs it to
  `till_variance_postings` purely for an audit trail — it never blocks the UI if it fails.
- If the variance changes after a resolution was recorded (e.g. a recount), the old resolution no
  longer matches and Close Shift is blocked again until it's re-resolved.
- **Whole Day Totals** rolls both shifts' Short/Over into one number, with either shift's note
  listed underneath it — the one place the director needs to look, rather than opening each
  shift to see why.

**Superseded (Oct 15, 2026):** an earlier version auto-booked every nonzero till variance the
moment a shift closed — short → an automatic "Till Cash Shortage" expense, over → an automatic
`custodian_receivables` row — via a DB trigger (`sync_till_variance_posting` on `daily_sales`).
That trigger function is now a no-op (neutralized via `CREATE OR REPLACE`, not dropped, since
DROP/DELETE statements are blocked on this project) — all booking now happens only through the
explicit, interactive flow above.

**JazzCash collected at night (added Oct 13, 2026):** at Gulberg, the JazzCash balance flagged
during Morning is actually cashed out around 10pm and physically handed into the **Evening**
till — it doesn't just sit as a receivable forever. So Evening (only) has a second field, **"Cash
received this shift — JazzCash collected from Morning"**, right under Cash Expenses in the Till
Cash Reconciliation box. This is *not* Evening's own sales — it's an inflow — so it adds into
the cash-available total (`Cash Sales + JazzCash Collected − Cash Expenses`) feeding Evening's
auto-handover and expected-till-balance, instead of Evening's own Cash Sales figure. The field
**pre-fills from Morning's saved JazzCash amount** the moment Evening is opened (confirm or
correct it — the actual cash handed over at 10pm is what should go here), so Morning's flagged
amount is counted exactly once: never (if ignored) and never twice (if someone also folded it
into an Evening sales field by hand). Saved as `daily_sales.jazzcash_collected_amount`.

**JazzCash that ISN'T converted same day — the outstanding receivable (added Oct 14, 2026):**
the mechanism above only covers Morning's same-day, same-amount handover into Evening. When
JazzCash backs up for days (agent unavailable, holiday, etc.), `cash-reconciliation.html` now
has a **"JazzCash Outstanding"** box right at the top (big red-bordered tile, same style as
Vendor Payment's Payable/Receivable boxes) — tap it to expand **"Record JazzCash Converted to
Cash"**.

- **The outstanding balance** = all JazzCash ever flagged across every shift/day
  (`SUM(daily_sales.jazzcash_amount)`) minus same-day collections already recorded
  (`SUM(daily_sales.jazzcash_collected_amount)`) minus every formal settlement already recorded
  below (`SUM(jazzcash_settlements.amount_outstanding_before)`). It's computed live from these
  three sources — nothing is pre-aggregated into a stored balance column.
- **Recording a settlement** (enter the amount actually received in cash + date + optional
  notes, click Record Settlement) calls the RPC `record_jazzcash_settlement`, which atomically:
  snapshots the current outstanding balance, saves a `jazzcash_settlements` row, and then:
  - **Partial or short (received < outstanding): no expense is booked.** The settlement retires
    only `LEAST(amount received, outstanding before)` of the balance; the unreceived remainder
    simply stays in the outstanding JazzCash balance until a later settlement actually collects
    it. A partial payment is not a loss, just not fully collected yet.
  - **Over** (received > outstanding): books the excess as a row in a new
    **`custodian_receivables`** ledger, attributed to whoever is flagged `cash_custodian`
    (Zeeshan) — money he's physically holding that isn't yet recognized as settled, to be
    accounted for or returned, not silently absorbed into the day's cash.
  - **Either way**, only `MIN(amount received, outstanding before)` ever flows into Safe 2's
    Cash In for that date (`fetchCashIn` in `cash-reconciliation.html`) — so a partial/short
    settlement shows up as less cash coming in (correct — less real cash actually arrived) and
    an overage does **not** inflate Safe 2's recorded cash until the receivable above is
    resolved.

  **Fixed Oct 15, 2026:** the original version above subtracted the *full* outstanding-before
  snapshot on every settlement, so even a partial payment wiped the whole balance on paper —
  which is why it used to also auto-book a "JazzCash Shortage" expense (code 63, G&A/Other) for
  the "missing" difference, on the theory that the gap was a real loss. The owner flagged this as
  wrong: a partial settlement isn't a loss, it should just stay in the outstanding payable until
  it's actually collected. The outstanding-balance formula now caps each settlement's retirement
  at `LEAST(amount_received, amount_outstanding_before)`, and the auto-expense branch was removed
  entirely. The one expense this bug had already wrongly booked (PKR 88,610, `expenses.id`
  `3685bb36-518d-4fc3-a569-b0cdfd997021`, tied to settlement
  `dc9bf5d5-aa4c-409e-b4ea-0d9aa97f621e`) was reversed (`amount` set to 0, with a note appended
  to `detail` rather than deleted, to preserve the audit trail) and that PKR 88,610 now correctly
  sits back in the outstanding JazzCash balance instead.
- `custodian_receivables` has no UI yet to mark one settled/collected — right now it's a record
  only, visible via SQL or a future small screen. Ask if a page for that becomes worth building.
- This is deliberately separate from the "collected from Morning" field above rather than
  replacing it — that field still handles the common same-day case inline on the sales entry
  screen; this new mechanism is for backlog that spans multiple days and needs short/over
  accounting, which the simple same-day field was never designed to do.

**Superseded:** an earlier same-day design (a manual "Cash left in till for next shift" field,
`till_leftover_amount` column; a Custodian "gave/picked" direction dropdown) is no longer
used — the custodian amount is now a single signed field (positive = cash left the till) and
opening is always the fixed float, decided server-side. The `till_leftover_amount` column still
exists in the DB but nothing reads or writes it going forward.

### Side-by-side shifts, Save vs. Close, and Director Unlock (as of Oct 13, 2026)

`sales-entry.html` no longer has a Morning/Evening dropdown. Morning and Evening are shown as
two full, independent panels side by side (stacked Morning → Evening on a phone), each with its
own sales fields and its own Till Cash Reconciliation. A third panel, **Whole Day Totals**,
sits to the right (last on a phone) and combines both shifts live — covers, total sale, cash
sales, cash expenses, and cash handed to the custodian — because the director cares about the
whole day, not either shift alone.

- **Save** behaves exactly as before and stays fully repeatable — a shift manager can keep
  re-saving the same shift all day (e.g. adding the closing count later) with no lock.
- **Close Shift** is a separate, explicit button, only enabled once the physical cash count is
  filled in. It saves the shift's current numbers and marks it `status = 'closed'` (with
  `closed_at` and which manager closed it) — after that the whole panel goes read-only and
  shows a "Closed — locked" badge. This was a deliberate change from the original ask ("locks on
  save") — locking on every save would have broken the documented workflow of saving mid-shift
  and coming back later to add the closing count, so locking only happens on this explicit,
  separate action.
- **Director Unlock** appears on a closed shift in place of Save/Close. It prompts for the
  owner PIN (same PIN/pattern as "Lock/Unlock Day" on `cash-reconciliation.html`) and calls the
  `admin_unlock_shift_v1` RPC, which resets that one shift back to `status = 'draft'` so it can
  be edited and saved again.
  - **Masked entry (added Oct 14, 2026):** this PIN prompt, and the matching "Lock Day"/"Unlock
    Day" prompts on `cash-reconciliation.html`, used to be plain `window.prompt()` dialogs — the
    PIN was visible in cleartext on screen as it was typed, since a native browser prompt can't
    be masked. All three now go through a small shared modal (`pin-modal.js`, `askPin(title)`)
    with a real `<input type="password">`, so the digits are hidden like any normal password
    field. No RPC or PIN-check logic changed — same `verify_owner_pin()` gate as before, just a
    masked way to type it in. If another screen is added later with an owner-PIN prompt, include
    `pin-modal.js` and use `askPin(...)` instead of `prompt()`.
- The old "evening manager sees a read-only Morning recap" card is gone — now redundant, since
  both shifts are always visible together on the same screen.

### Safe 2 — Cash Reconciliation (Zeeshan's safe)

Opening (carried from yesterday's count, or set once by hand for day one of using this system)
+ Cash In (the day's till handovers, i.e. the Safe 1 custodian amounts above) − Cash Out
(expenses/vendor payments/goods receipts paid **directly from the safe**, no shift attached —
a shift-tied expense already shows up as a smaller Safe 1 handover, so counting it here too
would double it) = Expected, compared against Zeeshan's physical count.

**Cash Out is deliberately narrow — only cash that actually left this safe, in Zeeshan's own
hands:**
1. Vendor Payments with method = cash (paying down a payable logged earlier on Goods Receipt).
2. **Goods Receipt entries marked "Paid Now" → Cash** — added Oct 13, 2026. A receipt paid on
   the spot never goes through Vendor Payments (there's no payable to pay down), so without this
   it vanished from the cash trail entirely. `purchases.payment_method` (cash/bank, only
   meaningful when `payment_status = 'paid'`) drives this — Goods Receipt now asks "Paid How?"
   whenever "Paid Now" is picked, defaulting to Cash.
3. **Daily Expense entries explicitly marked "Paid From: Safe 2"** — see below.

An ordinary Daily Expense entry (the default, "Paid From: Safe 1") is **never** summed into
Safe 2's Cash Out — it already comes out as a smaller Safe 1 till handover, so summing it here
too would deduct it twice. (An earlier version of this page summed every no-shift Daily Expense
entry in here regardless; the owner flagged it as double-counting against Safe 1 and it was
removed Oct 13, 2026, replaced by the explicit per-entry flag below.)

#### Paid From: Safe 1 vs Safe 2 (added Oct 13, 2026)

Every Daily Expense entry with **Payment Method = Cash** now has a second field, **Paid From**:
- **Safe 1 — Till** (default). The normal case: the cash came out of that shift's till, so it
  reduces that shift's custodian handover (above) the way it always has.
- **Safe 2 — Zeeshan paid it directly.** Use this when Zeeshan pays something straight out of
  the main safe instead of through a shift's till — the recurring example is **Government
  Charges & Taxes and Utilities** (EOBI, FESCO, gas, etc.), which he settles himself regardless
  of which shift is running. Picking this routes the amount into Safe 2's Cash Out (item 3
  above) instead of reducing any shift's till handover. It's entered the same way as any other
  Daily Expense — same category, same screen — just with this one field changed; nothing else
  about the entry (category, approval rules, receipt photo) is different. `expense-edit.html`'s
  entry list tags these "Paid from Safe 2" so they're easy to spot and re-flag if entered wrong.

**As of Oct 13, 2026, a DRAFT day always shows live totals**, not whatever was saved the last
time someone hit "Save Draft." Before this, a draft saved early in the day (before the shifts
or receipts were entered) froze at Cash In/Out = 0 and stayed wrong for the rest of the day —
the only way to see the real numbers was to keep clicking Save Draft and hope. A **submitted or
locked** day still freezes its totals on purpose (so a finalized day can't silently drift if
someone edits a sales/expense record afterward) — the drift warning banner only fires for those.

If Cash In / Cash Out still look wrong on a draft day, check: (1) has every shift for that day
actually saved its Safe 1 section (closing count), and (2) were the day's cash expenses/receipts
meant to be paid directly from the safe (no shift) or from a till during a shift (shift set) —
only the former shows up in Safe 2's Cash Out.

#### All Cash Movements — both safes (added Oct 13, 2026)

A card near the top of `cash-reconciliation.html`, above the Safe 1/Safe 2 breakdown, lists
every cash vendor payment, cash goods receipt (paid now), and cash expense for a chosen date
range — both safes, tagged — independent of the day-by-day reconciliation flow below it. This
exists because the per-day flow only surfaces a payment once you open that exact date, and a
**draft** day saved before a late entry lands can sit stale until someone happens to reopen it
(the drift banner only fires on reopen). The real-world trigger: staff sometimes pay a vendor
and take delivery, but don't log the Goods Receipt until later — in the meantime the payment is
a real cash outflow that's easy to miss unless you're looking at that specific day. This card
defaults to the last 14 days on login and can be widened with the From/To fields — use it to
catch a late-reported payment without hunting for which date it landed on.

**Total Payable to Vendors** moved off this page — it now lives at the top of
`vendor-payment.html`, which is where it's acted on.

#### Internal Transfer Between Safes (added Oct 14, 2026)

A card on `cash-reconciliation.html`, right below the Safe 2 flow breakdown, records cash moved
between Safe 1 (the till) and Safe 2 (Zeeshan's safe) that is **neither a sale nor an
expense** — e.g. Zeeshan hands the till an extra PKR 12,000 float for a busy shift, then takes
it back later. Pick a direction (Safe 2 → Safe 1, or Safe 1 → Safe 2), enter the amount and an
optional reason, and it flows straight into that day's Cash In/Out:

- **Safe 2 → Safe 1** shows as a Safe 2 **Cash Out** line ("Transfer to Safe 1").
- **Safe 1 → Safe 2** shows as a Safe 2 **Cash In** line ("Transfer from Safe 1").

Backed by a new `cash_transfers` table. Zeeshan (role `cash_custodian`) can record **both**
directions himself — unlike a genuine external cash injection, a transfer is self-balancing
(one safe's amount is always the other's mirror), so there's nothing here he could fabricate to
paper over a shortfall; recording it only states which safe currently holds money that was
always somewhere in the business. RLS on `cash_transfers` restricts inserts to `cash_custodian`
or `director`, verified with simulated anon-role transactions.

It also appears in the **All Cash Movements** ledger above, tagged "Transfer" and shown for
visibility — but excluded from that card's "Total cash out" figure, since a transfer isn't real
spending.

**Resolved Oct 14, 2026 — Evening's opening float now maps to Morning's actual closing float.**
Previously the opening float on `sales-entry.html` was always hardcoded to the standard PKR
40,000, for both Morning and Evening, regardless of what actually happened to the till in
between. If Zeeshan pulled cash out of (or added cash to) Safe 1 between shifts, Evening's
"Opening cash" still showed 40,000 — not what was really left in the till — so the two shifts
didn't map to each other and the mismatch looked like an unexplained variance.

Fixed in the DB trigger `daily_sales_compute_opening_cash()` (fires `BEFORE INSERT` on
`daily_sales`): for an **Evening** row, it now looks up that same day's **Morning** row for the
same location and uses Morning's `closing_cash_till` as Evening's `opening_cash_till`, when
Morning has one recorded. If there's no Morning row yet (or it hasn't closed), Evening falls
back to the standard PKR 40,000, same as before. **Morning** (the first shift of the day) is
unaffected and still always opens at the standard float. The separate `daily_sales_lock_opening_cash()`
trigger (fires `BEFORE UPDATE`) is unchanged — it still freezes `opening_cash_till` once a row
exists, so this mapping only happens at the moment Evening's row is first created, exactly
mirroring the number the shift manager already sees in the on-screen preview (`sales-entry.html`
now does the same Morning-closing-till lookup client-side, so what's shown before saving matches
what gets saved).

Net effect of today's (Oct 14) example: Morning closed with PKR 20,000 actually left in the
till (Zeeshan took the other 20,000 out) → Evening's opening float now shows and saves as PKR
20,000, not 40,000. No manual backdating or correction was needed since Evening's row for today
had not yet been saved when this fix went in.

Note: this did not, by itself, change the *standard* float — only how a later shift the same
day inherits from the one before it. (**Updated Oct 15, 2026:** the standard float itself *was*
then explicitly lowered — see below. This paragraph is left as written at the time for context.)

**Correction, same day:** before the fix above went in, a PKR 20,000 "Internal Transfer" (Safe 1
→ Safe 2, reason "20000 Float") had already been recorded by hand as a workaround for this exact
gap. On inspection, that cash wasn't actually separate from what Zeeshan was given anyway: Morning's
custodian handover (PKR 156,580) was already ~PKR 17,000 above the auto-suggested, sales-only
amount (PKR 139,531), and the till's physical count came in PKR 2,951 short of what that handover
alone would've left behind — together accounting for the same ~PKR 20,000 reduction in the till's
leftover float. Recording it a second time as a transfer meant Safe 2's Cash In counted it twice.
That transfer row was voided (amount reduced to PKR 0.01, a DB constraint blocks an exact zero;
reason field marked VOID with an explanation) — the separate, legitimate PKR 12,000 transfer from
earlier the same day was left untouched. **Going forward, with the mapping fix in place, this kind
of manual transfer workaround for a float reduction should no longer be needed** — Evening will
simply open at whatever Morning's till actually closed at.

**Standard float lowered from PKR 40,000 to PKR 20,000 (Oct 15, 2026), at the owner's explicit
request.** This is the actual standing-policy change — distinct from the Oct 14 fix above, which
only changed how Evening inherits from Morning and explicitly did *not* touch the standard float.
Changed in two places, kept in sync:
- `STANDARD_TILL_FLOAT` in `sales-entry.html` (the on-screen preview before saving).
- The trigger `daily_sales_compute_opening_cash()`'s fallback (used for every Morning shift, and
  for Evening when there's no Morning row yet to inherit from) — this is what actually gets saved.
Every Morning shift from Oct 15, 2026 onward opens at PKR 20,000; shifts saved before this change
keep whatever `opening_cash_till` they already have (never recalculated retroactively). A couple
of display-only fallback literals in `owner-dashboard.html` and `cash-reconciliation.html` (used
only if a row somehow has no `opening_cash_till` recorded at all — not expected to occur in
practice, since the trigger always sets it) were updated to match, for consistency.

#### Advance Paid, on Goods Receipt (added Oct 13, 2026)

Some vendors (e.g. **K&N**) won't deliver without an advance paid up front. Payment Status on
`goods-receipt.html` now has a third option, **"Advance Paid (balance stays on credit)"**, next
to On Credit and Paid Now. Picking it asks for the advance amount actually paid and how (Cash/
Bank) — the advance doesn't have to be the full bill, just what was handed over to get the
delivery moving.

Under the hood this is just an ordinary credit purchase plus an ordinary vendor payment, saved
together in one step:
- The `purchases` row saves as **`payment_status = 'credit'`**, same as On Credit — the full
  invoice amount is a real payable.
- A **`vendor_payments`** row is saved alongside it for the advance amount, same table and same
  math `vendor-payment.html` already uses to show the running balance (owed = credit purchases
  − vendor payments). So the vendor's payable net of the advance shows correctly on Vendor
  Payment automatically — no separate "advance" ledger to keep in sync, and an advance paid in
  cash shows up on Safe 2's Cash Out the same way a Vendor Payment always has (item 1 above).
- If the advance happens to equal the full bill, the net payable lands on zero — same result as
  Paid Now, just with the payment recorded as a vendor payment instead of folded into the
  purchase row.

The advance amount is capped at the receipt's total — a bigger advance (e.g. paid before the
bill/quantity is even known) goes through `vendor-payment.html` directly instead, which already
supports paying a vendor ahead of any purchase being logged.

---

## 5A. Attendance — past-date lock and the Weekly Off monthly cap (as of Oct 15, 2026)

`attendance-entry.html` has two standing rules enforced at the **database** level, not just
hidden in the UI — a manager can't get around either by calling the API directly.

- **Past dates are locked to Directors.** `anon_update_attendance_entries`'s RLS policy only
  allows a write when the entering `app_users` row has `role = 'director'`, OR
  `role = 'shift_manager'` AND the date is `current_business_date()` (today, by the same
  9am Karachi cutover used everywhere else). Store man and Shift Manager both see a lock
  banner in the UI once a date other than today is selected, but the real enforcement is the
  RLS check — all three Director accounts (Yasir, Imran, and the generic Admin account) can
  still fix a past day's attendance; this was confirmed as the intended rule (directors have
  full oversight access everywhere else in the system too), not a gap.
- **Weekly Off is capped per calendar month, hard-enforced.** Added because managers were
  overstating it — one employee already had two Weekly Offs logged in the same week (Oct 10
  and 11) before this was first tightened. Initially enforced as a strict one-per-week rule,
  then same day changed to a **monthly** cap instead — people sometimes skip a week's off and
  take two the following week, which a weekly rule would wrongly block.
  `attendance_enforce_one_weekly_off_trigger` (`BEFORE INSERT OR UPDATE` on
  `attendance_entries`, function name unchanged from the original weekly version, body
  replaced) blocks a `'Weekly Off'` row once the employee's count for that calendar month
  would exceed the cap (`RAISE EXCEPTION`, not just a UI warning) — unless the entering user
  is a Director, who can still override for a genuine exception, same posture as the
  past-date lock.
  - **The cap itself** = the number of Mondays that fall in that calendar month — always 4,
    occasionally 5, depending on where the month starts (never a fixed number, and
    deliberately *not* "every week that touches the month at all", which can hit 6 when a
    30-day month starts on a Sunday and ends on a Monday — e.g. Nov 2026 — since those two
    boundary weeks only contribute one real day each to that month).
  - The UI's pre-check (querying the employee's Weekly Off count for the calendar month
    before saving, so the person gets an immediate message instead of a raw database error)
    matches this: a non-Director sees a flat "X already booked, Y allowed this month" alert
    with no way around it; a Director sees a confirm dialog explaining they're overriding.
  - The pre-existing double Weekly Off (Oct 10/11, the employee that prompted this) was left
    as historical data, not retroactively fixed — ask if that should be corrected.

---

## 5B. Payroll — the 26-day standard

Every employee's `monthly_salary` is a flat monthly figure in `employees`. The per-day rate
used to compute an actual month's `salary_earned` is always `monthly_salary / 26` —
**not** divided by however many calendar days are actually in that month (28–31). This is
intentional: a calendar month averages roughly 4 Weekly Offs, so 26 is the expected number of
*working* days in a normal month, and someone who worked every working day in the month (no
unpaid absences) should be paid their full monthly salary, not something short because the
month happened to have 31 days.

- `perDayRate = monthly_salary / 26` — computed identically in two places:
  `payroll-entry.html` (the real monthly payroll sheet) and `employee-master.html` (a quick
  one-off entry point on the employee's own record). Keep both in sync if this ever changes.
- **Days worked** comes from the month's attendance, not a flat 26: `daysWorkedFromAttendance()`
  sums `Present + 0.5 × "Half Day"` for the period. **Weekly Off days are not counted** as
  days worked, and are also not subtracted — they're baked into the 26 already (a full month
  with no absences nets out to ~26 Present days once ~4 Weekly Offs are excluded from the
  ~30-day month, which is exactly full pay). An absence directly reduces `daysWorked` below 26,
  which reduces `salaryEarned` below the full monthly salary.
- If no attendance was marked at all for the period, it silently defaults to `daysWorked = 26`
  (full month) rather than zero — shown in the UI tooltip as "no daily attendance marked this
  period — defaulted to a full month". `days_worked` is always editable by hand on the sheet
  before saving, and editing it recalculates `salary_earned` live using the same /26 rate.
- Nothing else in the system recomputes payroll from scratch — `reports.html`'s Income
  Statement and `owner-dashboard.html`'s payroll-accrual readout both just read the saved
  `payroll_entries.net_salary`/`salary_earned` values, so this one rate is the only place the
  26-day rule needs to live.

---

## 5C. Inventory Balance Sheet — PKR valuation (added Oct 15, 2026)

`inventory-balance-sheet.html` now shows what the stock is actually worth, not just
quantities.

- **Per item**, a new **Value (PKR)** column = `ending qty × products.current_rate`. An item
  with no rate set (or rate = 0) shows `PKR 0` with a small "no rate" badge rather than
  silently looking like it's worth nothing for a real reason — 22 of the 600 active products
  currently have `current_rate = 0`, and a handful more have no rate at all; worth a pass in
  Item Master.
- **Aggregate**, three tiles above the table — **Total Stock Value**, **Paid For**, and
  **Still Payable** — covering every active item at this location regardless of the
  search/category filter below them (the filter only narrows the table, not these totals,
  since "what is the restaurant's stock worth right now" shouldn't change depending on what
  you happened to search for).
- **The Paid/Payable split is an estimate, stated as one on the page itself.** There's no
  per-unit/lot cost tracking in this system — a unit sitting on the shelf today can't be
  traced back to the specific invoice it came from. So each item's current stock value is
  split using that item's own **lifetime purchase mix**: `paid_ratio = (sum of that item's
  purchases.amount where payment_status='paid') / (sum of all that item's purchases.amount,
  paid + credit, up to the as-of date)`, applied to the item's current value. An item with no
  purchase history at all (e.g. only ever entered via an opening snapshot) defaults to 100%
  Paid rather than overstating what's owed. This is a weighted-average proxy, not a precise
  figure — sanity-checked against today's real data at ~PKR 818k total stock value, splitting
  roughly 47% Paid / 53% Payable, which is a plausible mix rather than a degenerate 0/100.
  Note this is **not** the same number as "Total Payable to Vendors" on
  `vendor-payment.html` — that's vendor-level accounts payable (what's owed in total,
  including stock already consumed); this is specifically the payable portion of what's
  still sitting in inventory right now.

---

## 6. Purchase Orders — Demand → Authorize → Order (advance) → Receive

`purchase-order.html` is the formal path for ordering something **before** it's received,
distinct from `goods-receipt.html`'s "Ad-hoc" mode (a cash buy with no advance planning, e.g.
someone ran to the market). Three stages, gated by role:

1. **Demand** — any manager with access requests an item + quantity (`status = 'Demand'`). No
   vendor yet.
2. **Authorize** — **director only**. Approves (`status = 'Authorized'`) or cancels the demand.
   This is the "director accepts it" step.
3. **Order** — **director only**. Assigns the vendor, confirms quantity and the agreed rate,
   and — added Oct 13, 2026 — optionally **pays an advance right here** before marking it
   Ordered (`status = 'Ordered'`).

Once Ordered, it shows up as a pickable PO on `goods-receipt.html`'s PO mode; saving the receipt
there sets `status = 'Received'`.

### Advance payment at the Order step (added Oct 13, 2026)

Some vendors (e.g. **K&N**, flagged `vendors.requires_advance = true`) won't deliver without an
advance. The Order card has a **"Pay an advance now"** checkbox — auto-checked for a vendor
flagged this way, but any vendor can have it checked by hand for a one-off advance. If a flagged
vendor's box is left unchecked, the person ordering gets a confirmation prompt before the order
goes through anyway (not a hard block — there can be legitimate reasons to skip it).

**The Advance Amount field is left blank on purpose — it does NOT auto-fill from qty × rate.**
Changed Oct 13, 2026: it used to pre-fill the full agreed amount, but K&N's rate moves daily with
the market and the "Agreed Rate" field pre-fills from the product master's `current_rate`, which
goes stale between Item Master updates. On Oct 13, 2026 three K&N advances auto-computed from a
stale rate totaled PKR 45,976 when Zeeshan had actually paid PKR 43,000 cash — the three
`purchase_orders.advance_amount` / linked `vendor_payments.amount` rows had to be corrected by
hand (scaled proportionally to sum to the real 43,000 paid). Whoever places the order now has to
type in the actual amount handed over, not trust a calculated number.

Confirming "Mark as Ordered" with the box checked does two things in one step:
- Saves `advance_amount`, `advance_paid_at`, `advance_payment_method`, `advance_paid_by` on the
  `purchase_orders` row itself (for quick display — this PO shows "Advance of PKR X already
  paid" on both the Order list and on Goods Receipt's PO picker).
- Saves an ordinary **`vendor_payments`** row for the advance amount (linked back via
  `vendor_payments.po_id`) — the same table and the same running-balance math
  `vendor-payment.html` already uses (owed = credit purchases − vendor payments). **This is
  what actually "lowers the receivable" as inventory arrives**: paying the advance before any
  purchase exists makes the vendor's balance go negative (we've prepaid, i.e. a receivable from
  the vendor); when the goods are later received as an ordinary credit purchase for the full
  invoice amount, that payable increase nets back against the prepaid balance automatically —
  no special-casing needed anywhere else. A cash advance also counts on Safe 2's Cash Out the
  same way any cash vendor payment already does.

**Fixed Oct 13, 2026**: `vendor-payment.html` now shows a second big box, "Total Receivable from
Vendors", right next to "Total Payable to Vendors", with its own breakdown card below
("Receivables — they owe us — advances paid ahead of delivery") listing every vendor whose
balance is negative (we've paid more than we currently owe them). Previously those vendors just
vanished from the page entirely — the balance list only ever showed positive balances, and
picking a prepaid vendor from the "Select vendor…" dropdown said "No outstanding balance on file"
with no indication a receivable existed. Selecting one now says plainly "We've prepaid PKR X
ahead of delivery — this is a receivable, not something owed."

**Remember balances are per-location.** `vendor-payment.html` only ever looks at Gulberg's own
`purchases`/`vendor_payments` rows (`location_id` filter) — a vendor's balance here reflects only
what Gulberg itself owes or is owed, not the group's combined balance across branches. K&N is a
good example: as of Oct 13, 2026 K&N's *group-wide* credit purchases (171,944, almost entirely
from another branch) dwarf Gulberg's three advances (43,000) — but Gulberg's own position with
K&N is a receivable (43,000 prepaid, nothing received here yet), which is exactly what this page
now shows. Don't blend numbers across locations when answering "what do we owe/are owed" — always
check the page for the specific location in question.

**Migration-era false receivables, cleared Oct 14, 2026.** Several vendors (Al Tayyab Foods,
Farooq Traders Diesel, FNK Bakery, FNK Grill, Local Market, Al-Barka Water, Sheri FSD) showed up
as receivables for the same reason as K&N above, but for a different root cause: these were real
cash payments settling real **old-system payables** — but the old system's opening payable
balances were never entered into this app, so each payment had nothing to net against and looked
like a pure prepaid advance. Confirmed with the owner that each payment fully settled its vendor's
old-system balance (no remainder owed), then cleared it by booking one `purchases` row per vendor
— `payment_status='credit'`, dated `2025-08-01` (the app's earliest recorded date, used as a
placeholder "opening balance" date since the real invoice dates weren't migrated), amount equal
to the payment, notes explaining it's a migration opening balance — so each balance now nets to
exactly PKR 0. **If a similar "payment with no purchase behind it" surfaces again, don't assume
it's a receivable or an unrecorded Goods Receipt without asking** — it can also be exactly this:
an old-system payable that was never migrated in. Check with the owner which case it is before
booking anything, since the fix (and the amount to book) differs.

**Also notable: `anon_select_purchases`'s RLS only shows a row to the app if
`entered_by_user_id` belongs to a `store_man` or `shift_manager`.** The first attempt at the
fix above set `entered_by_user_id` to the director's own app_user id (reasonable, since the
owner was the one directing the correction) — the row inserted fine, but then stayed invisible
to `vendor-payment.html` itself (the anon key frontend), so the Receivables box looked
completely unchanged even though the data existed. Same bug class as the
`manager_has_page_access` RLS fixes elsewhere in this file: a hardcoded role allow-list that
the fixing query's own actor doesn't satisfy. **When manually inserting into `purchases` (or
any table with a role-gated SELECT policy like this one) always point `entered_by_user_id` at
a real user whose role the SELECT policy actually allows** — here, re-pointed to Gulberg's
shift_manager (`S.Manager`, id `67f7245e-...`) — and verify with a `SET ROLE anon` read
afterward, not just a normal query, since a normal query runs with elevated privileges and
won't catch this.

**Fixed Oct 14, 2026 — `purchases`' RLS was blocking real Goods Receipt users.** Zeeshan
(`cash_custodian`) hit a 401 trying to save a "Paid Now, Cash" Goods Receipt for Malai Boti
Chicken. Root cause: `anon_insert_purchases` and `anon_select_purchases` only allowed
`entered_by_user_id` to belong to `store_man` or `shift_manager` — but `manage-access.html`'s
Manage Access had already granted the `goods_receipt` page to **cash_custodian** (Zeeshan) and
to **director** (Yasir, Admin, Imran), none of whom the RLS recognized. So the page itself let
them in, the UI showed the form, and the save failed at the database with no warning until they
tried. Fixed by widening both policies' role list to
`ARRAY['store_man','shift_manager','cash_custodian','director']`, verified with simulated
anon-role transactions: Zeeshan's insert now passes, an unrelated role (auditor) is still
correctly blocked. **General lesson for this app: a page being reachable via Manage Access
grants is not proof the underlying table's RLS actually permits that role** — the two are
configured completely independently, so whenever a role is added to a page's access list, check
whether that table's RLS role list needs the same addition.

#### Bank payments funded by a Safe 2 cash withdrawal (added Oct 14, 2026)

`vendor_payments.method` describes how the **vendor** was paid, not where the cash physically
came from. Zeeshan sometimes withdraws cash from Safe 2 himself and deposits it to make a bank
transfer (the Al Tayyab Foods / Farooq Traders Diesel payments on Oct 14 were exactly this,
PKR 250,000 and 226,132) — the vendor-facing method is "bank", but the safe still lost that cash
the same as any other cash-out. A new `vendor_payments.funded_from_safe2` boolean (default
`false`) disambiguates this: on `vendor-payment.html`, picking **Bank Transfer** as the method
reveals a checkbox — "Cash was withdrawn from Safe 2 and deposited to make this transfer" —
checked only when that's actually what happened. `cash-reconciliation.html`'s Safe 2 Cash Out
and the All Cash Movements ledger both now match `method=cash OR funded_from_safe2=true`
instead of `method=cash` alone, labeling the bank-but-safe2-funded ones distinctly ("bank
transfer, cash withdrawn from Safe 2") so they're never confused with a straight cash payment.
A plain `method=cash` row needs no flag — it's already counted by the `method=cash` half of that
OR, same as before. The two Oct 14 payments were backfilled with `funded_from_safe2=true` once
this was confirmed with the owner.

**Known parallel gap, not yet fixed:** `goods-receipt.html`'s "Paid Now" purchases have the
identical ambiguity (a Goods Receipt paid by bank transfer could also be funded by a Safe 2
cash withdrawal) but `fetchCashOut`'s `purchases` query still only checks
`payment_method=eq.cash`. Apply the same `funded_from_safe2`-style fix there if this comes up on
a Goods Receipt.

Also noted in passing: **two separate, both-active `vendors` rows are both named "LOCAL MARKET"**
(`46bb7358-...`, unused — zero purchases and zero payments — and `24553593-...`, the one actually
used above). Not yet merged/deactivated; same class of issue as the K&N duplicate-vendor cleanup
earlier, flagged for the owner to confirm before touching it.

### Standalone Authorize page (added Oct 13, 2026)

`purchase-order.html` gates its Authorize panel on `role === "director"` — hardcoded, not tied
to the page-access grant. That means even if Yasir granted someone the "Purchase Orders" page in
Manage Access, they'd still only see the Demand panel unless their manager record's role is
literally "director".

`po-authorize.html` is a separate, standalone page with its **own page key**
(`po_authorize`, labeled "Purchase Order — Authorize" in Manage Access) containing only the
Authorize/Reject panel — no Demand or Order panels. Access is controlled purely by the Manage
Access grant for that key: whoever is granted it can log in and authorize or reject pending
demands, regardless of their role (director, auditor, or anything else). This is how "director
or anyone Yasir chooses" gets to authorize, without touching `purchase-order.html`'s existing
director-only behavior, which is left as-is for backward compatibility.

To let someone else authorize demands: open `manage-access.html`, grant them the
"Purchase Order — Authorize" page, and give them the login code + PIN for `po-authorize.html`.

---

### Owner Dashboard — Expenses drawer label bug + Cash Position carry-forward (fixed Oct 16, 2026)

Yasir reported three things on the Owner Dashboard's Expenses drill-down and Cash Position card:
every expense row showed the generic word "Expense" instead of its real category, Safe 2
expenses looked missing from the drawer, and the Cash Position card didn't reflect the prior
day's cash balance.

**Root cause of the label bug**: the `expenses` table has two parallel category column sets —
legacy `head`/`sub_head` (populated only for a one-time Sep 2025 migration, 586 rows, all dated
Sep 2025) and the current `category`/`subcategory` (what `expense-entry.html` actually writes
today). Zero rows have both populated. `owner-dashboard.html`'s drawer, "Cash Paid Out"
breakdown, and Top Expenses list all selected and rendered `head`/`sub_head`, which is `null`
for every current row — so every modern expense fell back to the literal string `"Expense"`,
regardless of category. "Charge to salary X" entries are actually `category="Payroll"`,
`subcategory="Employee Charge"`; "Charge to Restaurant" entries are
`category="Charge to Restaurant"` with a subcategory like "Complimentary/Comp Charge". Fixed by
switching all three render sites to `category`/`subcategory` via a shared `expenseLabel()`
helper, and adding a `safeLabel()` helper so each row also shows "Safe 1" / "Safe 2" next to the
payment method — which also resolves the "Safe 2 looks missing" complaint: Safe 2 expenses were
already included in the query and in every total, they just weren't visually distinguishable
from Safe 1 ones without a category label to anchor on.

**Cash/non-cash classification** — confirmed with Yasir: today's "Charge to salary X"
(Payroll · Employee Charge) and "Charge to Restaurant" entries are correctly recorded as real
cash leaving the safe at the time of entry (e.g. cash paid now for a bike repair, recovered via
a later payroll deduction) — the existing cash/non-cash split on the Expenses KPI tile is
correct as-is and needed no logic change, only the label fix above so the categories are
actually visible when reviewing the split.

**Cash Position carry-forward** — the Cash Position card (Cash Collected / Cash Paid Out /
Payables Added / Net Cash Movement) only ever showed the selected range's flow, with no opening
balance, so it couldn't say what should actually be sitting in the safes right now. Safe 2's
running balance was already tracked correctly in Daily Cash Safe Check (`cash_safe_ledger`,
carried forward day to day in `cash-reconciliation.html`) — it just wasn't surfaced on the
summary card above it. Added two tiles, **Opening Balance** and **Expected Closing Balance**,
using the same carry-forward logic as `cash-reconciliation.html`'s `fetchPreviousClosing()`:
pull the most recent `cash_safe_ledger` row before the range's start date, use its
`counted_cash` (the custodian's actual physical count) when available, otherwise fall back to
`opening_cash + cash_in − cash_out`. Expected Closing Balance = Opening Balance + Net Cash
Movement. Verified against real data: the row before Oct 15 is Oct 13 (`counted_cash =
1,020,500`, the uncounted Oct 14 gap skipped correctly), which becomes Oct 15's Opening Balance.

---

### Sales Entry / Cash Reconciliation — till overage no longer blocks closing, Safe 2 fixes (Oct 15–16, 2026)

A cluster of related fixes to `sales-entry.html` and `cash-reconciliation.html`, all from the
owner reviewing the Till Cash Reconciliation and Daily Cash Safe Check flows closely on Oct 15:

- **Till overage no longer blocks Save/Close.** Previously, closing a shift with the till short
  OR over by more than PKR 1 required an explicit resolution (charge a shortage to a person/the
  owner, or click "Add excess to handover") before Save would go through. Per the owner: only a
  shortage (missing cash) is a real problem needing a decision — an overage just gets handed to
  the custodian either way, no decision required. Save now only blocks on a short till; a
  positive variance folds into the custodian handover automatically (same math as the old "Add
  excess to handover" button) before the save proceeds, and the audit RPC
  (`resolve_till_variance_v1`, `over_handed`) still logs it. The per-shift UI shows no variance
  explanation at all for an overage (just "PKR X counted — logged" in green) — only a shortage
  shows the Cash Short/Over box, the recount note, and the booking requirement.
- **Fixed a Cash Short/Over double-counting bug.** It used to compare the counted till against
  a handover-dependent "expected closing" figure. If a manager had already typed a bumped
  Actual Handover themselves (e.g. auto 315,475 + a 115 rounding excess = 315,590), the till's
  own "variance" showed that same 115 again (since counted till == float whenever handover ==
  auto + the real variance) — so closing the shift auto-folded the excess into the handover a
  **second time** (115 → 230 doubled). Fixed by comparing the counted till straight against the
  standard float (`openingCashTill`) instead of the handover field — the till returning to its
  float is the only thing this check verifies. (The Oct 15 evening entry that got doubled this
  way was corrected: `custodian_cash_amount` reverted from -315,705 to -315,590,
  `cash_short_over` cleared to 0.)
- **"Actual handover" relabeled "Actual handover (Hard Cash)"**, and "Actual physical cash
  present in till" relabeled "Actual **Hard Cash** left in Till" (bolded), for clarity that both
  fields are physical cash, not card/JazzCash.
- **Closing Safe Cash (Daily Cash Safe Check) is now a pure system calculation**, never the
  counted figure. It used to swap from the calculated `Opening + In − Out` to whatever Zeeshan
  physically counted once a count existed — exactly the kind of ambiguity behind the till bug
  above. Now it's always the calculated figure, labeled "system calculated — Opening + In − Out",
  not editable by anyone. Physical Count is a fully separate check against it: entering a count
  now shows a dedicated variance alert banner for **either** direction (short or over) — unlike
  the till in Sales Entry, an overage in Safe 2 still needs an explanation, since this is the one
  authoritative record of what Zeeshan actually has. (Submitting without an explanation when
  Counted ≠ Expected was already blocked; this just surfaces the mismatch immediately.)
- **Fixed a stale-count bug specific to draft days.** Cash In/Cash Out already recompute live
  for a draft day (fixed 2026-10-13), but `counted_cash` didn't get the same treatment — a
  draft's saved count loaded unconditionally even if it was taken hours earlier, before the
  day's real activity came in, making "Closing Safe Cash" show a stale number. This turned out
  to be the **normal daily rhythm**, not an error: Zeeshan leaves around 8pm and doesn't
  physically count the safe again until he starts his next shift around 11am the next day, so a
  given day's early-morning "count" is really him confirming the *prior* day's closing (= that
  day's opening, since nothing moves in the safe overnight) — it just gets saved under today's
  date because that's whatever page is open. Fixed: a draft's saved count is only trusted when
  it was taken against the same Cash In/Out totals as right now; otherwise the field is left
  blank and an informational (green, not orange) banner explains why — not a call to action.
- **Removed the "Set opening cash (owner only)" manual override entirely.** Opening Safe Cash is
  now always carried forward automatically from the previous day's closing, for every role. This
  was the exact gap that let Oct 15's opening silently drift to 724,346 instead of the real
  703,321 (Oct 14 itself was never actually reconciled/submitted in the system at all — nobody
  opened Daily Cash Safe Check for that date — so someone hand-typed a number into Oct 15's
  opening that didn't match Oct 14's real transactions). Backfilled a proper Oct 14 row
  (submitted, opening 1,020,500 + Cash In 312,930 − Cash Out 630,109 = closing 703,321, zero
  variance) and corrected Oct 15's opening to 703,321 so the chain is continuous again. Any real
  correction now has to go through Cash In or Cash Out instead — each tied to an actual
  transaction (a transfer, an expense, a vendor payment), never a number typed over the chain.
- **Cash In/Cash Out breakdown rows now link to their receipt photos** ("📷 View", opens a
  signed URL) when one exists — `payment_photo_path` on `vendor_payments` (bucket
  `vendor-payment-photos`), `receipt_photo_path` on `purchases` and `expenses` (bucket
  `receipts`). Rows without a photo show "no photo"; till handovers, internal transfers, and
  JazzCash settlements show neither tag since they have no photo concept at all.
- **Whole Day Totals gained an "Excess cash handed over (both shifts)" line** (green,
  informational, shown only when positive) — separate from Cash Short/Over, which now correctly
  reads PKR 0 whenever both tills are at float. This is the sum of each shift's
  handover-minus-auto-generated difference, so the day's rounding excess stays visible even
  though it's no longer flagged as a till problem.

### Duplicate-transaction detection (added Oct 15, 2026)

While reviewing Cash Out receipt photos, the owner caught **4 identical GMSA purchases**
(6 LPG cylinders, PKR 115,770 each, same vendor/product/qty/rate) entered 3 minutes apart on
Oct 15 — almost certainly one real delivery re-submitted 3 extra times (3 of the 4 rows share
the exact same receipt photo). This had gone unnoticed because nothing in the system flagged
duplicate entries; it only surfaced because the owner happened to scan the vendor names in a
breakdown list.

Built a general-purpose duplicate detector, `detect_duplicate_transactions()` (Postgres
function, scheduled via `pg_cron` as job `detect_duplicate_transactions`, every 15 minutes —
same cadence as the existing `daily_task_checklist` job), covering the three transaction types
that move real cash: **purchases**, **expenses**, and **vendor payments**. For each table it
groups the last 3 days of rows by their identifying attributes (purchases: vendor + product +
qty + rate; expenses: category + subcategory + amount + detail; vendor payments: vendor +
amount + method) and flags any group with more than one row entered within a 30-minute window —
tight clustering is what distinguishes an accidental resubmission from two genuinely separate
same-day transactions that happen to match. Each flagged group writes a `high`-severity row to
`audit_alerts` (`alert_type = 'duplicate_transaction'`) with the matching record IDs listed in
the body, so it shows up automatically in the Owner Dashboard's existing "Open Audit Alerts"
section — no new UI needed.

Unlike the fixed daily-checklist alerts (`check_daily_task_completion`), duplicate groups aren't
enumerable in advance, so this function takes a simpler approach: it bulk-resolves every open
`duplicate_transaction` alert at the start of each run, then re-inserts fresh ones for whatever
duplicates still exist — avoiding orphaned alerts that never got explicitly cleared.

The Oct 15 GMSA duplicate itself was left as-is in the data. The owner was explicit that this
class of correction is not Claude's to make: whoever entered the mistaken rows (Zeeshan / the
store man) should fix it themselves, through the app, not via a direct database edit. That is
what the void/correct capability below is for — the alert stays open until it's fixed that way.

### Self-service void/correct on Goods Receipt (added Oct 16, 2026)

Until now, nobody but a director (via the Owner Dashboard's PIN-gated delete) could undo a
mistaken purchase entry — `purchases` had no `anon` UPDATE policy at all, so even the page that
creates receipts (`goods-receipt.html`) had no way to fix one afterwards. Added:

- An `anon_update_purchases` RLS policy (purchases previously allowed anon INSERT/SELECT only),
  mirroring the existing `anon_update_expenses` policy: any active store_man / shift_manager /
  cash_custodian / director at the location can update a purchase row.
- A "Entered by mistake? Void / correct this entry" link under each row in Goods Receipt's
  "Received Today" list. Voiding requires a typed reason, then zeroes `qty` and `amount` (so
  every existing report, inventory and cash-reconciliation query already treats it as if it
  never happened — no other page needed changes) while preserving the original `qty`/`rate`/
  `amount` and the reason in new columns (`voided_at`, `voided_by_manager_id`, `void_reason`,
  `original_qty`, `original_rate`, `original_amount`) for a full audit trail. Follows the
  project's standing no-DELETE rule — nothing is ever removed, only corrected with a note.
  The voided row still shows in the day's list, struck through, with the reason underneath.

The GMSA duplicate (and any future one like it) gets fixed this way, by whoever entered it —
not by a direct SQL correction.

### Broader AI audit checks (added Oct 16, 2026)

Four more `pg_cron` jobs (`0 * * * *`, hourly), each a Postgres function following the same
shape as `detect_duplicate_transactions()` — bulk-resolve its own alert_type, re-insert fresh
findings, write to `audit_alerts` so everything surfaces on the Owner Dashboard automatically:

- **`detect_price_anomalies()`** — flags a purchase whose rate is ≥25% off the median of that
  same item+vendor's last purchases in the prior 60 days (needs ≥2 prior purchases to have a
  baseline, so a first-time item/vendor pairing never false-positives).
- **`detect_inventory_anomalies()`** — reads the daily stock-count entries
  (`variance_daily_entries`): flags a negative closing count or a negative implied usage
  (physically impossible), and flags a day's opening count that doesn't match the prior day's
  closing count for the same item (the same carry-forward problem fixed earlier in Safe 2,
  now watched for in inventory too).
- **`detect_vendor_payment_anomalies()`** — flags a vendor payment that exceeds what's recorded
  as owed to that vendor (credit purchases to date minus payments already made), skipping
  payments whose notes say "advance" since those are legitimately paid before any purchase
  exists yet. Framed as "worth confirming," not an accusation — it can be a legitimate advance.
- **`detect_missing_documentation()`** — flags a purchase, expense, or vendor payment of
  PKR 10,000+ with no receipt/payment photo attached.

All four were run once by hand against live data as a smoke test and found several genuine,
pre-existing items worth a look (an onion purchase at a rate well off its recent median; several
large cash transactions missing a receipt photo; two vendor payments — Al Tayyab Foods and
Farooq Traders Diesel — that exceed their recorded credit-purchase balance). None of these were
corrected — they are sitting as open audit alerts for review, same as the GMSA duplicate.

**Known gap, flagged but not fixed:** `expense_categories` and `expense_subcategories` have RLS
disabled entirely (fully exposed to the anon key, unlike every other table). This was surfaced
by Supabase's own advisory, not asked for — it needs a decision on which policies to add before
enabling RLS (enabling it with no policies would block the Expense Entry/Edit dropdowns
entirely), so it was deliberately left alone pending the owner's decision.

### Monthly Cash Priority Waterfall (added Oct 16, 2026)

The owner described a real payment priority order for how the month's sales cash actually gets
spent: salaries first (paid on the 7th of the following month, from the first week's cash),
then building rent and electricity, then dairy & protein vendors -- cheese and chicken --
sized to 10-14 days of average sales, with clearing cheese payments the priority within that
tier, then whatever inventory needs to stay at roughly its starting level, with the true
leftover being profit.

New table `cash_allocation_priorities` (one row per priority tier, ranked) holds this as data
rather than code, so the owner can change a target figure without asking for a code change:

| rank | name | calc_type | target |
|---|---|---|---|
| 1 | Staff Salaries | fixed_monthly | PKR 1,800,000 |
| 2 | Fuel & Delivery (KM) | actual_category | tracked, no fixed target -- varies |
| 3 | Building Rent | fixed_monthly | PKR 800,000 (Utilities > Building Rent subcategory) |
| 4 | Electricity | fixed_monthly | PKR 900,000 (midpoint of the stated PKR 7-11 lac range) |
| 5 | Dairy & Protein Vendors | vendor_category_days | 12 days of average daily sales (midpoint of 10-14) |
| 6 | Inventory Maintenance Reserve | inventory_baseline | informational only, no baseline snapshot yet |

The Owner Dashboard's new "Monthly Cash Priority Waterfall" card (`loadCashWaterfall()`) reads
this table plus the calendar month-to-date numbers (sales, Payroll/Fuel & Gas/Utilities
expenses, dairy+protein vendor payments) and walks the tiers in rank order: each tier claims
its target out of the month's cash-in so far, and whatever's left after all tiers is shown as
"left over (profit, before inventory check)" -- or a shortfall, in red, if the fixed tiers alone
already exceed what's come in. **This is advisory/dashboard-only, by the owner's choice** --
nothing here blocks or warns against an actual payment; it is purely visibility into whether
this month's priorities are on track.

Two things worth knowing:
- The Oct 10 rent entry was saved with no subcategory (just "Building rent" typed into the
  detail field), even though a "Building Rent" subcategory already exists under Utilities. The
  waterfall falls back to matching `detail ILIKE '%rent%'` so it still picks it up, but going
  forward rent should be entered with the Building Rent subcategory selected, so it's reliably
  tagged without relying on text matching.
- The inventory tier is informational only for now -- there's no stored start-of-month baseline
  to compare against yet (`inventory_snapshots` is empty). Once a snapshot exists, this tier can
  compare current inventory value to it and flag whether cash was actually freed by running
  inventory down rather than genuine profit.

### Cash Priority & Payments page (added Oct 16, 2026)

The waterfall above lived only on the Owner Dashboard, which the owner didn't want to open up
to managers wholesale. Split it out into its own page, `cash-priority.html`, with its own
page_key (`cash_priority`) so it can be granted to specific managers from Manage Access without
giving them the rest of the Owner Dashboard. It shows:

- **Cash Available Right Now** — Safe 2's latest actual count (or expected figure if not yet
  counted), same carry-forward logic as Cash Position elsewhere.
- **This Month's Priorities** — the same waterfall tiers as the dashboard card.
- **Suggested Payments Today** — new. Takes cash-on-hand, holds back whatever's still short on
  an unfunded fixed tier (salaries/rent/electricity) this month, then proposes specific vendor
  payments against outstanding balances with whatever's left — dairy (cheese) vendors first,
  then protein (chicken), largest balance first within each, stopping when the cash runs out.
  Each suggestion deep-links to `vendor-payment.html?vendor=<id>&amount=<n>`, which now reads
  those params and pre-fills the form (`applyPrefillFromUrl()`) -- the manager still has to
  review and hit Save themselves, nothing is submitted automatically.
- **Outstanding Vendor Balances** — same payables calc as the dashboard, with dairy/protein
  vendors tagged.

Purely advisory, same as the dashboard card — no payment is blocked or auto-submitted.

---

## 7. Open items / things still being built out

This system is being built incrementally. When something needed isn't there yet, it gets
listed here until it's resolved — treat this as the punch list, not just a changelog.

- Inventory balance sheet, attendance rollout to store man, and tighter sales/expense entry
  controls are in progress (as of Oct 12, 2026).
- Cost of Sales currently uses expense categories as a stand-in for true COGS. Once the
  inventory balance sheet is live, this should switch to actual consumption-based COGS.
- The 79 "OTHER" / 1 "Test Category" inventory items in Item Master still need individual
  review (searchable in Item Master by typing "OTHER" or "Test Category").
- `daily_sales` has a bad row dated 2099-01-03 — needs correcting (doesn't affect bounded
  date-range reports, but will corrupt any future "all-time" query).
- Stock Count has never actually been used (`inventory_snapshots` is empty) — the owner's
  focus has been on removing quirks on the sales/expense side first; Stock Count is next, "in
  the next couple of days" as of Oct 16, 2026. Once real counts start flowing in, two things
  are waiting on it: the Reorder Alerts card on the Owner Dashboard (currently shows everything
  as "uncounted"), and a Restock Forecast tier for the Cash Priority Waterfall/Cash Priority &
  Payments page (reorder_qty × current_rate for anything below min_stock_level, plus a real
  beginning-vs-ending inventory value check instead of today's placeholder row).
