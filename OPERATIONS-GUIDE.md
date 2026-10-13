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
- **`requires_rgm_approval`** — true only for "Charge to Restaurant". An entry under this
  head cannot be saved without the RGM entering their PIN first (enforced both in the UI and
  by a database trigger — it fails even if someone bypasses the app and hits the database
  directly). The Owner Dashboard shows a daily audit panel of every approval.

**Subcategories** are managed inside the same page (expand a category → Subcategories
section). A category with no subcategories just skips that dropdown on the entry form.

**If a new category is added**, give it a `code`/`group_name` right away — an expense
category without one shows up on the Income Statement under a red "Uncategorized / Needs
Review" banner until it's fixed. That banner is deliberate: it's the system catching an
unclassified expense before it quietly skews a financial statement.

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

### Safe 1 — Till Cash Reconciliation (Sales Entry)

This is an **audit check**, not a data-entry chore — almost everything fills in on its own.
Each shift's till always opens — and is expected to close — at the standard **PKR 40,000**
float (set server-side by a DB trigger on insert; no longer carried forward from whatever the
previous shift's physical count happened to be, so a miscount can't silently compound into the
next shift). The shift manager's only required input is the **actual physical cash count**
at the end of the shift. Everything else:

- **Cash sales this shift** — computed from the sale amounts already on the form.
- **Cash expenses this shift** — pulled live from Daily Expense entries tied to this same
  shift and date, cash payment method only. (This is scoped to ONE shift — the "Today's
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
- The old "evening manager sees a read-only Morning recap" card is gone — now redundant, since
  both shifts are always visible together on the same screen.

### Safe 2 — Cash Reconciliation (Zeeshan's safe)

Opening (carried from yesterday's count, or set once by hand for day one of using this system)
+ Cash In (the day's till handovers, i.e. the Safe 1 custodian amounts above) − Cash Out
(expenses/vendor payments/goods receipts paid **directly from the safe**, no shift attached —
a shift-tied expense already shows up as a smaller Safe 1 handover, so counting it here too
would double it) = Expected, compared against Zeeshan's physical count.

Cash Out is three sources combined:
1. Daily Expense entries with no shift and payment method = cash.
2. Vendor Payments with method = cash (paying down a payable logged earlier on Goods Receipt).
3. **Goods Receipt entries marked "Paid Now" → Cash** — added Oct 13, 2026. A receipt paid on
   the spot never goes through Vendor Payments (there's no payable to pay down), so without this
   it vanished from the cash trail entirely. `purchases.payment_method` (cash/bank, only
   meaningful when `payment_status = 'paid'`) drives this — Goods Receipt now asks "Paid How?"
   whenever "Paid Now" is picked, defaulting to Cash.

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

**Total Payable to Vendors** moved off this page — it now lives at the top of
`vendor-payment.html`, which is where it's acted on.

---

## 6. Open items / things still being built out

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
