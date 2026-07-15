# CFA Level 1 × IBKR Active Trading — Combined Curriculum

A single study track that pairs **CFA Level 1** theory with **hands-on IBKR paper trading**.
CFA L1's 10 topic areas are the backbone (with approximate exam weights); each is tagged
with the trading practice that makes the theory concrete. Check items off as you go.

**Legend:** 📘 CFA theory · 🔗 trading concept it maps to · 🖥️ IBKR paper practice · ⭐ heavy trading overlap

---

## 1. Ethical & Professional Standards (~15–20%)
- [ ] 📘 Code of Ethics; the seven Standards of Professional Conduct; intro to GIPS
- [ ] 📘 Market manipulation, material nonpublic information, fair dealing
- [ ] 🔗 Discipline, honest record-keeping (Trading Module 8)
- [ ] 🖥️ Keep a truthful trade journal; understand why wash trades / manipulation are prohibited

*Mostly standalone — study on its own; heaviest single weight on the exam.*

## 2. Quantitative Methods (~6–9%) ⭐
- [ ] 📘 Time value of money; rates & returns (holding-period, annualized)
- [ ] 📘 Statistical measures (mean, variance, standard deviation); probability distributions
- [ ] 📘 Probability, expected value; sampling; hypothesis testing (intro); regression (intro)
- [ ] 🔗 Risk-per-trade, position sizing formula, R-multiples, expectancy, win-rate probability (Module 5)
- [ ] 🖥️ Compute expectancy = (win% × avg win) − (loss% × avg loss) from your journal
- [ ] 🖥️ Size every trade with `shares = risk ÷ stop distance`

## 3. Economics (~6–9%)
- [ ] 📘 Supply, demand, elasticity; market structures (competition → monopoly)
- [ ] 📘 Aggregate output, business cycles; monetary & fiscal policy; interest rates; exchange rates
- [ ] 🔗 What moves price and volatility; why spreads widen; the open/close dynamics (Module 1)
- [ ] 🖥️ Observe how SPY behaves around scheduled data (Fed, CPI) — *observe, never predict*

## 4. Financial Statement Analysis (~11–14%)
*Official CFA L1 lessons — the "what to trade" foundation; pairs with your MarketHub fundamentals + scraped filings.*

### 4.1 Introduction to Financial Statement Analysis
- [ ] 📘 The analysis framework; roles of the statements, notes, MD&A, and the audit report
- [ ] 🖥️ Locate each of these sections inside a 10-K you scraped into `finance.db`

### 4.2 Analyzing Income Statements
- [ ] 📘 Revenue recognition; expense recognition; basic vs. diluted EPS; common-size income statement
- [ ] 🖥️ Compute gross / operating / net margins for a tracked company

### 4.3 Analyzing Balance Sheets
- [ ] 📘 Assets, liabilities, equity; measurement bases; common-size balance sheet
- [ ] 🖥️ Pull balance-sheet items and eyeball the capital structure

### 4.4 Analyzing Statements of Cash Flows I
- [ ] 📘 Operating / investing / financing sections; direct vs. indirect method

### 4.5 Analyzing Statements of Cash Flows II
- [ ] 📘 Free cash flow; cash-flow ratios; linking cash flow to earnings quality

### 4.6 Analysis of Inventories
- [ ] 📘 FIFO / LIFO / weighted-average; effect on margins and ratios

### 4.7 Analysis of Long-Term Assets
- [ ] 📘 PP&E, intangibles, goodwill; depreciation, amortization, impairment

### 4.8 Topics in Long-Term Liabilities and Equity
- [ ] 📘 Bonds & leases, pensions (DB vs. DC), deferred items, equity accounts

### 4.9 Analysis of Income Taxes
- [ ] 📘 Deferred tax assets/liabilities; permanent vs. temporary differences; effective vs. statutory rate

### 4.10 Financial Reporting Quality
- [ ] 📘 Quality spectrum; earnings management red flags
- [ ] 🔗 Don't trade on cooked books — a filter before any position

### 4.11 Financial Analysis Techniques
- [ ] 📘 Ratio analysis (activity, liquidity, solvency, profitability, valuation); DuPont decomposition of ROE
- [ ] 🔗 Your P/E, ROE, D/E metrics; screening (Topic 6.5)
- [ ] 🖥️ Rank tracked companies by ratios pulled from `finance.db`

### 4.12 Introduction to Financial Statement Modeling
- [ ] 📘 Building forecasts; sensitivity & scenario analysis
- [ ] 🔗 Feeds forecasting and valuation (6.7 & 6.8)

## 5. Corporate Issuers (~6–9%)
*Official CFA L1 lessons.*

### 5.1 Organizational Forms, Corporate Issuer Features, and Ownership
- [ ] 📘 Sole proprietorship / partnership / corporation; public vs. private; ownership & voting
- [ ] 🔗 What kind of entity you own a share of (ties to 6.4)

### 5.2 Investors and Other Stakeholders
- [ ] 📘 Shareholders vs. debtholders vs. other stakeholders; conflicting interests
- [ ] 🔗 Equity vs. debt claim — why they behave differently

### 5.3 Corporate Governance: Conflicts, Mechanisms, Risks, and Benefits
- [ ] 📘 Principal–agent problems; governance mechanisms; ESG intro
- [ ] 🔗 Governance risk as a reason to avoid a name

### 5.4 Working Capital and Liquidity
- [ ] 📘 Managing current assets/liabilities; liquidity ratios; sources of liquidity
- [ ] 🖥️ Compare current/quick ratios across tracked companies

### 5.5 Capital Investments and Capital Allocation
- [ ] 📘 Capital budgeting; NPV / IRR; the capital-allocation process

### 5.6 Capital Structure
- [ ] 📘 Debt vs. equity mix; cost of capital (WACC); leverage effects
- [ ] 🔗 Leverage concept → connects to margin/buying power (Module 7); beta
- [ ] 🖥️ Compare D/E and beta across your tracked companies

### 5.7 Business Models
- [ ] 📘 How a company creates & captures value; revenue models
- [ ] 🔗 Feeds "Company Analysis: Past and Present" (6.5)

## 6. Equity Investments (~11–14%) ⭐⭐ — *biggest trading overlap*
*Official CFA L1 lessons — trading practice mapped onto each.*

### 6.1 Market Organization and Structure ⭐⭐
- [ ] 📘 Assets & markets; the players (buy-side, sell-side, brokers, exchanges)
- [ ] 📘 Long vs. short positions; leverage, margin, leverage ratio, margin calls
- [ ] 📘 **Order types — market, limit, stop, stop-limit** — and execution instructions
- [ ] 📘 Order-driven vs. quote-driven vs. brokered markets; how orders clear/settle
- [ ] 🔗 *This lesson IS your trading Modules 2–4 & 7* — order types, TIF, routing, margin
- [ ] 🖥️ Read the lesson, then place each order type it names on IBKR the same day

### 6.2 Security Market Indexes
- [ ] 📘 Index construction, weighting methods (price / market-cap / equal), rebalancing
- [ ] 📘 Uses of indexes; types (broad market, sector, style)
- [ ] 🔗 What SPY actually tracks; sector indexes vs. your GICS universe (Module 1)
- [ ] 🖥️ Look at SPY on IBKR and connect its moves to the index it mirrors

### 6.3 Market Efficiency
- [ ] 📘 Efficient Market Hypothesis: weak / semi-strong / strong forms
- [ ] 📘 Market anomalies; intro to behavioral finance
- [ ] 🔗 *Why an edge is hard* — random entries lose to costs (Module 9)
- [ ] 🖥️ Reality-check your paper results against "was that skill or noise?"

### 6.4 Overview of Equity Securities
- [ ] 📘 Common vs. preferred shares; public vs. private equity
- [ ] 📘 Risk & return characteristics of equity; company's cost of equity
- [ ] 🔗 What you're actually buying when you trade a share
- [ ] 🖥️ Note share class / type for the names you trade

### 6.5 Company Analysis: Past and Present
- [ ] 📘 Business model, revenue drivers, historical performance
- [ ] 📘 Reading the financials to understand what a company *has* done
- [ ] 🔗 Ties to FSA (Topic 4) and your MarketHub fundamentals
- [ ] 🖥️ Pull a tracked company's history from `finance.db` + its 10-K you scraped

### 6.6 Industry and Competitive Analysis
- [ ] 📘 Industry classification; Porter's Five Forces; competitive positioning
- [ ] 📘 Industry life cycle; pricing power
- [ ] 🔗 Your `industries.json` GICS sectors are exactly this lens
- [ ] 🖥️ Compare companies within one sector across your data

### 6.7 Company Analysis: Forecasting
- [ ] 📘 Projecting revenue, margins, and earnings; scenario/sensitivity analysis
- [ ] 📘 Building forecast inputs into a valuation
- [ ] 🔗 The forward-looking side (vs. 6.5's backward look)
- [ ] 🖥️ Try a simple revenue/margin forecast for one company you track

### 6.8 Equity Valuation: Concepts and Basic Tools
- [ ] 📘 Dividend discount model (DDM); Gordon growth; free-cash-flow intuition
- [ ] 📘 Multiplier models (P/E, P/B, P/S, EV/EBITDA); enterprise value
- [ ] 🔗 Turns your collected P/E / multiples into a "cheap vs. rich" judgment
- [ ] 🖥️ Compute a rough fair value for a name, compare to its market price on IBKR

## 7. Fixed Income (~11–14%)
- [ ] 📘 Bond features & cash flows; yield measures; price–yield inverse relationship
- [ ] 📘 Interest-rate risk (duration, convexity intro); credit risk; securitization intro
- [ ] 🔗 Interest-rate sensitivity; a second asset class to eventually trade (Module 1 macro)
- [ ] 🖥️ *(Later)* explore a Treasury/bond ETF instrument on IBKR to see how it's quoted

## 8. Derivatives (~5–8%)
- [ ] 📘 Forwards, futures, options, swaps; payoffs and basic pricing; arbitrage intro
- [ ] 🔗 Stop/limit logic extends to option orders; hedging as risk management (Module 6)
- [ ] 🖥️ *(Later)* paper-trade one simple option to see how the derivatives order ticket differs

## 9. Alternative Investments (~7–10%)
*Official CFA L1 lessons — mostly awareness-level; lighter trading tie-in.*

### 9.1 Alternative Investment Features, Methods, and Structures
- [ ] 📘 What makes an asset "alternative"; investment methods (direct, funds, co-invest); structures & fees (e.g. 2-and-20)

### 9.2 Alternative Investment Performance and Returns
- [ ] 📘 Return measures; fee impact; benchmarking & reporting biases
- [ ] 🔗 Fee drag & why reported returns can mislead (ties to Market Efficiency 6.3)

### 9.3 Investments in Private Capital: Equity and Debt
- [ ] 📘 Private equity (buyout, venture) and private debt basics

### 9.4 Real Estate and Infrastructure
- [ ] 📘 Property types; REITs; infrastructure characteristics
- [ ] 🖥️ *(Awareness)* how a REIT/infrastructure ETF is quoted on IBKR

### 9.5 Natural Resources
- [ ] 📘 Commodities, farmland, timberland; roles in a portfolio

### 9.6 Hedge Funds
- [ ] 📘 Strategies (long/short, event-driven, macro, relative value); structure & risks

### 9.7 Introduction to Digital Assets
- [ ] 📘 Distributed ledgers, tokens/crypto; investment forms & risks
- [ ] 🔗 Diversification thinking (Module 5.10)

## 10. Portfolio Management (~8–12%) ⭐⭐ — *big trading overlap*
- [ ] 📘 Portfolio risk & return; risk aversion & utility
- [ ] 📘 Diversification, correlation, covariance; the efficient frontier; CAPM & beta
- [ ] 📘 The portfolio risk-management process; investment policy statement (intro)
- [ ] 🔗 Position sizing, correlation risk, daily loss limit, total risk on the table (Modules 5 & 6)
- [ ] 🖥️ Track your total R at risk across open positions; watch how SPY/MSFT/NVDA move together

---

## How the two tracks fit together
- **Trade to learn:** Topics **6 (Equity)**, **10 (Portfolio Mgmt)**, **2 (Quant)** — placing IBKR paper trades directly teaches the CFA material. Do the reading, then place the matching order.
- **Study to trade:** Topics **4 (FSA)**, **5 (Corporate)**, **7 (Fixed Income)** — the *decision* side (what's worth trading), using data you already collect.
- **Standalone:** Topics **1 (Ethics)**, **3 (Economics)**, **8 (Derivatives)**, **9 (Alts)** — mostly pure study, lighter practice hooks.

**Suggested order:** start Quant (2) + Equity/Market Structure (6) together (they pair with live paper trading),
add Portfolio Mgmt (10), then layer in FSA (4) and the rest. Save Ethics (1) for a dedicated push —
largest single weight, unrelated to trading mechanics.

---

## Trading concept reference (the "Modules" tagged above)

| Module | Covers |
|--------|--------|
| 1 | Reading price: bid/ask, spread, liquidity, slippage, sessions, volatility |
| 2 | Order types: market, limit, stop, stop-limit, trailing, bracket, MOC/LOC, algos |
| 3 | Order params & execution: quantity, TIF (DAY/GTC), routing, status, fills, fees |
| 4 | Linking orders: attached/child, OCA, brackets, conditional orders, presets |
| 5 | Risk & sizing: risk-per-trade, stop distance, position sizing, R-multiples, expectancy, correlation |
| 6 | Managing trades: immediate stops, breakeven, trailing, scaling out, never widen |
| 7 | Broker rules: cash vs margin, settlement, PDT, gap risk, market data |
| 8 | Process & psychology: journal, stats, routine, tilt, paper→live criteria |
| 9 | Building an edge: charts, timeframes, setups, backtesting |
| 10 | IBKR tooling: iPad app, TWS, paper vs live, the API |

## Trade journal template (use every trade)
```
Date | Ticker | In price | Stop | Target | Shares | Risk (1R=$) | Out price | Result (R) | What I learned
```
