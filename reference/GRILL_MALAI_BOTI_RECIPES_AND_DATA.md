# FNK Grill (Malai Boti section) — source data captured from owner

Captured 2026-10-22 from two inputs the owner sent: a chat message with three spice
recipes, and an uploaded Excel workbook `MALAI_BOTI_FILE_01-SEP_-2026.xlsx` — the
section's own manual Excel "mini-accounting system" (P&L, Expense, Purchase, Issue,
Inventory, Payroll, inter-store, and a handwritten recipe-costing sheet). This is
research/reference material for the still-pending "set up audit & accounting for FNK
Grill" build — nothing below has been entered into the app or database yet.

## Recipes given directly by the owner (chat message, verbatim quantities)

**Malai Boti Blend — dry spice mix, output basis "1 pkt":**
- Black pepper 315g
- White pepper 125g
- Chicken powder 75g
- Salt 265g
- Garlic powder 165g
(Total dry mix ≈ 945g per packet)

**Malai Wings spice — recipe for 12 kg raw wings (sourced from Ahmed sb):**
- Black pepper 120g
- Salt 110g
- Zeera powder 25g
- Dhania powder 15g
- White pepper 50g
- Garam masala 50g
- Chicken powder 15g

**"On Spot Spice" — wet finishing/marinade mix, batch basis not yet given:**
- Coconut 50g
- Vinegar 15g
- Nestle cream 6 pkt
- Mint 2 gutti
- Coriander 50g
- Green chilli 50g
- Fresh garlic 100g

Open questions on these three (still unanswered):
1. Malai Boti Blend is dry spices only (no cream/yogurt) — is "On Spot Spice" the wet
   component added together with it to marinate the chicken, or a separate
   finishing/basting step done at a different point? Does it apply to Malai Boti only,
   or Wings too?
2. What's the batch/output basis for "On Spot Spice" (per kg raw chicken? per batch of
   wings?) and the unit size of "1 pkt" Nestle cream and "1 gutti" mint (so usage can be
   tracked against purchased inventory)?
3. How does "Malai Boti Blend (1 pkt)" relate to the Excel file's own "MALAI BLEND" item
   (code 1.2.01, rate 1700/PKT) and its recipe below (4 pkt blend per 100kg chicken) —
   same thing, i.e. is "1 pkt" from the chat message the same packet as 1.2.01?

## Item master (from ISSUE sheet — the section's full coded item list)

Numbered like a mini chart of items, one block per category:

- **1.1.xx — Fresh/finished chicken**: 1.1.01 THAI (KG, 961.1), 1.1.02 CHEST (KG, 959.2),
  1.1.03 MALAI BOTI (KG, 1550 — finished good), 1.1.04 STEAK FILLET (PCS, 200),
  1.1.05 BEHARI CHICKEN (PCS, 1150)
- **1.2.xx — Spices** (19 items): 1.2.01 MALAI BLEND (PKT, 1700), 1.2.02 BEHARI BLEND
  (PKT, 1600), 1.2.03 PAPRIKA POWDER (PKT, 1600), 1.2.04 GARAM MASALA (KG, 2600),
  1.2.05 CHICKEN POWDER 12KG (KG, 1333), 1.2.06 TANDOORI MASALA (PKT, 1550),
  1.2.07 ACHAR GOAST (PKT, 1500), 1.2.08 WHITE ZEERA (KG, 880), 1.2.09 TIKKA MASALA
  (PCS, 1550), 1.2.10 MURGI MASALA (KG, 1550), 1.2.11 GARLIC POWDER (PKT, 800),
  1.2.12 CRUSHED CHILLI (PKT, 750), 1.2.13 CORIANDER POWDER (PKT, 550),
  1.2.14 COCONUT POWDER 300GM SANTAN (PKT, 550), 1.2.15 CUMERIC POWDER (KG, 360),
  1.2.16 BLACK PEPPER (KG, rate blank), 1.2.17 WHITE PEPPER (KG, rate blank),
  1.2.18 RED PEPPER (KG, 700), 1.2.19 ZEERA POWDER (KG, 2000)
- **1.3.xx — Sauces/condiments** (14 items): WARDA MAYO (POUCH, 2513), BBQ SAUCE
  (BOTT, 1400), NANDOS PERI PERI (BOTT, 1150), MUSTARD PASTE/GALLON (BOTT, 5500),
  HOT SAUCE (BOTT, 600), CHILI SAUCE 4.5L (BOTT, 1150), WORCESTERSHIRE 5L (BOTT, 1500),
  VINEGAR 4.5L (BOTT, 650), GINGER POWDER (KG, 700), FOOD COLOUR (PKT, 60), FRESH LIME
  (BOT, 190), CHILLI GARLIC SAUCE 4.5L (BOTT, 1350), COCONUT POWDER 50GM SANTAN
  (PKT, 150), TOMATO KETCHUP 4.5L (BOTT, 1350)
- **1.4.xx — Oil/milk/cream** (9 items): MILK PACK CREAM (PKT, 996), OLPER MILK 1.5L
  (221), DAY FRESH MILK 1L (0), FRESH CREAM 1L (LTR, 1080), FRESH CREAM 200ML (223.55),
  HABIB OIL 4.5L (2900), SUFI 5L (2178), SUFI 3L (1685), KISAN OIL 1L (580)
- **1.5.xx — Cleaning material** (22 items, e.g. dish wash soap, phenyle, gloves,
  grill brush @113/pcs, harpic, etc.)
- **1.6.xx — Packing material** (7 items incl. MALAI BOTI PACKING KG@540, MRD STICKERS,
  zipper bag, garbage liner)
- **1.7.xx — Crockery/equipment** (8 items: weight scale, knife, spatula, fries machine,
  tong, scoop, etc.)
- **1.8.xx — Office/stationery** (6 items incl. LPG CYLINDER @17706 and a line literally
  called RENT @800 — worth checking whether rent is really meant to post as a Grill
  operating expense or is a misfiled placeholder)

## Vendors (AMOUNT UPDATE sheet — payable ledger)

AR CHIKES (raw chicken — THAI & CHEST cuts, ~Rs 738–749/kg in Sept), AHMAD FOOD
(sauces/mayo — e.g. WARDA MAYO), NESTLE (fresh cream), FNK SPICE, ARIB SPICE,
GMSA LPG (gas cylinders), LOCAL MARKET (small/ad-hoc items), HAFIZ MAHMOD, METRO,
SHERI CHEMICAL (cleaning supplies — same "SHERI" family as the existing rate-variable
vendor SHERI VEGGIE in the main system), AZIZ TRADER, PUNJAB DRY FRUIT, plus **C-3,
C-4, C-5, C-6 and BAKERY** carried as inter-store counterparties on the same ledger.

**AR CHIKES is confirmed as the raw-chicken vendor** — answers one of the open
questions from the earlier Grill design discussion.

## Employees (PAY ROLL sheet, department "MALAI BOTI")

| Name | Role | Monthly salary | Hours/day |
|---|---|---|---|
| AHMAD SB | P.Manager | 100,000 | 9 |
| IMTIYAZ | Helper | 43,000 | 9 |
| ZOHAIB | Helper | 35,000 | 9 |

Note: the owner's original message described "2 employees who buy, process and
prepare" — this payroll sheet shows 3 (a manager plus 2 helpers). Worth confirming
whether Ahmad Sb is dedicated to this section or a shared/supervisory role.

## Recipes with real yields — from the Excel's own handwritten costing sheet (C-1 tab)

This is the most valuable find: the owner's team is already manually computing a
raw-to-finished yield check, almost exactly the shrinkage audit the Grill project asked
for.

**Cost of Malai Chicken — batch basis 100 kg raw chicken ("Cock Chicken"):**
| Ingredient | Unit | Price | Qty used | Line total |
|---|---|---|---|---|
| Chicken | KG | 769 | 100.0 | 76,900 |
| Blend (Malai Blend, 1.2.01) | PKT | 1700 | 4.0 | 6,800 |
| Cream | PCS | 224 | 48.0 | 10,752 |
| Coconut | PKT | 550 | 2.3 | 1,265 |
| Vinegar | LTR | 175 | 1.5 | 262.5 |
| **Total cost for 100kg batch** | | | | **95,979.5** |

Yield: **100 kg raw chicken → 79 kg finished Malai Boti** ("ADD 79-KG" / "21-KG
YIELD" loss), giving a cost of 95,979.5 ÷ 79 ≈ **PKR 1,214.93 per kg finished** (matches
the sheet's own "ONE KG COST" figure exactly). **That means the real historical
shrinkage/yield here is ~21%**, not a guess — this should replace the "propose a
benchmark" placeholder from the earlier design discussion.

One open question on this: a "SALE 14000" figure sits right next to the "21-KG YIELD"
line — is that 21kg of trim/loss partly sold off separately (bone, fat, off-cuts) for
Rs 14,000, rather than being pure waste? That changes how the shrinkage tolerance
should be defined (loss net of a recoverable byproduct, vs. gross loss).

Also on this sheet: a per-kg cream ratio is spelled out directly — **"per kg chicken,
use 0.48 pcs cream pack"** (48 pcs ÷ 100 kg), consistent with the batch table above.

**Cost of Peri Peri Sauce — batch basis 20 packets:**
| Ingredient | Unit | Price | Qty | Line total |
|---|---|---|---|---|
| Achar Goast | KG | 1560 | 3.0 | 4,680 |
| Black pepper | GRM | 2.06 | 200 | 412 |
| Garlic powder | GRM | 1.25 | 200 | 250 |
| **Total for 20 pkt** | | | | **5,342** (→ 267.1/pkt) |

**Cost of Donner Sauce — batch basis 4.75 kg (4750g):**
| Ingredient | Pack size | Price/g | Qty (g) | Line total |
|---|---|---|---|---|
| Mayo | 4kg pack | — | 1 pack | 628.25 |
| Ketchup | 350g pack | 0.355 | 87.5 | 31.06 |
| Hot sauce | 90g pack | 1.33 | 22.5 | 29.93 |
| BBQ sauce | 100g pack | 2.843 | 25.0 | 71.08 |
| Peri sauce | 100g pack | — (0, internal transfer, cost TBD) | 25.0 | 0 |
| Sriracha sauce | 40g pack | 1.111 | 10.0 | 11.11 |
| Mustard sauce | 70g pack | 1.833 | 17.5 | 32.08 |
| **Total (4.75kg batch)** | | | | **803.51** (ingredients priced; Peri Sauce component not yet costed) |

Still no recipe given for: Steak Fillet, Steak Sauce, Zinger Sauce, Behari Chicken/
Behari Blend, Tandoori/Achar Goast/Murgi/Tikka marinades (items exist in the catalog
with rates, but no BOM yet).

## A live finding already visible in this data — cream usage doesn't reconcile

On the same C-1 sheet, a second small table cross-checks cream packet usage for the
month: **theoretical use** (chicken processed × 0.48 ratio) = 512.016 pcs, but
**Imtiyaz's reported actual use** = 564 pcs — a difference of **~52 packets
(≈ PKR 11,645 at Rs 224/pcs)** unaccounted for by the chicken-processing ratio. This
is exactly the kind of variance the planned shrinkage/theft audit is meant to catch,
and it's sitting unresolved in their own current month's figures. Flagging it now
rather than waiting for the full system to be built.

## Distribution network — broader than originally described

The owner's original request said finished product "goes to 4 branches in
Faisalabad." The SALE sheet in this workbook tells a fuller story: it tracks daily
sales, by the same 7 products (M.B/B.C/S.F/P.S/S.S/D.S/B.S — Malai Boti, Behari
Chicken, Steak Fillet, Peri [Peri] Sauce, Steak Sauce, Donner Sauce, Behari/Zinger
Sauce), **separately for 5 named points: KOHINOOR, SUSAN ROAD, GULBERG (=C-5 in the
main system), GREEN AVENUE, and a generic "LAHORE" column** — plus a BILL sheet
example billing **BAGHBAN PURA** (C-7). A daily cash-summary section further right
has separate "FSD BRANCH HOLD CASH" (Faisalabad) and "LHR HOLD CASH" (Lahore)
columns, confirming Faisalabad branches exist too, just not broken out by product in
this sheet the way the Lahore ones are.

Also notable: **"FNK GRILL" already exists as a vendor in the main system**, and
C-5 already orders Grill's finished goods through `fast-track-demand.html` → Goods
Receipt → `purchases`. That may already be how the Lahore side of this gets captured
on the buying branches' books — worth checking whether this Excel "SALE" ledger is
Grill's own mirror of those same transactions (from the seller's side) before
building a second, separate tracking mechanism for Lahore.

## Expense categories actually in use at Grill (EXPENSE sheet, Sept totals)

FOOD 1,331,990 (chicken/food bills paid — separate from the itemized PURCHASE sheet,
same cash-vs-inventory split the main app already has via expenses vs. purchases),
DIRECTOR 250,000 (owner draw), PAYROLL 162,616, UTILITIES 73,321, CLEANING 23,010,
EMPLOYEE MEAL 18,900, M&R 6,940, Distribution Cost 1,000 — all map cleanly onto
categories that already exist in the main system's `expense_categories` table.
