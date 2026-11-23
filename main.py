# RangeBreak — a cbBTC breakout-and-hold bot for make.fun's BTC race.
#
# Idea, in one paragraph: the first two hours of a 24-hour window set a
# range. If price breaks above that range's highest close, a real move is
# usually under way, so the bot commits almost all of its cash and then
# does as little as possible: it holds through ordinary chop and leaves
# only when the move is demonstrably over — the close falls 4% under the
# highest close since entry (trailing stop) or 5% under the entry close
# (hard stop). If no breakout ever comes, a single smaller probe trade in
# the second half keeps the bot in the race without betting the account
# on a market that never moved. Every decision is integer arithmetic on
# the closes seen so far: no clock, no files, no network, so two runs on
# the same bars send the same orders.
#
# Costs shape the design. A full-size round trip pays roughly 26 bps in
# fees, slippage and pool impact, so the bot trades a handful of times
# per window at most, and sizes against the pool depth the SDK reports.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
RANGE_BARS = 120          # opening range: the first two hours of closes
TRAIL_NUM, TRAIL_DEN = 96, 100    # trailing stop: 4% under the peak close
HARD_NUM, HARD_DEN = 95, 100      # hard stop: 5% under the entry close
PROBE_BAR = 720           # halfway: probe if no breakout ever triggered
PROBE_UP = 60             # probe size (% of cash) when above the 360-bar mean
PROBE_DOWN = 25           # probe size (% of cash) otherwise
DEPLOY = 95               # breakout entry size (% of cash)
MAX_SLIPPAGE_BPS = 100

closes = []               # every close of SYMBOL, warm-up included
range_hi = None           # highest close of the opening range
peak_close = None         # highest close since the current entry
entry_close = None        # close on the bar that decided the current entry
probed = False


def _mean_last(n):
    if len(closes) < n:
        return None
    return sum(closes[-n:]) / n


def on_batch(state, batch):
    global range_hi, peak_close, entry_close, probed
    close = state.close(SYMBOL)
    if close is None:
        return None
    closes.append(close)
    if len(closes) <= RANGE_BARS:
        range_hi = close if range_hi is None else max(range_hi, close)
    if state.warming_up:
        return None

    held = state.positions.get(SYMBOL)
    if held is not None and held.qty > 0:
        # A position is open: guard it, never add to it.
        if entry_close is None:
            entry_close = close
            peak_close = close
        peak_close = max(peak_close, close)
        if close * TRAIL_DEN < peak_close * TRAIL_NUM or close * HARD_DEN < entry_close * HARD_NUM:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return None

    # Flat. A fill may have landed since the last decision; reset markers.
    peak_close = None
    entry_close = None
    if len(closes) > RANGE_BARS and range_hi is not None and close > range_hi:
        spend = min(state.cash * DEPLOY // 100, state.weight_room(SYMBOL))
        if spend >= 1_000_000:
            entry_close = close
            peak_close = close
            return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return None
    if len(closes) >= PROBE_BAR and not probed:
        probed = True
        mean = _mean_last(360)
        pct = PROBE_UP if (mean is not None and close > mean) else PROBE_DOWN
        spend = min(state.cash * pct // 100, state.weight_room(SYMBOL))
        if spend >= 1_000_000:
            entry_close = close
            peak_close = close
            return [{"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return None


if __name__ == "__main__":
    makefun_bars.run(on_batch)
