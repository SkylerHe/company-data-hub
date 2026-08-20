# Cash Flow Statement — Accrual ↔ Cash Cheat Sheet

Everything for converting **accrual figures ↔ actual cash**, for both the
**indirect** and **direct** methods. Built from worked practice questions.

> **Both methods give the SAME operating cash flow (CFO).** They differ only in
> *how you build the operating section*. Investing (CFI) and financing (CFF) are
> identical either way.

---

## 0. The ONE tool behind every formula: the T-account roll-forward

Every conversion below is just this equation, solved for the missing piece:

```
Beginning balance + increases − decreases = Ending balance
```

Draw the account's T, fill in what you know, solve for the unknown. You never
have to memorize the individual formulas — you can rebuild any of them.

Example (interest payable, a liability): expense flows IN, cash paid flows OUT
```
Beginning payable + Interest expense − Cash paid = Ending payable
```

---

## 1. Which method is the question using?

| You're given… | Method |
|---|---|
| **Net income** + depreciation + working-capital changes | **Indirect** |
| **Revenue, COGS, cash payments** (salaries/interest/taxes) | **Direct** |
| Only **Retained earnings** (no net income) | Derive NI first (see §5), then indirect |

---

## 2. INDIRECT method — start at net income, adjust to CFO

```
  Net income                         (from income statement)
+ Non-cash charges                   depreciation, amortization, impairments
± Non-operating gains / losses       − gains,  + losses
± Changes in working capital         (see sign rules below)
─────────────────────────────────
= Cash flow from operations (CFO)
```

### Sign rules (memorize these two lines)
- **ASSET  ↑ → subtract**   ·   ASSET ↓ → add
- **LIABILITY ↑ → add**     ·   LIABILITY ↓ → subtract

| Item | Change | Adjustment | Why |
|---|---|---|---|
| Accounts receivable ↑ | asset up | **subtract** | sold but not yet collected |
| Inventory ↓ | asset down | **add** | sold stock, didn't restock → freed cash |
| Accounts payable ↑ | liability up | **add** | expense recorded, not yet paid → kept cash |
| Accounts payable ↓ | liability down | **subtract** | paid off suppliers → cash out |
| Depreciation | non-cash | **add** | reduced NI but no cash left |
| **Gain** on asset sale | non-operating | **subtract** | cash is in *investing* |
| **Loss** on debt retirement | non-operating | **add** | cash is in *financing* |

**Gains vs losses memory hook:** *Gains → minus, Losses → plus.* (Reverse them
out of operating; their real cash lives in investing/financing.)

**"Addition" ≠ "cash in."** An addition is just a *reversal* — removing something
that shouldn't sit in operating.

---

## 3. DIRECT method — add up actual cash in and out

```
  Cash collected from customers
− Cash paid to suppliers
− Cash paid for operating expenses (salaries, etc.)
− Cash paid for interest
− Cash paid for taxes
─────────────────────────────────
= Cash flow from operations (CFO)
```

No net income needed. Convert each accrual figure to cash:

### Cash collected from customers
```
Cash from customers = Revenue − increase in AR
                   (= Revenue + decrease in AR)
```
AR ↑ = sales not yet collected → collected LESS than revenue.

### Cash paid to suppliers  (two steps)
```
Purchases         = COGS + increase in inventory
Cash to suppliers = Purchases − increase in AP
                 (= COGS + Δinventory + decrease in AP)
```
Inventory ↑ = bought more than sold → cash out.
AP ↓ = paid suppliers down → cash out.

### Cash paid for an expense (interest, taxes, wages)
```
Cash paid = Expense − increase in related payable
         (= Expense + decrease in payable)
```

---

## 4. Accrual ↔ Cash — BOTH directions (same T-account, rearranged)

The exam runs these forward AND backward. Payable = a liability.

| Direction | Formula |
|---|---|
| **expense → cash paid** | Cash paid = Expense **−** increase in payable (**+** decrease) |
| **cash paid → expense** | Expense = Cash paid **+** increase in payable (**−** decrease) |

**Universal payable logic:**
- **Payable ↑ → kept cash** → paid LESS than expense
- **Payable ↓ → spent cash** → paid MORE than expense

Applies to interest payable, taxes payable, wages payable, accounts payable —
same bucket, different label.

### ⚠️ Tax-only wrinkle: deferred taxes
Full income tax expense = *current* tax + *deferred* tax. If a question also gives
a **deferred tax liability/asset** change, fold it in like a payable:
```
Cash taxes paid ≈ Tax expense − ↑taxes payable − ↑deferred tax liability + ↑deferred tax asset
```
For basic questions (only "taxes payable" given), ignore this.

---

## 5. When net income ISN'T given — derive it from retained earnings

```
Ending RE = Beginning RE + Net income − Dividends
→ Net income = Ending RE − Beginning RE + Dividends
```
Then feed that net income into the indirect method (§2).
Dividends are a **financing** outflow — they never enter CFO directly.

---

## 6. IFRS vs. US GAAP (cash flow)

### Format
- Both allow **direct or indirect**; both prefer direct; most use indirect.
- **US GAAP:** using the direct method → must ALSO show the indirect reconciliation.
- **IFRS:** no such reconciliation required.

### Classification (the heavily-tested part)
| Item | US GAAP (fixed) | IFRS (flexible) |
|---|---|---|
| Interest paid | Operating | Operating **or** Financing |
| Interest received | Operating | Operating **or** Investing |
| Dividends received | Operating | Operating **or** Investing |
| Dividends paid | Financing | Operating **or** Financing |
| Taxes paid | Operating | Operating (unless tied to I/F) |

IFRS = choose, but apply **consistently**. US GAAP = one fixed home.

**Effect of reclassifying (track inflow vs outflow!):**
Moving an **outflow** OUT of a section makes that section **higher**; INTO a
section makes it **lower**. E.g. IFRS interest-paid in financing → switch to US
GAAP (operating): CFO **lower**, CFF **higher**, CFI unchanged.

---

## 7. Worked examples (from practice)

**Indirect, derive NI first (Q3):** RE 120→145, dividends 10, deprec 25,
AR 38→43, Inv 45→48, AP 36→29.
```
NI = 145 − 120 + 10 = 35
CFO = 35 + 25 − 5 − 3 − 7 = 45
```

**Direct (Q5):** Rev 37, COGS 16, Inv 36→40, AR 22→19, AP 14→12; cash salaries 6,
interest 2, taxes 4.
```
Cash from customers = 37 + 3 = 40
Cash to suppliers   = 16 + 4 + 2 = 22
CFO = 40 − 22 − 6 − 2 − 4 = 6
```

**expense → cash paid (Q10):** interest exp 19, int payable ↑3; tax exp 6, tax payable ↓4.
```
Interest paid = 19 − 3 = 16
Taxes paid    = 6 + 4 = 10
```

**cash paid → expense (Q15):** cash paid interest 103.3, int payable 90.4→84.5.
```
Interest expense = 103.3 + (84.5 − 90.4) = 97.4
```

---

## One-line summary
> Draw the **T-account** (`Beginning + in − out = Ending`) and solve for the
> unknown. **Indirect** = net income + adjustments (assets ↑ subtract, liabilities
> ↑ add, gains subtract, losses add). **Direct** = cash in − cash out (convert
> revenue/COGS/expenses using the related receivable/payable). Both land on the
> same CFO.
