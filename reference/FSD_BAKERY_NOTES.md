# FSD Bakery — reference notes

Source file: `FSD_BAKERY_FEB-2026.xlsx` (same folder). This is the central bakery's own
operating file (Yasir calls it a separate entity that bakes in-house and bills the
full amount to each branch, Gulberg/C-5 included). Full bakery financials are a
**later** build — not done yet. These notes are so a future session doesn't have to
re-derive the structure from scratch.

## Sheets
`P&L WITH EXP.`, `PURCHASE`, `EXPENSES`, `INVONTERY FEB` (bakery's own raw-material
inventory — flour, "SPONAGE", etc. — not finished-goods), `ISSU`, `DAILY UPDATE`,
`AMOUNT UPDATE`, `PAY ROLL`, `ENDING AND MAKE`, `ORDER SENT`, `B-M`, `Sheet3`,
`Sheet2`, `GENERATOR`.

**`ENDING AND MAKE` and `ORDER SENT` are a stale 2022 template** (dated Aug 2022,
never updated) — do NOT use them as the live source. Per Yasir (2026-10-08):
> "the information that is sent to branches are in the daily update tab"

## `DAILY UPDATE` — the live source, structure
One row per date (col A). Columns repeat in **17-column blocks per branch**, in this
order: `C-1 (KOHINOOR)`, `C-2 (SUSAN ROAD)`, `C-5 (GULBERG)`, then a `TOTAL` block,
then cash-safe columns. (Despite the "KOHINOOR"/"SUSAN ROAD" labels here, cross-check
against the main `locations` table before trusting branch codes — this bakery file's
own C-1/C-2/C-5 numbering may or may not line up 1:1 with the app's `locations.code`.)

Gulberg's block is columns **AJ:BA** (36–53). Row 2/3/4 hold the category label, the
column code, and that item's price (PKR) respectively:

| Col | Code | Price (Feb 2026) | Best-guess meaning |
|---|---|---|---|
| AJ | C/C | 1100 | Unclear — ask Yasir |
| AL | C.2.P | 2399 | Unclear, Gulberg-only column (no equivalent in C-1/C-2 blocks) — ask Yasir |
| AM | CT-1 | 1499 | Cake, size/weight tier 1 |
| AN | CT-2 | 1699 | Cake, size/weight tier 2 |
| AO | CT-3 | 1899 | Cake, size/weight tier 3 |
| AP | PAS | 250 | Pastry |
| AQ | LAV / CAK | 275 | Unclear ("LAV" header, "CAK" sub-label) — ask Yasir |
| AR | CUPCAKE REG | 220 | Cupcake, regular |
| AS | CUPCAKE CUS | 320 | Cupcake, custom |
| AT | SUN | 220 | Sundae |
| AU | 3 MILKI | 450 | Three Milk Cake (spelled "3 MILK"/"3 MILKI"/"T.M.S" inconsistently across sheets) |
| AV | C.B | 120 | Unclear (maybe "Choco Ball"?) — ask Yasir |
| AW | BRO | 275 | Brownie |
| AX | DIME | 1000 | Unclear (also spelled "DIM"/"DIMI"/"DIME" across branches) — ask Yasir |
| AY | TOTAL/SALE | — | computed, not an item |
| AZ | CASH/REC. | — | cash received, not an item |
| BA | CASH/BAL | — | balance, not an item |

The `ORDER SENT` tab (stale, but useful for cross-reference) breaks the "CAKE"
category down by **flavor** instead of size: Black Forest, Kit Kat, Almond, Coffee
Kaju, Bounty, Fe Roacher, Lotus Fudge, Caramel, Royal Fruit, Pineapple, Kulfa, Red
Velvet — plus Pastry (Kit Kat/Bounty/Caramel), Cupcake (Chocolate/Caramel/Red
Velvet), Sundae (Bounty/Red Velvet/Chocolate), Brownie. `DAILY UPDATE` only tracks by
size tier, not flavor, so flavor-level variance isn't currently trackable from the
live sheet.

## What's seeded so far
The CT-1/CT-2/CT-3/PAS/CUPCAKE-REG/CUPCAKE-CUS/SUN/3MILK/BRO items above were added
to `variance_items` (department='bakery', location=Gulberg/C-5) on 2026-10-08 so the
variance-entry/pos-upload/variance-dashboard screens have something to work with.
The four unclear codes (C/C, C.2.P, LAV/CAK, C.B, DIM) were **not** added — confirm
their real names with Yasir before adding them.

## For the later full bakery-financials build
- `INVONTERY FEB` = bakery's own raw-material inventory (not finished goods) — needed
  for the bakery's own COGS, separate from what it bills branches.
- `PAY ROLL`, `EXPENSES`, `PURCHASE`, `P&L WITH EXP.` = the bakery's own P&L inputs.
- Branch billing ("charges the full amount to branches") would come from the
  per-branch `SALE`/`REC.`/`BAL` columns in `DAILY UPDATE` (e.g. Gulberg's AY/AZ/BA).
