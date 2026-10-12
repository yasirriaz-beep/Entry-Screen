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

## 5. Till Cash Reconciliation (Sales Entry)

Each shift's till starts at a standard float (PKR 40,000) and should also **end** at that
same float — the custodian sweeps anything above it out of the till. As of Oct 12, 2026,
`sales-entry.html` has a dedicated **"Cash left in till for next shift"** field, separate from
"Closing cash in till (physical count)":

- **Closing cash in till** = the full physical count before any of it leaves the till.
- **Cash left in till for next shift** (defaults to 40,000) = what's deliberately kept behind
  as next shift's opening float. This is what actually carries forward as the next shift's
  opening balance (previously the system carried forward the raw closing count, which silently
  propagated any miscount or shortfall into the next shift).

Formula: `Implied cash expenses = Opening + Cash Sales + Custodian ± − Closing + Leftover`.
Leaving the full 40,000 float no longer looks like an unexplained cash shortfall — it's added
back in. This should match what the Cash Custodian separately recorded as cash expenses paid
directly out of the till; a mismatch means a recount is needed.

The Owner Dashboard's cash-recon audit list and the "Morning shift" recap shown to the evening
manager both use the same corrected formula.

**Older rows** (saved before Oct 12, 2026) have no `till_leftover_amount` — the system falls
back to their raw `closing_cash_till` for continuity, same as before.

---

## 6. Cash Reconciliation (the Safe page) — why Cash In / Cash Out can read PKR 0

`cash-reconciliation.html` tracks the **safe**, one level up from the till. Its Cash In and
Cash Out are pulled automatically — there's nothing to type in on that page itself — and they
depend on upstream data existing for that same day:

- **Cash In** comes from the till-to-safe handover (`custodian_cash_amount` on `daily_sales`).
  It stays PKR 0 until a shift manager actually fills in and saves the Till Cash Reconciliation
  section on `sales-entry.html` for that shift (custodian amount + closing cash). Sales amounts
  alone (covers/revenue) don't trigger this — the handover has to be entered and saved
  separately, same shift.
- **Cash Out** only counts expenses and vendor payments paid **directly from the safe**
  (`shift` left blank on the expense). A shift-tied expense was already paid out of the
  cashier's till during the shift, and shows up as a *smaller* Cash In instead — counting it
  again here would deduct it twice. So a day where every cash expense was logged against a
  shift will correctly show Cash Out = 0; that's by design, not a bug.

If both read 0 on a day with real activity, check: (1) has every shift for that day actually
saved its Till Cash Reconciliation section, and (2) were the day's cash expenses meant to be
paid from the safe directly (no shift) or from a till during a shift (shift set) — only the
former shows up here.

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
