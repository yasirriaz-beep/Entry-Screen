# General ledger layer — plan & foundation

Started 2026-10-08. Goal: a real double-entry ledger sitting underneath the operational
screens, structured so it can be exported as QuickBooks General Journal Entries later if this
ever becomes a product sold to other restaurants. Built additively — new tables only, nothing
existing touched — specifically so it carries zero risk to the 2026-10-09 Gulberg mock run.

## What's built (schema only, nothing wired yet)

Three new tables, via migration `gl_foundation_chart_of_accounts_and_journal`:

- **`chart_of_accounts`** — `code`, `name`, `type` (asset/liability/equity/revenue/expense),
  `normal_balance` (debit/credit), `active`. Seeded with a starter chart (see below). Edit
  freely — nothing depends on these exact codes yet.
- **`journal_entries`** — one row per business event: `entry_date`, `source_type` (free text:
  `goods_receipt`, `vendor_payment`, `issuance`, `sales`, `expense`, `payroll`, `writeoff`,
  `manual`), `source_table` + `source_id` (points back at the operational row that caused it,
  e.g. the `purchases.id`), `description`, `created_by`.
- **`journal_entry_lines`** — the Dr/Cr lines for a journal entry: `account_id`, `debit`,
  `credit` (never both nonzero on one line), `memo`.

RLS: read-only for now (`select using (true)`) — no insert/update policy exists yet, so nothing
can post to these tables from the app until that's deliberately added per source type. This is
intentional: the tables exist, but nothing writes to them until each event type is wired
one at a time (below).

Starter chart of accounts seeded:

| Code | Name | Type |
|---|---|---|
| 1000 | Cash | asset |
| 1010 | Bank | asset |
| 1100 | Accounts Receivable - Card & Delivery | asset |
| 1200 | Inventory - Store (General) | asset |
| 1210 | Inventory - Drinks | asset |
| 1220 | Inventory - Bakery | asset |
| 2000 | Accounts Payable | liability |
| 2100 | Accrued Payroll | liability |
| 4000 | Sales - Dine In | revenue |
| 4010 | Sales - Takeaway | revenue |
| 4020 | Sales - Delivery | revenue |
| 4030 | Sales - Food Panda | revenue |
| 4040 | Sales - Third Party (Careem/Other) | revenue |
| 4050 | Sales - Bakery | revenue |
| 5000 | Food Cost (COGS) | expense |
| 5010 | Payroll Expense | expense |
| 5020 | Operating Expense | expense |
| 5030 | Inventory Shrinkage / Waste | expense |

## The intended posting map (not yet wired — do one at a time)

| Source event | Dr | Cr |
|---|---|---|
| Goods Receipt (credit purchase) | Inventory (1200/1210/1220 by department) | Accounts Payable (2000) |
| Goods Receipt (cash purchase) | Inventory | Cash (1000) |
| Vendor Payment | Accounts Payable (2000) | Cash/Bank |
| Issue to Kitchen/Floor | Food Cost (5000) | Inventory |
| Drinks/Bakery Discard | Inventory Shrinkage (5030) | Inventory (1210/1220) |
| Daily Sales (per channel) | Cash / AR (card, delivery) | Sales - <channel> (4000s) |
| Expense Entry | Operating Expense (5020) or the specific head | Cash/AP |
| Payroll | Payroll Expense (5010) | Cash or Accrued Payroll (2100) |

Plan is to go through this list **one row at a time** starting tomorrow (2026-10-09, after the
mock run), each as a small trigger that posts a balanced journal entry on insert, tested in
isolation before moving to the next row. First target: **Goods Receipt**, since that's what
prompted this (the vendor-payment "pull up what's owed" question). Do not wire several of
these in one sitting — each one touches a live operational table's trigger surface, and that's
exactly the kind of change to make section by section, not all at once.

## QuickBooks export (future, not started)

Once journal_entries/journal_entry_lines are actually being populated, exporting them as a
QBO-importable General Journal Entry CSV (or IIF) is a bounded, separate piece of work — one
query joining the two tables plus the chart of accounts, formatted to QBO's import spec. Not
needed until there's real posted data to export.
