"""
DOS (Direction of SuperTrend) strategy rules, implementing the spec exactly:

- Instrument: Bank Nifty Futures, weekly-expiry Wed/Thu only
- Timeframe: 5-min candles, SuperTrend(period=10, multiplier=3)
- Entry: 9:20 AM or later (first bar with a confirmed SuperTrend value)
- Signal: BNF Fut > SuperTrend -> SELL CE (call). BNF Fut < SuperTrend -> SELL PE (put).
- Strike: nearest 100 rounded from the current SuperTrend value (not spot)
- Initial SL: 50% of premium sold on Wednesday, 100% on Thursday
- Trailing SL: triggers when price closes above/below the ST value of the
  short leg, whichever is *lower* risk-wise for a short option seller
- Default exit: market close if no SL is hit
"""


def select_strike(supertrend_value, step=100):
    """Nearest `step`-rounded strike from the current SuperTrend value."""
    return round(supertrend_value / step) * step


def get_signal(fut_price, supertrend_value):
    """Returns 'CE' (sell call) or 'PE' (sell put) or None if fut==ST exactly."""
    if fut_price > supertrend_value:
        return "CE"
    elif fut_price < supertrend_value:
        return "PE"
    return None


def initial_sl_pct(day_type):
    """50% of premium on Wednesday, 100% on Thursday (Thursday expiry is same-day, higher theta burn tolerance)."""
    return 0.50 if day_type == "Wednesday" else 1.00


def initial_sl_price(premium_sold, day_type):
    """SL price level for a SHORT option: loss cap is a premium INCREASE of the SL%."""
    return premium_sold * (1 + initial_sl_pct(day_type))


def trailing_sl_hit(current_supertrend, option_type, bar_close_fut_price):
    """
    Trailing SL logic: for a short CE, the position is at risk if BNF Fut closes
    back BELOW the SuperTrend (trend flips against the seller's directional
    assumption). For a short PE, at risk if BNF Fut closes back ABOVE the ST.
    Returns True if the trailing exit condition is triggered.
    """
    if option_type == "CE":
        return bar_close_fut_price < current_supertrend
    else:
        return bar_close_fut_price > current_supertrend


def entry_allowed(bar_time):
    """Entry only at 9:20 AM or later."""
    return (bar_time.hour, bar_time.minute) >= (9, 20)
