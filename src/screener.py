"""
Screener module.

Scans all stocks in the database against technical filters
and returns ranked lists of matching candidates.
"""

import sqlite3
from pathlib import Path

import pandas as pd

from src.data_loader import DB_PATH, load_prices
from src.strategy import (
    moving_average_crossover,
    rsi_mean_reversion,
    bollinger_bands,
)


def get_all_tickers_in_db() -> list[str]:
    """Return all tickers currently stored in the local database."""
    if not Path(DB_PATH).exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT DISTINCT ticker FROM prices ORDER BY ticker")
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers


def screen_rsi(
    threshold: float = 30.0,
    direction: str = "below",
    rsi_window: int = 14,
) -> pd.DataFrame:
    """
    Find stocks with RSI above or below a threshold.

    Args:
        threshold: RSI value to compare against (default 30).
        direction: 'below' for oversold, 'above' for overbought.
        rsi_window: Lookback period for RSI (default 14).

    Returns:
        DataFrame ranked by current RSI value, with columns:
        ticker, rsi, close, change_1d_pct
    """
    if direction not in ("below", "above"):
        raise ValueError(f"direction must be 'below' or 'above', got {direction}")

    tickers = get_all_tickers_in_db()
    results = []

    for ticker in tickers:
        try:
            prices = load_prices(ticker)
            if len(prices) < rsi_window + 1:
                continue

            # Compute RSI using the existing strategy function
            df = rsi_mean_reversion(prices, rsi_window=rsi_window)
            latest_rsi = df["rsi"].iloc[-1]

            if pd.isna(latest_rsi):
                continue

            # Apply the filter
            if direction == "below" and latest_rsi < threshold:
                results.append({
                    "ticker": ticker,
                    "rsi": round(latest_rsi, 2),
                    "close": round(df["close"].iloc[-1], 2),
                    "change_1d_pct": round(df["close"].pct_change().iloc[-1] * 100, 2),
                })
            elif direction == "above" and latest_rsi > threshold:
                results.append({
                    "ticker": ticker,
                    "rsi": round(latest_rsi, 2),
                    "close": round(df["close"].iloc[-1], 2),
                    "change_1d_pct": round(df["close"].pct_change().iloc[-1] * 100, 2),
                })

        except Exception:
            # Skip any ticker that fails (corrupt data, etc.)
            continue

    if not results:
        return pd.DataFrame(columns=["ticker", "rsi", "close", "change_1d_pct"])

    df_results = pd.DataFrame(results)
    # Sort: most oversold first if below, most overbought first if above
    df_results = df_results.sort_values(
        "rsi",
        ascending=(direction == "below"),
    ).reset_index(drop=True)

    return df_results


def screen_ma_crossover(
    short_window: int = 50,
    long_window: int = 200,
    just_crossed: bool = True,
    lookback_days: int = 5,
) -> pd.DataFrame:
    """
    Find stocks where the short MA has crossed above the long MA recently.

    Args:
        short_window: Short MA period (default 50).
        long_window: Long MA period (default 200).
        just_crossed: If True, only return stocks that crossed in the last N days.
        lookback_days: How many days back to look for crossings (default 5).

    Returns:
        DataFrame with columns: ticker, close, short_ma, long_ma, days_since_cross
    """
    tickers = get_all_tickers_in_db()
    results = []

    for ticker in tickers:
        try:
            prices = load_prices(ticker)
            if len(prices) < long_window + lookback_days:
                continue

            df = moving_average_crossover(
                prices,
                short_window=short_window,
                long_window=long_window,
            )

            # Check if signal changed from 0 to 1 in the last `lookback_days`
            recent_signals = df["signal"].tail(lookback_days + 1)
            signal_diffs = recent_signals.diff()
            crossings = (signal_diffs == 1)

            if just_crossed and not crossings.any():
                continue

            # If a crossing happened, find how many days ago
            if just_crossed:
                crossing_indices = crossings[crossings].index
                days_since = len(df) - df.index.get_loc(crossing_indices[-1]) - 1
            else:
                # If just_crossed is False, only include stocks currently in bullish state
                if df["signal"].iloc[-1] != 1:
                    continue
                days_since = None

            results.append({
                "ticker": ticker,
                "close": round(df["close"].iloc[-1], 2),
                "short_ma": round(df["short_ma"].iloc[-1], 2),
                "long_ma": round(df["long_ma"].iloc[-1], 2),
                "days_since_cross": days_since,
            })

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    df_results = pd.DataFrame(results)
    if just_crossed:
        df_results = df_results.sort_values("days_since_cross").reset_index(drop=True)
    else:
        df_results = df_results.sort_values("ticker").reset_index(drop=True)

    return df_results


def screen_bollinger(
    position: str = "below_lower",
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """
    Find stocks where the latest close is at the upper or lower Bollinger band.

    Args:
        position: 'below_lower' for stocks below the lower band (oversold),
                  'above_upper' for stocks above the upper band (overbought).
        window: Bollinger lookback period (default 20).
        num_std: Number of standard deviations for the bands (default 2).

    Returns:
        DataFrame with columns: ticker, close, lower, middle, upper,
        distance_from_band_pct
    """
    if position not in ("below_lower", "above_upper"):
        raise ValueError(
            f"position must be 'below_lower' or 'above_upper', got {position}"
        )

    tickers = get_all_tickers_in_db()
    results = []

    for ticker in tickers:
        try:
            prices = load_prices(ticker)
            if len(prices) < window + 1:
                continue

            df = bollinger_bands(prices, window=window, num_std=num_std)
            close = df["close"].iloc[-1]
            upper = df["bb_upper"].iloc[-1]
            lower = df["bb_lower"].iloc[-1]
            middle = df["bb_middle"].iloc[-1]

            if pd.isna(upper) or pd.isna(lower):
                continue

            if position == "below_lower" and close < lower:
                distance_pct = ((lower - close) / lower) * 100
                results.append({
                    "ticker": ticker,
                    "close": round(close, 2),
                    "lower": round(lower, 2),
                    "middle": round(middle, 2),
                    "upper": round(upper, 2),
                    "distance_from_band_pct": round(distance_pct, 2),
                })
            elif position == "above_upper" and close > upper:
                distance_pct = ((close - upper) / upper) * 100
                results.append({
                    "ticker": ticker,
                    "close": round(close, 2),
                    "lower": round(lower, 2),
                    "middle": round(middle, 2),
                    "upper": round(upper, 2),
                    "distance_from_band_pct": round(distance_pct, 2),
                })

        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(
        "distance_from_band_pct",
        ascending=False,
    ).reset_index(drop=True)

    return df_results