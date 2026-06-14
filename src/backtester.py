"""
Backtester module.

Simulates how a trading strategy would have performed historically
by walking through price data day-by-day and applying signals.
"""

import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 10_000,
    commission_per_trade: float = 0.0,
    slippage_bps: float = 0.0,
) -> pd.DataFrame:
    """
    Run a backtest on a DataFrame with price and signal columns.

    Applies signals with proper look-ahead bias prevention by shifting
    the signal by one day. Optionally models transaction costs.

    Args:
        df: DataFrame with at least 'close' and 'signal' columns.
        initial_capital: Starting portfolio value (default 10,000).
        commission_per_trade: Fixed commission per buy or sell (default 0).
        slippage_bps: Slippage in basis points (1/100th of 1%) applied to
            each trade. E.g. 5 bps = 0.05% applied as cost on each side
            of a round-trip trade (default 0 for no slippage).

    Returns:
        DataFrame with added columns:
            return: daily price return (% change)
            strategy_return: daily strategy return (after costs)
            equity: portfolio value over time (strategy)
            buy_hold_equity: portfolio value over time (buy-and-hold)
            trade_cost: cost incurred on each trading day
    """
    result = df.copy()

    # Daily returns (price change as a decimal)
    result["return"] = result["close"].pct_change()

    # CRITICAL: Shift signal by 1 day to prevent look-ahead bias
    # Today's signal acts on tomorrow's return
    position = result["signal"].shift(1).fillna(0)

    # Identify trade events: 0->1 (buy) or 1->0 (sell)
    position_change = position.diff().fillna(0)
    is_trade_day = position_change != 0

    # Calculate cost as a fraction of portfolio value on each trade day
    # Slippage: bps converted to decimal, applied on the trade day
    slippage_cost = abs(position_change) * (slippage_bps / 10_000.0)

    # Commission: dollar amount as fraction of current capital
    # We approximate using initial capital as the denominator for simplicity
    # (more accurate to use running equity but adds complexity)
    commission_cost = is_trade_day.astype(float) * (commission_per_trade / initial_capital)

    # Total daily cost
    result["trade_cost"] = slippage_cost + commission_cost

    # Strategy returns: when in position, get market returns minus costs
    result["strategy_return"] = (position * result["return"]) - result["trade_cost"]

    # Cumulative equity curves
    result["equity"] = initial_capital * (1 + result["strategy_return"].fillna(0)).cumprod()
    result["buy_hold_equity"] = initial_capital * (1 + result["return"].fillna(0)).cumprod()

    return result