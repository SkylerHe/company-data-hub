#!/usr/bin/env python3
"""options_lab.py — a hands-on options/volatility learning tool (Phase-1 of vol study).

Makes the 5 core concepts tangible on live SPY data (free, via yfinance):
  1. Implied volatility (IV) — what the option market prices in.
  2. Realized volatility (RV) — how much SPY actually moved.
  3. The volatility risk premium — IV usually > RV (you're paid to sell insurance).
  4. The Greeks — delta / gamma / vega / theta, computed from Black-Scholes (from scratch).
  5. Skew — IV is higher for OTM puts than OTM calls (crash fear).

Standalone: math + numpy + pandas + yfinance (no scipy — normal CDF via math.erf).
Run: source venv/bin/activate && python trade/options_lab.py
"""
import math
import datetime as dt
import numpy as np
import yfinance as yf

TICKER = "SPY"
R = 0.043                       # risk-free rate (~current T-bill)


# ---- Black-Scholes + Greeks, coded from scratch (this IS the learning) ----
def _N(x):   return 0.5 * (1 + math.erf(x / math.sqrt(2)))      # normal CDF
def _n(x):   return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)  # normal PDF


def bs(S, K, T, r, sigma, call=True):
    """Black-Scholes price + Greeks. vega per 1% vol; theta per calendar day."""
    if T <= 0 or sigma <= 0:
        return None
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if call:
        price = S * _N(d1) - K * math.exp(-r * T) * _N(d2)
        delta = _N(d1)
        theta = (-S * _n(d1) * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * _N(d2)) / 365
    else:
        price = K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)
        delta = _N(d1) - 1
        theta = (-S * _n(d1) * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * _N(-d2)) / 365
    gamma = _n(d1) / (S * sigma * math.sqrt(T))
    vega = S * _n(d1) * math.sqrt(T) / 100
    return dict(price=price, delta=delta, gamma=gamma, vega=vega, theta=theta)


def iv_at(df, target):
    """Implied vol of the option whose strike is nearest `target`."""
    row = df.iloc[(df["strike"] - target).abs().argsort().iloc[0]]
    return float(row["strike"]), float(row["impliedVolatility"])


def main():
    tk = yf.Ticker(TICKER)
    hist = tk.history(period="6mo")["Close"]
    S = float(hist.iloc[-1])
    rets = hist.pct_change().dropna()
    rv20 = rets.tail(20).std() * np.sqrt(252)
    rv60 = rets.tail(60).std() * np.sqrt(252)

    # pick an expiry ~35 days out (near-term, liquid)
    today = dt.date.today()
    exp = min(tk.options, key=lambda e: abs((dt.date.fromisoformat(e) - today).days - 35))
    days = (dt.date.fromisoformat(exp) - today).days
    T = days / 365
    chain = tk.option_chain(exp)
    calls, puts = chain.calls, chain.puts

    print(f"\n{'='*66}\n{TICKER} options lab   ·   spot ${S:.2f}   ·   expiry {exp} ({days}d)\n{'='*66}")

    # --- 1&2&3: IV vs RV, the volatility risk premium ---
    atm_k, atm_iv = iv_at(calls, S)
    print("\n[1-3] IMPLIED vs REALIZED volatility (the risk premium)")
    print(f"  ATM implied vol (IV)      : {atm_iv:6.1%}   (option market's forecast)")
    print(f"  Realized vol, last 20d    : {rv20:6.1%}   (what SPY actually did)")
    print(f"  Realized vol, last 60d    : {rv60:6.1%}")
    prem = atm_iv - rv20
    print(f"  → Vol risk premium (IV-RV): {prem:+6.1%}   "
          f"{'IV richer → sellers of vol get paid' if prem > 0 else 'IV cheap vs recent moves'}")

    # --- 5: skew (OTM puts vs OTM calls) ---
    kp, ivp = iv_at(puts, S * 0.90)      # ~10% OTM put
    kc, ivc = iv_at(calls, S * 1.10)     # ~10% OTM call
    print("\n[5] SKEW — IV across strikes (crash fear lifts OTM-put IV)")
    print(f"  OTM put  (K≈{kp:.0f}, ~-10%): {ivp:6.1%}")
    print(f"  ATM      (K≈{atm_k:.0f})      : {atm_iv:6.1%}")
    print(f"  OTM call (K≈{kc:.0f}, ~+10%): {ivc:6.1%}")
    print(f"  → put IV {'>' if ivp > ivc else '<'} call IV  ⇒ "
          f"{'negative skew (typical equities: crash insurance costs more)' if ivp > ivc else 'unusual'}")

    # --- 4: the Greeks for the ATM call & put (from our Black-Scholes) ---
    print("\n[4] THE GREEKS — ATM call & put (Black-Scholes, sigma = ATM IV)")
    print(f"  {'':8}{'price':>9}{'delta':>9}{'gamma':>9}{'vega':>9}{'theta/day':>11}")
    for name, is_call in [("call", True), ("put", False)]:
        g = bs(S, atm_k, T, R, atm_iv, call=is_call)
        print(f"  {name:<8}{g['price']:>9.2f}{g['delta']:>9.2f}{g['gamma']:>9.4f}"
              f"{g['vega']:>9.3f}{g['theta']:>11.3f}")
    print("\n  Read: delta = $ move per $1 of SPY · gamma = how fast delta changes ·")
    print("  vega = $ per +1% IV · theta = $ lost per day to time decay (why sellers like it).")


if __name__ == "__main__":
    main()
