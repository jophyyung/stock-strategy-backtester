"""
Strategy module.

Implements trading strategies that take historical price data
and produce buy/sell signals based on technical indicators.

Current strategies:
- Moving Average Crossover (golden/death cross)
"""

import pandas as pd

def moving_average_crossover(
    prices: pd.DataFrame,
    short_window: int = 50,
    long_window: int = 200
) -> pd.DataFrame:
    """
    Compute moving average crossover signals.

    A 'golden cross' occurs when the short MA crosses above the long MA (buy signal).
    A 'death cross' occurs when the short MA crosses below the long MA (sell signal).

    Args:
        prices: DataFrame with at least a 'close' column, indexed by date.
        short_window: Lookback period for the short moving average (default 50 days).
        long_window: Lookback period for the long moving average (default 200 days).

    Returns:
        A new DataFrame (copy of input) with these added columns:
        - short_ma: Short moving average
        - long_ma: Long moving average
        - signal: 1 when short_ma > long_ma (in market), else 0 (out of market)
    """
    # Sanity check the inputs
    if short_window >= long_window:
        raise ValueError(
            f"short_window ({short_window}) must be less than long_window ({long_window})"
        )

    # Work on a copy so we don't mutate the caller's DataFrame
    df = prices.copy()

    # Compute the moving averages on the closing price
    df["short_ma"] = df["close"].rolling(window=short_window).mean()
    df["long_ma"] = df["close"].rolling(window=long_window).mean()

    # Generate the signal
    # When short_ma > long_ma, we want to be in the market (signal = 1)
    # Otherwise, we want to be out of the market (signal = 0)
    df["signal"] = (df["short_ma"] > df["long_ma"]).astype(int)

    return df