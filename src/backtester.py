"""
Backtester module.

Simulates how a trading strategy would have performed historically
by walking through price data day-by-day and applying signals.
"""

import pandas as pd


def run_backtest(
    prices_with_signal: pd.DataFrame,
    initial_capital: float = 10_000.0
) -> pd.DataFrame:
    """
    Run a backtest on prices that already contain a signal column.

    Args:
        prices_with_signal: DataFrame with at least 'close' and 'signal' columns.
                           The signal column should be 1 (in market) or 0 (out).
        initial_capital: Starting portfolio value in dollars (default $10,000).

    Returns:
        DataFrame with original columns plus:
        - return: Daily return of the underlying stock
        - strategy_return: Daily return of the strategy
        - equity: Running portfolio value following the strategy
        - buy_hold_equity: Running portfolio value if you just bought and held
    """
    # Sanity check the inputs
    required_columns = ["close", "signal"]
    for col in required_columns:
        if col not in prices_with_signal.columns:
            raise ValueError(f"Required column '{col}' not found in input DataFrame")

    # Work on a copy to avoid mutating the caller's DataFrame
    df = prices_with_signal.copy()

    # Compute the daily return of the underlying stock
    # pct_change() gives us (today - yesterday) / yesterday
    df["return"] = df["close"].pct_change()

    # Shift the signal forward by one day to avoid look-ahead bias
    # The signal on day T can only act on day T+1
    shifted_signal = df["signal"].shift(1)

    # Strategy return: stock's return × yesterday's signal (we're either in or out)
    df["strategy_return"] = df["return"] * shifted_signal

    # Compute the running portfolio value (equity curve)
    # (1 + return) cumulated, multiplied by starting capital
    df["equity"] = (1 + df["strategy_return"].fillna(0)).cumprod() * initial_capital

    # Compute the buy-and-hold benchmark for comparison
    df["buy_hold_equity"] = (1 + df["return"].fillna(0)).cumprod() * initial_capital

    return df