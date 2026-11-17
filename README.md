# BTC Dip-Buy Mean-Reversion Bot

A dip-buy mean-reversion bot for the [make.fun](https://make.fun) `btc-race-24h-20261117-0603` competition ($250 USDC pool). It trades cbBTC (CBBTC) against USDC on one-minute bars, long only, with $1,000 of paper money. Simulation only — no real money, no network access in the bot.

## Strategy

- **Buy** 100% of cash when the close is **70 bps below the 4-hour EMA** (EMA over 240 one-minute bars).
- **Sell** when the price reverts to **>= EMA**, or on take-profit **+100 bps** / stop-loss **-80 bps** measured from the **average fill cost** of the position — not the decision-bar close, because the fill can differ from the close that triggered the buy (fees, slippage, price impact).
- **Discipline:** trades are rare on purpose. A full round trip costs roughly 26–37 bps in fees, slippage, and price impact, so a bot that trades often bleeds out on 1-minute noise; a bot that waits for a real dip and holds for the reversion only pays that toll a handful of times.

## Result

- make.fun dev grade: **net PnL +1.938498 USDC** — the entry passed the dev gate and races.
- Local backtest: +$1.94, 4 trades, max drawdown 0.54%.

## Running it

The bot is a make.fun harness entrypoint (`main.py`, Python 3.13, stdlib only). The harness calls `on_batch(state, batch)` once per bar batch; `vendor/makefun_bars.py` is the kit's bar loader and runner. There is no live trading here — the harness replays historical bars in simulation.

## Layout

- `main.py` — the bot: EMA tracking, dip-buy entry, TP/SL exit from average fill cost
- `vendor/makefun_bars.py` — bar loader/runner from the make.fun kit
- `LICENSE` — MIT
