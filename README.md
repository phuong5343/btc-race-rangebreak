# RangeBreak

A cbBTC trading bot for make.fun's "Race a BTC trading bot live for 24 hours"
(btc-race-24h-20261123-0511), built by an AI agent for vivid-ibis-80.

Simulation only: the bot trades paper money against real on-chain cbBTC
prices, one 1-minute bar at a time, through the `agent-fun/bars-replay/v1`
protocol (Python shim vendored in `vendor/`, run as `python3 main.py`).

## Strategy

- The first 120 closes set an **opening range**. A close above its highest
  point is a breakout: the bot deploys 95% of its cash.
- It then **holds through chop** and exits only on a 4% trailing stop under
  the highest close since entry, or a 5% hard stop under the entry close.
- No breakout by the halfway bar: one **probe** trade (60% of cash above
  the 360-bar mean, 25% below it) keeps the bot in the race cheaply.
- Costs drive the design: a full-size round trip pays ~26 bps in fees,
  slippage and pool impact, so the bot trades a handful of times per
  window, never more.

Decisions are integer arithmetic on the closes seen so far — no clock, no
network, no files — so the same bars always produce the same orders.

On the published dev window this design made about +$26 net on the $1,000
start in local simulation (one trade, ~1.9% maximum drawdown), clearing the
dev gate with room to spare while risking far less than a plain hold in a
falling market.

MIT licensed.
