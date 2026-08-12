# Option Volatility — Explained From Zero

A plain-English primer for someone who has **never** traded an option. No math
degree needed. Read it top to bottom once; it builds on itself.

Every concept follows the same shape (same as `IBKR_TRADER_TRAINING.md`):

> **What it is (plain)** → **The logic / why** → **Example** → **Common mistake**

### 🎓 CFA overlap badge
Concepts marked **🎓 Also in CFA L1** are also tested on the CFA Level 1
**Derivatives** topic — study once, count twice.

---

## Part 0 — The 60-second option refresher

You can't talk about option *volatility* until "option" means something, so:

- **An option is a contract** that gives you the *right, but not the obligation,*
  to buy or sell a stock at a fixed price ("**strike**") before a fixed date
  ("**expiration**").
- A **call** = the right to **buy** at the strike (you want the stock to go **up**).
- A **put** = the right to **sell** at the strike (you want the stock to go **down**).
- You pay a small price up front — the **premium** — to own that right. That
  premium is the whole game. **Everything below is about what makes the premium
  expensive or cheap.**

> **Plain analogy:** an option is like paying a small, non-refundable deposit to
> lock in a price. If the price moves your way, the deposit was a bargain. If it
> doesn't, you just lose the deposit — never more.

---

## Part 1 — What "volatility" actually means

### 1.1 Volatility = how much a stock swings
- **What it is:** Volatility measures how *jumpy* a stock's price is — big daily
  moves = high volatility; sleepy, slow drift = low volatility. It says nothing
  about **direction**, only **size** of the swings.
- **The logic / why:** Direction is a coin flip; *size of the swing* is
  measurable and surprisingly persistent (calm weeks cluster; wild weeks cluster).
- **Example:** A utility stock that moves ±0.5% a day is low-vol. A biotech that
  moves ±6% a day is high-vol — same dollar price, totally different personality.
- **How it's quoted:** as an **annualized percentage**. "30% volatility" means
  the market expects the stock to stay within roughly ±30% over a year (about two
  times out of three). Higher number = wider expected swing.
- **Common mistake:** thinking "high volatility = going down." No — it just means
  *big moves either way*.

### 1.2 The two flavours: Historical vs. Implied  🎓
> **🎓 Also in CFA L1 — Derivatives** (option value = intrinsic + time value)

This is the single most important distinction in the whole document.

| | **Historical (a.k.a. Realized) Volatility** | **Implied Volatility (IV)** |
|---|---|---|
| Looks | **Backward** — what the stock *actually did* | **Forward** — what the market *thinks it will do* |
| Source | Measured from past prices | Backed out of the option's *current price* |
| Think of it as | The weather report for last month | Tomorrow's forecast |

- **What Implied Volatility is:** the market's **forecast of future swinginess**,
  reverse-engineered from what people are *willing to pay* for the option right now.
- **The logic / why it exists:** an option's price is set by supply and demand. If
  traders expect a wild ride, they bid options up. You can run that price
  *backwards* through the pricing formula to ask: "what level of future volatility
  would justify this price?" That answer **is** the implied volatility.
- **Example:** If puts and calls on a stock suddenly get expensive before an FDA
  decision, IV spikes — the market is *implying* a big move is coming, even though
  nothing has happened *yet*.
- **Common mistake:** treating IV as a fact. It's an **opinion the market is
  pricing in** — it can be too high or too low, and that's exactly where trading
  edges come from.

---

## Part 2 — Why volatility is *the* driver of an option's price

### 2.1 More swing = more valuable option
- **What it is:** Hold the stock price, strike, and time fixed, and just crank up
  volatility — the option gets **more expensive**. Always. For both calls and puts.
- **The logic / why:** An option has a **floor of zero** — the most you can lose is
  the premium. But the upside is open. More volatility means a fatter chance of a
  *big* favourable move, while the downside stays capped at "expires worthless."
  You're paying for the size of the lottery, and the losing tickets all cost the
  same (nothing extra).
- **Example:** Two stocks both at \$100, same \$100 strike, same 1 month left. The
  sleepy one might have a \$1 call; the jumpy one a \$4 call. Same starting price —
  the extra \$3 is *purely* the volatility.
- **Common mistake:** shopping for options by price alone. A "cheap" \$0.50 option
  on a dead stock and an "expensive" \$5 option on a wild one can be *equally* fair —
  the price difference is mostly volatility, not a bargain.

### 2.2 Time value and "vol" are the two things you're really buying
- **Intrinsic value** = the part that's already in-the-money (a \$100 call with the
  stock at \$105 has \$5 of intrinsic value — real, guaranteed-if-exercised-now worth).
- **Time value** = everything *above* intrinsic — the "maybe it moves more" part.
  **Volatility is the fuel of time value.** High IV → fat time value → pricey option.
- **Common mistake:** buying a high-IV option, being *right* about direction, and
  still losing money because you overpaid for time value that then deflated (next section).

---

## Part 3 — The Greek you must know: Vega

### 3.1 Vega = how much the option price moves when volatility moves
- **What it is:** **Vega** tells you how many dollars the option's price changes for
  each **1 percentage point** change in implied volatility. (The other "Greeks" —
  delta, theta, gamma — measure sensitivity to price, time, etc. Vega is the
  *volatility* one.)
- **The logic / why:** It turns the abstract idea "IV went up" into a concrete
  dollar impact on *your* position.
- **Example:** Vega of 0.10 means: IV rises from 30% → 31%, your option gains ~\$0.10
  (×100 shares per contract = ~\$10). If IV *falls* a point, you lose that.
- **Rule of thumb:** longer-dated and at-the-money options have the **most** vega
  (most exposure to volatility); near-expiry, far-out-of-the-money options have little.
- **Common mistake:** ignoring vega and being blindsided when the *stock barely
  moved* but your option lost value anyway — because IV dropped.

---

## Part 4 — The trap every beginner hits: IV Crush

### 4.1 IV crush around earnings
- **What it is:** Before a scheduled event (earnings, FDA ruling, big product
  launch), implied volatility **inflates** because a big move is *possible*. The
  instant the news is out, uncertainty vanishes and IV **collapses** — often
  violently. That collapse is "**IV crush**."
- **The logic / why:** IV prices in *unknown* outcomes. Once the outcome is known,
  there's nothing left to be uncertain about, so the volatility premium evaporates —
  regardless of which way the stock went.
- **Example:** You buy a call the day before earnings at 80% IV. The company beats,
  stock pops +3%... but IV crushes from 80% → 35%, and your call *loses* money. You
  were **right on direction and still lost** — the vega loss outweighed the gain.
- **Common mistake:** "I'll buy options right before earnings because a big move is
  coming." The big move is already *priced in* by the inflated IV. You need a move
  *bigger than the market expects* just to break even.

---

## Part 5 — Is volatility cheap or expensive *right now*?

You can't judge an IV number in a vacuum. 40% IV is high for a utility, low for a
meme stock. You compare it to **its own history**.

### 5.1 IV Rank and IV Percentile
- **What it is:** Both tools place today's IV against the **past year** of that
  stock's IV.
  - **IV Rank** = where today sits between the year's low and high (0 = yearly low,
    100 = yearly high).
  - **IV Percentile** = the % of days in the past year that IV was *lower* than today.
- **The logic / why:** It answers the only question that matters for timing:
  "**Is option premium expensive or cheap for this name right now?**"
- **The core trading heuristic this unlocks:**
  - **High IV rank (premium is expensive)** → favour **selling** options (you collect
    the fat premium and benefit when IV falls back).
  - **Low IV rank (premium is cheap)** → favour **buying** options (you pay little
    and benefit if IV rises).
- **Common mistake:** confusing IV Rank with IV Percentile — Rank only cares about
  the high/low endpoints; Percentile counts every day. In a year with one crazy
  spike, they can disagree a lot.

### 5.2 Volatility mean-reverts (the reason the heuristic works)
- **What it is:** Volatility tends to **spring back toward its average** — spikes fade,
  dead-calm periods eventually wake up. It doesn't trend forever the way prices can.
- **The logic / why:** Fear and panic are temporary; markets calm down. This
  "rubber-band" behaviour is *far* more reliable than trying to predict price direction.
- **Common mistake:** assuming a high-vol stock will *stay* high-vol. Usually it's
  reverting — which is precisely why selling into high IV has an edge.

---

## Part 6 — Skew, smile, and the VIX (good to recognise)

### 6.1 The volatility smile / skew
- **What it is:** Options at *different strikes* on the same stock trade at
  *different* IVs. Plot them and you get a "smile" (or, for stocks, a lopsided
  "**skew**" — downside puts carry higher IV than upside calls).
- **The logic / why:** Crashes happen faster and scarier than rallies, so investors
  pay up for downside **put** protection. That extra demand lifts put IV — a
  permanent "insurance premium" baked into the market.
- **Common mistake:** assuming one IV number describes the whole stock. It varies by
  strike and by expiration (the "vol surface").

### 6.2 The VIX — the market's "fear gauge"  🎓
> **🎓 Also in CFA L1 — Derivatives / Equity market context**
- **What it is:** The **VIX** is the implied volatility of the *whole S&P 500*,
  packaged into one number — roughly the market's expected 30-day swing, annualised.
- **The logic / why:** It's a single dial for overall market fear. Calm markets:
  VIX ~12–15. Nervous: 20s. Panic/crash: 30, 50, 80+.
- **Example:** VIX at 15 = complacent, cheap index options. VIX at 40 = fear,
  expensive options, often near market bottoms.
- **Common mistake:** calling VIX a *prediction of direction*. It's a size-of-move
  gauge; a high VIX means "big moves expected," not "market will fall" (though the
  two often coincide).

---

## Part 7 — The whole thing in seven sentences

1. **Volatility = how big a stock's swings are**, quoted as an annual %, direction-agnostic.
2. **Historical vol looks back; implied vol (IV) looks forward** and is baked into the option's price.
3. **Higher volatility = more expensive options**, because upside is open and downside is capped at the premium.
4. **Vega** tells you how many dollars you gain/lose per 1-point change in IV.
5. **IV crush** — IV inflates before known events and collapses after — is how beginners lose money *while being right on direction*.
6. **IV Rank/Percentile** tells you if premium is cheap (lean toward **buying**) or expensive (lean toward **selling**); **volatility mean-reverts**, which is why this works.
7. **Skew** = downside puts cost more (crash insurance); the **VIX** is this same idea for the entire market — the fear gauge.

---

## Part 8 — First practice steps (paper only)

Aligns with the `IBKR_TRADER_TRAINING.md` paper-account discipline — **no real
money** while learning options.

1. Pick one liquid name you already watch (e.g. SPY or MSFT). Find its option chain
   on the platform and just **read** the IVs across strikes — see the skew live.
2. Note the **IV Rank** if the platform shows it. Ask: cheap or expensive today?
3. Watch **one** stock through an **earnings** date *without trading* — record IV the
   day before and the day after. Feel the crush before you ever risk a cent on it.
4. Only after those observations, paper-trade **one** single option and track how its
   price moves vs. the stock's move — you'll *see* delta, theta, and vega at work.

> **Golden rule:** if you don't know whether you're buying *cheap* or *expensive*
> volatility, you don't yet know the most important thing about the trade.
