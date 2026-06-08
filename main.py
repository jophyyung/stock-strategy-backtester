"""
Main entry point for the stock backtester.

Phase 4: Multi-strategy comparison.
Runs three different trading strategies on each ticker and produces
a side-by-side performance comparison.
"""

from src.data_loader import init_database, download_and_store, load_prices
from src.strategy import (
    moving_average_crossover,
    rsi_mean_reversion,
    bollinger_bands,
)
from src.backtester import run_backtest
from src.metrics import (
    total_return,
    annualised_return,
    annualised_volatility,
    sharpe_ratio,
    max_drawdown,
    count_trades,
)


def refresh_data(tickers, period="5y"):
    """Initialise the database and download/refresh price data for given tickers."""
    print("=" * 80)
    print("Refreshing price data...")
    print("=" * 80)
    init_database()
    for ticker in tickers:
        download_and_store(ticker, period=period)


def compute_strategy_metrics(results, signal_col="signal"):
    """Compute the standard metrics dictionary for a backtest result."""
    return {
        "total_return": total_return(results["equity"]),
        "annual_return": annualised_return(results["equity"]),
        "annual_vol": annualised_volatility(results["strategy_return"].dropna()),
        "sharpe": sharpe_ratio(results["strategy_return"].dropna()),
        "max_dd": max_drawdown(results["equity"]),
        "trades": count_trades(results[signal_col]),
    }


def compute_buy_hold_metrics(results):
    """Compute the standard metrics for buy-and-hold benchmark."""
    return {
        "total_return": total_return(results["buy_hold_equity"]),
        "annual_return": annualised_return(results["buy_hold_equity"]),
        "annual_vol": annualised_volatility(results["return"].dropna()),
        "sharpe": sharpe_ratio(results["return"].dropna()),
        "max_dd": max_drawdown(results["buy_hold_equity"]),
        "trades": 0,
    }


def print_comparison_table(ticker, period_start, period_end, results_by_strategy):
    """Print a clean side-by-side comparison of strategies."""
    print()
    print("=" * 80)
    print(f"Multi-Strategy Comparison: {ticker}  |  {period_start} to {period_end}")
    print("=" * 80)

    # Column headers
    header_format = "{:<20} {:>12} {:>12} {:>12} {:>10}"
    row_format = "{:<20} {:>11.2f}% {:>11.2f}% {:>12.2f} {:>9.2f}% {:>10}"

    print(header_format.format("Strategy", "Total Ret", "Annual Ret", "Sharpe", "Max DD"))
    print("-" * 80)

    for strategy_name, metrics in results_by_strategy.items():
        print(
            "{:<20} {:>11.2f}% {:>11.2f}% {:>12.2f} {:>9.2f}% {:>10}".format(
                strategy_name,
                metrics["total_return"] * 100,
                metrics["annual_return"] * 100,
                metrics["sharpe"],
                metrics["max_dd"] * 100,
                metrics["trades"] if metrics["trades"] > 0 else "-",
            )
        )


def backtest_all_strategies(ticker, initial_capital=10_000):
    """Run all strategies on a single ticker and print a comparison table."""
    prices = load_prices(ticker)
    if prices.empty:
        print(f"No data for {ticker}. Skipping.")
        return

    period_start = prices.index.min().date()
    period_end = prices.index.max().date()

    results_by_strategy = {}

    # Strategy 1: MA Crossover
    ma_signals = moving_average_crossover(prices, short_window=50, long_window=200)
    ma_results = run_backtest(ma_signals, initial_capital=initial_capital)
    results_by_strategy["MA Crossover (50/200)"] = compute_strategy_metrics(ma_results)

    # Strategy 2: RSI Mean Reversion
    rsi_signals = rsi_mean_reversion(prices, rsi_window=14)
    rsi_results = run_backtest(rsi_signals, initial_capital=initial_capital)
    results_by_strategy["RSI Mean Reversion"] = compute_strategy_metrics(rsi_results)

    # Strategy 3: Bollinger Bands
    bb_signals = bollinger_bands(prices, window=20, num_std=2.0)
    bb_results = run_backtest(bb_signals, initial_capital=initial_capital)
    results_by_strategy["Bollinger Bands"] = compute_strategy_metrics(bb_results)

    # Benchmark: Buy and Hold (same for all, use any results)
    results_by_strategy["Buy-and-Hold"] = compute_buy_hold_metrics(ma_results)

    # Print comparison
    print_comparison_table(ticker, period_start, period_end, results_by_strategy)


def main():
    tickers = [
        "AAPL",      # US tech
        "MSFT",      # US tech
        "GOOGL",     # US tech
        "0700.HK",   # Tencent
        "0005.HK",   # HSBC
    ]

    # Refresh data (comment this out if data is already up to date)
    refresh_data(tickers, period="5y")

    # Run multi-strategy comparison on each ticker
    for ticker in tickers:
        backtest_all_strategies(ticker)


if __name__ == "__main__":
    main()