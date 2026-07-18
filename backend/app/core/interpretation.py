"""
Plain-language interpretation cards.

These are template-driven, not NLP: compute the number, bucket it against
thresholds grounded in how NSE option-chain readers actually use them, and
render a one-line explanation. Keeping this rule-based (rather than reaching
for an LLM call) keeps it deterministic, free, and instant to render.
"""
import numpy as np


def compute_pcr(chain_df):
    """Put-Call Ratio = Total Put OI / Total Call OI."""
    call_oi = chain_df.loc[chain_df.option_type == "call", "open_interest"].sum()
    put_oi = chain_df.loc[chain_df.option_type == "put", "open_interest"].sum()
    return put_oi / call_oi if call_oi > 0 else np.nan


def pcr_card(pcr):
    pcr = float(pcr)
    if pcr > 1.3:
        sentiment, note = "Bullish", "Heavy put writing relative to calls suggests traders expect a floor -- bullish-to-neutral bias."
    elif pcr < 0.7:
        sentiment, note = "Bearish", "Call OI dominating put OI suggests resistance building up -- bearish-to-neutral bias."
    else:
        sentiment, note = "Neutral", "Put and call OI are roughly balanced -- no strong directional skew from positioning."
    return {"metric": "PCR", "value": round(float(pcr), 2), "sentiment": sentiment, "note": note}


def compute_max_pain(chain_df):
    """
    Max pain strike: the strike at which option WRITERS (sellers) collectively
    lose the least, i.e. buyers' aggregate payout is minimized. Computed by
    summing intrinsic-value payouts across all strikes for each candidate
    expiry price and picking the minimum.
    """
    strikes = sorted(chain_df.strike.unique())
    total_loss_to_writers = []
    for candidate_price in strikes:
        loss = 0.0
        for _, row in chain_df.iterrows():
            if row.option_type == "call" and candidate_price > row.strike:
                loss += (candidate_price - row.strike) * row.open_interest
            elif row.option_type == "put" and candidate_price < row.strike:
                loss += (row.strike - candidate_price) * row.open_interest
        total_loss_to_writers.append(loss)
    idx = int(np.argmin(total_loss_to_writers))
    return float(strikes[idx])


def max_pain_card(max_pain_strike, spot):
    max_pain_strike = float(max_pain_strike)
    spot = float(spot)
    direction = "above" if spot > max_pain_strike else "below" if spot < max_pain_strike else "at"
    pct = abs(spot - max_pain_strike) / max_pain_strike * 100
    note = (f"Spot is trading {pct:.1f}% {direction} the max pain strike of {max_pain_strike:.0f}. "
            f"Prices often gravitate toward max pain into expiry as writers defend positions.")
    return {"metric": "Max Pain", "value": max_pain_strike, "note": note}


def dos_trade_card(trade):
    """
    Plain-language interpretation card for one DOS trade (live or backtested).
    `trade` is a dict shaped like a row from backtester.run_backtest()'s trade
    log or the /api/dos/live-signal response, at minimum containing:
    day_type, option_type, strike, exit_reason, pnl_rupees, and (optionally)
    delta_pnl/gamma_pnl/theta_pnl/vega_pnl for the driver line.
    """
    day_type = trade.get("day_type", "session")
    opt = "call" if trade.get("option_type") == "CE" else "put"
    strike = trade.get("strike")
    exit_reason = trade.get("exit_reason", "open")
    pnl = trade.get("pnl_rupees")

    reason_note = {
        "initial_sl": "the initial stop-loss was hit -- the trade was cut early to cap loss.",
        "trailing_sl": "the trailing stop triggered as SuperTrend flipped against the sold side.",
        "market_close": "the position ran to market close with no stop-loss triggered.",
    }.get(exit_reason, "the trade is still open.")

    driver_note = ""
    greek_pnls = {k: trade.get(k) for k in ("delta_pnl", "gamma_pnl", "theta_pnl", "vega_pnl")
                  if trade.get(k) is not None}
    if greek_pnls:
        driver = max(greek_pnls, key=lambda k: abs(greek_pnls[k])).replace("_pnl", "").capitalize()
        driver_note = f" {driver} was the main driver of this trade's P&L."

    result = "profitable" if (pnl is not None and pnl > 0) else "a loss" if pnl is not None else "still open"
    note = (f"{day_type} DOS trade: sold the {strike:.0f} {opt} on the SuperTrend signal; "
            f"{reason_note} Result: {result}"
            + (f" of Rs {abs(pnl):,.0f}." if pnl is not None else ".") + driver_note)
    return {"metric": "DOS Trade", "day_type": day_type, "option_type": trade.get("option_type"),
            "strike": strike, "pnl_rupees": pnl, "note": note}


def iv_spike_card(current_iv, historical_avg_iv):
    """Flags unusually elevated or depressed IV relative to a trailing average."""
    current_iv, historical_avg_iv = float(current_iv), float(historical_avg_iv)
    if historical_avg_iv <= 0:
        return {"metric": "IV Spike", "value": None, "note": "Insufficient history to assess IV spike."}
    change_pct = (current_iv - historical_avg_iv) / historical_avg_iv * 100
    if change_pct > 15:
        note = f"ATM IV is {change_pct:.0f}% above its recent average -- market is pricing in an event or heightened uncertainty."
    elif change_pct < -15:
        note = f"ATM IV is {abs(change_pct):.0f}% below its recent average -- options are relatively cheap; low expected movement priced in."
    else:
        note = "ATM IV is close to its recent average -- no unusual volatility repricing right now."
    return {"metric": "IV Spike", "value": round(change_pct, 1), "note": note}
