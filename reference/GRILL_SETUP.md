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

## October 23 follow-up — Grill's actual item list, pulled from the Excel

You flagged, correctly, that the Grill pages were showing C-5's full shared
catalog instead of Grill's own items: "you have copied the same inventory
from c-5. it has different items. get it from the excel file." That's
because `products` has no per-location scoping at all — every mirrored
page's Stock Count / Purchase Orders / Goods Receipt / Issue Entry /
Inventory Balance Sheet was pulling the entire ~800-row shared catalog, not
a Grill-specific subset.

**What was wrong, specifically:** the original build only wired up the 9
finished-product codes that branches *buy from* Grill (Malai Boti, Steak
Fillet, etc.) — it never built Grill's own day-to-day operating item list
(the raw materials, spices, sauces, cleaning supplies, packing material,
crockery and office supplies Grill's own staff purchase, count and issue).
Your Excel's `INVENTORY` sheet has that full list — 90 items across 8
categories.

**The fix:**
1. Read the Excel's `INVENTORY` sheet in full (not just the 9 fast-track
   codes) — 90 real stockable items (one Excel row, "RENT," was dropped as a
   misfiled expense line, not a real inventory item).
2. Matched each item against the existing shared catalog by name (allowing
   for typos/spelling differences between your Excel and the catalog, e.g.
   "MURGI MASALA" ↔ "MURGHI MASALA", "ACHAR GOAST" ↔ "ACHAR GOSHT MASLA") —
   53 of the 90 already existed under the catalog's normal code scheme and
   were reused as-is, no duplicates created.
3. Added **37 new products** for items that genuinely didn't exist yet
   (MALAI BLEND, BEHARI BLEND, HOT SAUCE, FRESH CREAM 1-LTR, DUSTER, TONG,
   FRIES MACHINE, etc.) — all under a fresh `GRL-xxx` code prefix, chosen
   specifically so they can never collide with the catalog's own numbering
   or with your Excel's own "BB" code scheme (which reuses strings like
   "1.1.01" and "1.3.14" for completely unrelated items already in the main
   catalog).
4. Updated all 5 Grill pages that load products
   (`grill-inventory-balance-sheet.html`, `grill-stock-count.html`,
   `grill-purchase-order.html`, `grill-goods-receipt.html`,
   `grill-issue-entry.html`) to filter to exactly this 90-code list instead
   of pulling every active product in the system.

**A real bug this surfaced, and fixed:** the THAI and CHEST raw-chicken
products added in the first pass last night were accidentally given codes
`FD-200` / `FD-201` — which, it turns out, already belonged to two
unrelated, active products: **FUSILLI 400 GM** and **FRENCH LOAF**. Nothing
in the database stops two products from sharing a code (there's no unique
constraint on `products.code`), so this collision wasn't caught until this
pass's checks. Renamed THAI → `GRL-038` and CHEST → `GRL-039`; FUSILLI and
FRENCH LOAF were untouched. Separately — not Grill's doing, just flagged
while checking — the shared catalog already has three other pairs of
duplicate codes elsewhere (`MK-020`, `2.3.05`, `Bar224`), pre-existing and
unrelated to this work; worth a cleanup pass sometime, not urgent.

The full 90-code list each Grill page now filters to lives in a
`GRILL_ITEM_CODES` constant right next to that page's `LOCATION_ID` —
same mirroring convention as everything else in this app.

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
in the catalog: **Thai** and **Chest** (raw chicken cuts, code `GRL-038` /
`GRL-039` as of the Oct 23 follow-up below — originally assigned `FD-200` /
`FD-201`, which turned out to collide with two unrelated existing products;
see that section — unit KG, preferred vendor AR CHIKES). Starting rates
(740 / 735) are rough averages from the September purchase log in your
Excel — these will drift with the market, so treat them as a starting
point, not gospel.

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
3. Spot-check the 37 new `GRL-xxx` items' starting rates (Item Master) —
   they're taken straight from your Excel's `INVENTORY` sheet rate column,
   not independently verified against a current purchase.
4. None of the new items have a `preferred_vendor_id` set (unlike THAI/
   CHEST, which point at AR CHIKES) — your Excel names several Grill-specific
   vendors (FNK SPICE, ARIB SPICE, AHMAD FOOD, NESTLE, SHERI CHEMICAL, GMSA
   LPG, etc.) that don't exist in the system yet. Didn't create them
   unilaterally since that's its own small decision (merge into an existing
   similarly-named vendor vs. add new) — say if you want them added.
3. Confirm the THAI/CHEST starting rates (740 / 735) are reasonable, or give
   current ones.
4. Say when you want the sell-to-branch page designed — that's the next
   real piece of new work here, not a mirror.
5. Decide what to do about the Cash Reconciliation gap (company-wide table,
   not per-branch) — low urgency, but worth knowing it's there.
