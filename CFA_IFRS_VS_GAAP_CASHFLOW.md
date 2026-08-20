# Cash Flow Classification — IFRS vs. US GAAP Cheat Sheet

**Where does each item go** across the three activities — Operating (CFO),
Investing (CFI), Financing (CFF) — and how IFRS and US GAAP differ.

Companion to [`CFA_CASHFLOW_CHEATSHEET.md`](CFA_CASHFLOW_CHEATSHEET.md) (the
accrual↔cash *math*). This file is the *classification*.

---

## 1. The three activities — what belongs in each (both standards agree)

| Activity | Covers | Typical items |
|---|---|---|
| **Operating (CFO)** | day-to-day business | cash from customers; cash to suppliers & employees; other operating expenses |
| **Investing (CFI)** | long-term assets | buy/sell PP&E; buy/sell investments; loans made to others + principal collected; acquisitions |
| **Financing (CFF)** | capital structure (debt & equity) | issue/repurchase stock; issue/repay debt **principal**; dividends paid* |

*\*Dividends paid: financing under US GAAP; operating-or-financing under IFRS (see §2).*

These "clear-cut" items are the **same under both standards**. The differences are
only the five items in §2.

---

## 2. THE difference — the 5 flexible items (heavily tested)

| Item | **US GAAP** (fixed) | **IFRS** (choice) |
|---|---|---|
| **Interest paid** | Operating | Operating **or** Financing |
| **Interest received** | Operating | Operating **or** Investing |
| **Dividends received** | Operating | Operating **or** Investing |
| **Dividends paid** | **Financing** | Operating **or** Financing |
| **Taxes paid** | Operating | Operating (unless specifically identified with I / F) |

---

## 3. The LOGIC (so you don't just memorize)

### US GAAP — "does it hit the income statement?"
- **Yes → Operating.** Interest paid, interest received, dividends received all
  flow through net income → all **Operating**.
- **No → its own section.** Dividends paid do NOT touch the income statement (paid
  from retained earnings) → **Financing**.

> US GAAP rule of thumb: *everything income-statement-related is operating;*
> *only dividends paid escape to financing.*

### IFRS — "what's the nature of the cash flow?" (choose, then stay consistent)
- **Interest & dividends RECEIVED** = returns on investments → Operating **or Investing**
- **Interest & dividends PAID** = cost of obtaining finance → Operating **or Financing**
- **Taxes** = Operating, *unless* the tax can be tied specifically to an investing
  or financing item.

> IFRS theme: **flexibility with consistency** — pick a classification and apply
> it the same way every period (can't flip year to year to flatter CFO).

---

## 4. Memory hooks

- **"Received → could be Investing; Paid → could be Financing"** (the IFRS options).
- **US GAAP = one home each; IFRS = a choice** (except the received/paid pattern).
- **Dividends paid → Financing under BOTH** — US GAAP *requires* it, IFRS *allows*
  it. So classifying dividends paid as financing is always valid.
- **Taxes → Operating** under both (IFRS lets you split out the I/F portion).

---

## 5. Effect of reclassifying between sections

First ask: **is the item an inflow or an outflow?** Then:

> Moving an **outflow OUT** of a section → that section goes **HIGHER**.
> Moving an **outflow INTO** a section → that section goes **LOWER**.
> (Inflows: reverse it.)

**Worked example (Q17):** company reports **interest paid** in **Financing** under
IFRS. Switch to **US GAAP** (interest paid must be **Operating**):
- Interest (an **outflow**) moves Financing → Operating.
- **CFO → LOWER** (gains the outflow)
- **CFF → HIGHER** (sheds the outflow)
- **CFI → unchanged**

Numeric feel (interest paid = 10; start CFO 100, CFF −50):
```
IFRS:     CFO = 100      CFF = −50
US GAAP:  CFO = 90       CFF = −40     (lower CFO, higher CFF)
```

---

## 6. Quick-reference grid (fill-in-the-blank drill)

| Item | Inflow/Outflow | US GAAP | IFRS options |
|---|---|---|---|
| Cash from customers | in | CFO | CFO |
| Cash to suppliers/employees | out | CFO | CFO |
| Buy/sell PP&E or investments | either | CFI | CFI |
| Issue/repay debt principal | either | CFF | CFF |
| Issue/buy back stock | either | CFF | CFF |
| **Interest paid** | out | **CFO** | CFO / **CFF** |
| **Interest received** | in | **CFO** | CFO / **CFI** |
| **Dividends received** | in | **CFO** | CFO / **CFI** |
| **Dividends paid** | out | **CFF** | CFO / **CFF** |
| **Taxes paid** | out | **CFO** | CFO (split I/F if identifiable) |

---

## One-line summary
> The three sections agree on the obvious items. The exam lives in **5 flexible
> items**. **US GAAP:** income-statement items → Operating; dividends paid → Financing.
> **IFRS:** received → could be Investing, paid → could be Financing, choose and stay
> consistent. To gauge a reclassification's effect, track **inflow vs. outflow** and
> which section **gains or loses** it.
