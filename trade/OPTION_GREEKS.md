# Option Greeks — Plain-Terms Study Notes

The "Greeks" each measure **how an option's price reacts to one thing changing** —
the stock, time, volatility, or interest rates. Together they describe the full
risk profile of an option (or an options book).

Related notes: delta hedging & where option P&L comes from (see the delta-hedging
discussion), Natenberg *Option Volatility & Pricing* (in the book collection,
`papers` table), and CFA L1→L2 derivatives readings (BSM, put-call parity, Greeks).

---

## The 5 core Greeks

| Greek | Sensitivity to… | Plain meaning | Order |
|---|---|---|---|
| **Delta (Δ)** | **stock price** | How much the option moves per **$1** move in the stock | 1st |
| **Gamma (Γ)** | **delta itself** | How fast **delta changes** as the stock moves | 2nd |
| **Theta (Θ)** | **time** | How much value the option **loses each day** from time passing | 1st |
| **Vega (ν)** | **volatility** | How much the option moves per **1-pt change in implied volatility** | 1st |
| **Rho (ρ)** | **interest rates** | How much the option moves per **1% change in interest rates** | 1st |

---

## Each one in plain terms

### Delta (Δ) — direction sensitivity
"How many shares the option currently acts like." A call with delta 0.60 gains
~$0.60 when the stock rises $1.
- Calls: 0 → +1. Puts: 0 → −1.
- Deep in-the-money → |delta| near 1 (acts like the stock). At-the-money → ~0.5.
  Far out-of-the-money → near 0.
- **This is the number you hedge with** (delta-neutral = hold enough stock to
  cancel the option's directional exposure).

### Gamma (Γ) — how unstable delta is
Delta doesn't stay put; gamma tells you how quickly it shifts.
- **High gamma = delta moves fast = you must rehedge often.**
- Highest for at-the-money options near expiry.
- It's the "curvature" — the reason **gamma scalping** earns money when the stock
  wiggles (rebalancing forces buy-low / sell-high round trips).

### Theta (Θ) — the daily rent
Options are decaying assets: every day, some time value evaporates even if nothing
else changes.
- **Own options → theta works against you** (you pay rent).
- **Sold options → theta works for you** (you collect rent).
- Decay accelerates as expiration approaches.

### Vega (ν) — volatility sensitivity
How much the option's price moves when **implied volatility** (the market's expected
jumpiness) rises or falls.
- Vega 0.15 → a 1-point rise in implied vol adds ~$0.15 to the option.
- **Option buyers are "long vega"** — they profit if the market gets more
  jumpy/fearful, *regardless of stock direction*.
- (Trivia: "vega" isn't actually a Greek letter; the others are.)

### Rho (ρ) — interest-rate sensitivity
How much the option moves when rates change.
- Usually the *least* important for short-dated options.
- Matters more for long-dated options (LEAPS) and in high-rate environments.

---

## How they fit together (the intuition)

**Delta and Gamma = a speed / acceleration pair:**
- **Delta = your speed** (rate the option tracks the stock).
- **Gamma = your acceleration** (how fast that speed changes).

**Gamma and Theta are opposites — this is the whole options game:**
> Owning options gives **positive gamma** (profit from movement) but **negative
> theta** (pay decay every day). Selling options flips it: **positive theta**
> (collect decay) but **negative gamma** (movement hurts you).

**Vega** is the pure volatility knob: even if the stock never moves, the option's
price shifts when the market's *expectation* of movement changes.

---

## Signs at a glance (long or short each Greek?)

| Position | Delta | Gamma | Theta | Vega |
|---|---|---|---|---|
| **Long call**  | + | + | − | + |
| **Long put**   | − | + | − | + |
| **Short call** | − | − | + | − |
| **Short put**  | + | − | + | − |

The single pattern that ties it together:
- **Anything you buy** → long gamma / long vega, short theta
  (you pay decay to own movement + volatility).
- **Anything you sell** → short gamma / short vega, long theta
  (you collect decay, but movement + rising vol hurt you).

---

## Where option P&L comes from (ties Greeks to profit)

Delta hedging removes *direction*, so profit comes from **realized vs. implied
volatility**:

| You are… | You collect | You pay | You profit when |
|---|---|---|---|
| **Long option + hedge**  | gamma scalping (movement) | theta (decay) | stock moves **more** than priced (realized > implied) |
| **Short option + hedge** | theta (decay) | gamma losses (movement) | stock moves **less** than priced (realized < implied) |

The trade is really: *"the market has mispriced how jumpy this stock will be."*
Buy & hedge if options look too cheap (implied vol too low); sell & hedge if they
look too expensive (implied vol too high).

---

## One-line memory hook
> **Delta** = direction · **Gamma** = how fast direction changes · **Theta** =
> time decay · **Vega** = volatility · **Rho** = interest rates.
