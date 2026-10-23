# Grill setup — October 2026

Built overnight from the Excel workbook you sent
(`MALAI_BOTI_FILE_01-SEP_-2026`) while you were asleep, following the same
"mirror C-5" approach used for the other branches. This file records exactly
what was done, the judgment calls made along the way, and what's
deliberately left undone for you to review.

## What already existed (found, not built tonight)

Turns out Grill wasn't starting from zero — some of this was already wired
up in Supabase before tonight:

- A vendor row named **FNK GRILL** (`fast_track = true`) already existed, so
  branches could already see Grill as a fast-track vendor.
- Five of Grill's finished products already existed in the shared `products`
  catalog with `fast_track_vendor_id` pointed at that vendor: **Malai Boti**
  (FD-003), **Steak Fillet** (FD-004), **Behari Chicken** (FD-005), **Peri
  Peri Sauce** (FD-108), **Steak Sauce** (1.8.21) — plus **Grill Brush**
  (3.4.11) and **Peri Peri Blend** (1.6.07) without fast-track wiring (brush
  isn't sold to branches; blend may need it, see Open Items).
- **AR CHIKES** (the chicken supplier) did *not* exist as a vendor yet,
  despite being referenced in earlier engagement notes — added tonight.

## What was added tonight

**Location.** A new `locations` row: code `GRL`, name "Grill", city
Faisalabad, id `10000000-0000-0000-0000-000000000008`. The existing FNK
GRILL vendor's `linked_location_id` now points at it — this is the column
that will let a future report pull "sales to branches" straight from the
purchase-order rows branches already place against this vendor, instead of
needing a second ledger kept in sync by hand (see Open Items).

**Vendors.** Added **AR CHIKES** (category PROTEIN, credit terms, not
fast-track — it's Grill's own upstream supplier, not something a branch
orders from).

**Raw material items.** Added two products Grill actually needs that weren't
in the catalog: **Thai** and **Chest** (raw chicken cuts, code FD-200 /
FD-201, unit KG, preferred vendor AR CHIKES). Starting rates (740 / 735) are
rough averages from the September purchase log in your Excel — these will
drift with the market, so treat them as a starting point, not gospel.

**Payroll roster.** Added Grill's three employees to the `employees` table,
scoped to the new Grill location, with the figures from the Pay Roll sheet:

| Name | Designation | Type | Monthly salary |
|---|---|---|---|
| Ahmad Sb | Production Manager | FT | 100,000 |
| Imtiyaz | Helper | FT | 43,000 |
| Zohaib | Helper | FT | 35,000 |

Only Imtiyaz and Zohaib are plain roster entries (payroll/attendance only,
no system login) — same pattern as helper-level staff elsewhere in the app.

**Login.** Ahmad Sb got an actual account to run Grill day-to-day:
- `app_users` row, role `shift_manager`, location = Grill.
- `managers` row, login code **AS**, **no PIN set yet** — I deliberately did
  not invent one. Set his PIN yourself from Manage Access
  (`manage-access.html`, works the same everywhere since it's shared across
  the whole system) once you're back, the same way you'd set anyone else's.
- Page access granted: Expense Entry, Attendance, Purchase Orders, Goods
  Receipt, Issue Entry, Stock Count (full), Inventory Balance Sheet
  (view-only — see below). Not granted: Payroll, Employee Master (director/
  cash_custodian-only everywhere in this app, not just for Grill — you
  already have cross-branch access to run Grill's payroll yourself from
  `grill-payroll-entry.html`).

**Role choice.** There's no "Production Manager" role in the system yet —
the closest functional match with the write-access Ahmad Sb actually needs
(expenses, purchases, issues, attendance) is `shift_manager`, so that's what
I used. It's a label mismatch, not a permissions problem — worth a proper
`production_manager` role later if that bothers you, but didn't want to
touch the role list and its policies unilaterally overnight for one person.
Flag it if you want it cleaned up.

**Pages.** Mirrored ten of C-5's pages for Grill, exactly the same way
future branches will be mirrored — same files, LOCATION_ID swapped to
Grill's, titles relabeled, nothing about C-5's own files touched:

`grill-home.html`, `grill-expense-entry.html`, `grill-attendance-entry.html`,
`grill-purchase-order.html`, `grill-goods-receipt.html`,
`grill-issue-entry.html`, `grill-stock-count.html`,
`grill-inventory-balance-sheet.html`, `grill-payroll-entry.html`,
`grill-employee-master.html`, `grill-reports.html`.

`grill-home.html`'s menu is deliberately shorter than C-5's — no daily
checklist, sales entry, POS upload, delivery/diesel tracking (no retail
counter here) and no fast-track demand (that's how a *branch* orders from
Grill, not something Grill itself uses). Item Master and Manage Access link
straight to the existing shared pages (`item-master.html`,
`manage-access.html`) rather than being mirrored — those two already work
across every location as-is, nothing Grill-specific needed.

The **Grill tile on `/locations.html`** now links to `grill-home.html` and
shows "Live."

Syntax-checked every file (Node parse of each inline `<script>` block) and
re-grepped for stray "C-5" text after the mirror pass — all clean.

## Deliberately NOT built tonight

**"Sell to branch" revenue page.** This is the one genuinely new piece from
our earlier conversation — recording what Grill delivers to which branch, at
what price, so it hits both that branch's purchase and Grill's own revenue.
It's new business logic affecting money, not a mirror of anything that
exists, so it deserves your eyes before I build it rather than me guessing
at the UI overnight. Until it exists, **Grill's Reports → Income Statement
will show real costs and payroll but zero revenue** — that's expected, not
a bug, and will stay that way until this page exists. The clean way to do
it without a second ledger: query `purchases` where `vendor_id` = the FNK
GRILL vendor, grouped by date/branch — the `linked_location_id` set tonight
is what makes that possible without duplicate bookkeeping.

**Cash Reconciliation on `grill-reports.html`.** Found a real gap while
mirroring: `cash_safe_ledger` has no `location_id` column at all — it's one
shared table for the whole business, not per-branch. That means Grill's
Cash Reconciliation tab currently shows the *same* company-wide cash data
C-5's does, not Grill-specific numbers. I didn't rip the tab out blind at
this hour without being able to see it rendered, but don't trust that one
tab's numbers as Grill's own yet — the other tabs (Sales, Expense, Purchase,
Vendor Payment, Income Statement) are correctly scoped to Grill via
`location_id`, just not Cash Reconciliation.

**Recipe/BOM costing.** The "Malai Chicken" ingredient breakdown in your
Excel (coconut, cream, blend, chicken → cost per batch) is real and useful,
but building that properly is its own piece of work, not something to bolt
on tonight.

**Peri Peri Blend fast-track wiring.** Unlike the other five Grill products,
`1.6.07 PERI PERI BLEND` has no `fast_track_vendor_id` set. Might be
intentional (maybe it's a Grill-internal ingredient, not something sold to
branches) or might just be a gap in what already existed before tonight —
didn't want to guess either way.

**C-1 inventory transfer mechanic.** Your Excel's inventory sheet also has
raw-stock transfer columns to/from specific branches (not just finished-
goods sales) — noted, not built. Worth discussing once the sell-to-branch
page is designed, since it may be the same underlying mechanism.

## For your review when you're up

1. Set Ahmad Sb's PIN (Manage Access, login code **AS**).
2. Confirm the `shift_manager` role reuse is fine, or say if you want a
   proper Production Manager role instead.
3. Confirm the THAI/CHEST starting rates (740 / 735) are reasonable, or give
   current ones.
4. Say when you want the sell-to-branch page designed — that's the next
   real piece of new work here, not a mirror.
5. Decide what to do about the Cash Reconciliation gap (company-wide table,
   not per-branch) — low urgency, but worth knowing it's there.
