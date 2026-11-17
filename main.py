"""Dip-buy mean-reversion bot for the make.fun BTC race.

The bot trades cbBTC (CBBTC) against USDC on one-minute bars, long only,
with $1,000 of paper money. It buys only when the close is far below its
4-hour EMA (240 one-minute bars) and sells when the price reverts to that
EMA, or on a take-profit / stop-loss measured from the average fill cost
of the position.

Trades are rare on purpose. A full-size round trip pays roughly 26-37 bps
in fees, slippage and price impact, so a bot that trades often bleeds out
on 1-minute noise; a bot that waits for a real dip and holds for the
reversion only pays that toll a handful of times.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

EMA_SPAN = 240
EMA_ALPHA = 2.0 / (EMA_SPAN + 1)
MIN_BARS = 240

ENTRY_DIP_BPS = -70      # buy when the close is 70 bps below the EMA
TAKE_PROFIT_BPS = 100    # sell when 100 bps above the average fill price
STOP_LOSS_BPS = -80      # sell when 80 bps below the average fill price
MAX_SLIPPAGE_BPS = 100


class DipBuyer:
    """Keeps the EMA and the entry price across batches."""

    def __init__(self):
        self.ema = None
        self.bars_seen = 0
        self.entry_close = None

    def on_batch(self, state, batch):
        # Defensive guard: no bar for the symbol yet (or an invalid
        # close) means there is nothing to trade on — return without
        # touching the EMA, the position, or any order.
        close = state.close(SYMBOL)
        if close is None or close <= 0:
            return []
        if self.ema is None:
            self.ema = float(close)
        else:
            self.ema = EMA_ALPHA * close + (1.0 - EMA_ALPHA) * self.ema
        self.bars_seen += 1

        if state.warming_up or self.bars_seen < MIN_BARS:
            return []

        holding = state.positions.get(SYMBOL)
        if holding is None or holding.qty <= 0:
            self.entry_close = None
            dip_bps = (close / self.ema - 1.0) * 10_000
            if dip_bps < ENTRY_DIP_BPS and state.cash > 0:
                self.entry_close = close
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        # TP/SL are measured from the actual average fill cost, not the
        # decision-bar close proxy: the fill can differ from the close
        # that triggered the buy (fees, slippage, price impact), so the
        # close proxy misstates both the profit taken and the loss cut.
        # Holding.cost is in quote units and qty in base units, and
        # prices are price-scale ints (10**7), so the average fill
        # price is cost * 10**7 // qty.
        if holding.cost and holding.qty > 0:
            entry_price = holding.cost * 10**7 // holding.qty
        else:
            if self.entry_close is None:
                self.entry_close = close
            entry_price = self.entry_close
        reverted = close >= self.ema
        move_bps = (close / entry_price - 1.0) * 10_000
        if reverted or move_bps > TAKE_PROFIT_BPS or move_bps < STOP_LOSS_BPS:
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []


BOT = DipBuyer()


def on_batch(state, batch):
    return BOT.on_batch(state, batch)


makefun_bars.run(on_batch)
