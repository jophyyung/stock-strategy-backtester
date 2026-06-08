"""
Metrics module.

Computes performance metrics from a backtest result:
- Total and annualised returns
- Annualised volatility
- Sharpe ratio
- Maximum drawdown
- Trade statistics (count, win rate, profit factor)
"""

import numpy as np
import pandas as pd


# Number of trading days in a year (US/HK both use ~252)
TRADING_DAYS_PER_YEAR = 252


def total_return(equity: pd.Series) -> float:
    """
    Compute the total return as a decimal (e.g. 0.50 = 50% gain).

    Args:
        equity: Series of portfolio values over time.

    Returns:
        Total return as a decimal.
    """
    return equity.iloc[-1] / equity.iloc[0] - 1


def annualised_return(equity: pd.Series) -> float:
    """
    Compute the annualised return (CAGR - Compound Annual Growth Rate).

    Args:
        equity: Series of portfolio values, indexed by date.

    Returns:
        Annualised return as a decimal.
    """
    num_days = len(equity)
    years = num_days / TRADING_DAYS_PER_YEAR

    total = total_return(equity)
    return (1 + total) ** (1 / years) - 1


def annualised_volatility(returns: pd.Series) -> float:
    """
    Compute the annualised volatility (standard deviation of returns).

    Args:
        returns: Series of daily returns.

    Returns:
        Annualised volatility as a decimal.
    """
    return returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Compute the annualised Sharpe ratio.

    Sharpe = (annualised return - risk-free rate) / annualised volatility

    Args:
        returns: Series of daily returns.
        risk_free_rate: Annual risk-free rate as a decimal (default 0).

    Returns:
        Annualised Sharpe ratio.
    """
    # Annualised mean daily return
    annual_return = returns.mean() * TRADING_DAYS_PER_YEAR

    # Annualised volatility
    annual_vol = annualised_volatility(returns)

    # Guard against divide-by-zero (a flat strategy with no movement)
    if annual_vol == 0:
        return 0.0

    return (annual_return - risk_free_rate) / annual_vol


def max_drawdown(equity: pd.Series) -> float:
    """
    Compute the maximum drawdown (worst peak-to-trough loss).

    A drawdown is the percentage drop from a previous peak.
    Maximum drawdown is the largest such drop the strategy experienced.

    Args:
        equity: Series of portfolio values over time.

    Returns:
        Maximum drawdown as a negative decimal (e.g. -0.25 = 25% peak-to-trough loss).
    """
    # Running maximum of equity curve at each point in time
    running_max = equity.cummax()

    # Drawdown at each point = (current - peak) / peak
    drawdown = (equity - running_max) / running_max

    # The maximum drawdown is the most negative value in the drawdown series
    return drawdown.min()


def count_trades(signal: pd.Series) -> int:
    """
    Count the number of completed trades (buy events).

    A trade is defined as a transition from 0 to 1 in the signal column.

    Args:
        signal: Series of signal values (0 or 1).

    Returns:
        Number of trades.
    """
    transitions = signal.diff()
    buys = (transitions == 1).sum()
    return int(buys)


def trade_stats(strategy_returns: pd.Series, signal: pd.Series) -> dict:
    """
    Compute per-trade statistics: win rate, average win, average loss, profit factor.

    A 'trade' here is each continuous period of being in the market (signal = 1).
    For each trade, we sum its daily returns to get the trade's total return.

    Args:
        strategy_returns: Series of daily strategy returns.
        signal: Series of signal values (0 or 1).

    Returns:
        Dictionary with keys: num_trades, win_rate, avg_win, avg_loss, profit_factor.
    """
    # Group consecutive periods where signal == 1 (we're holding a position)
    # When signal flips, the trade ends
    in_position = signal.shift(1).fillna(0).astype(int)
    trade_id = (in_position.diff() == 1).cumsum()

    # Only keep rows where we were actually in the market
    active = in_position == 1

    # Sum daily returns per trade
    trade_returns = strategy_returns[active].groupby(trade_id[active]).sum()

    # Convert from log-style sums to approximate trade returns
    # Note: for small returns, summing daily returns is a close approximation
    # of compound return. This is the standard simplification for backtests.

    num_trades = len(trade_returns)

    if num_trades == 0:
        return {
            "num_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
        }

    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]

    win_rate = len(wins) / num_trades if num_trades > 0 else 0.0
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0

    # Profit factor = total wins / total losses (absolute)
    total_wins = wins.sum()
    total_losses = abs(losses.sum())
    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

    return {
        "num_trades": num_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
    }