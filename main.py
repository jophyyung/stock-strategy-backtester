"""
Main entry point for the stock backtester.

Phase 3: Backtest engine with performance metrics.
Loads price data, applies a strategy, runs a backtest,
and prints a comprehensive performance report.
"""

from src.data_loader import init_database, download_and_store, load_prices
from src.strategy import moving_average_crossover
from src.backtester import run_backtest
from src.metrics import (
    total_return,
    annualised_return,
    annualised_volatility,
    sharpe_ratio,
    max_drawdown,
    count_trades,
    trade_stats,
)


def refresh_data(tickers, period="5y"):
    """Initialise the database and download/refresh price data for given tickers."""
    print("=" * 70)
    print("Refreshing price data...")
    print("=" * 70)
    init_database()
    for ticker in tickers:
        download_and_store(ticker, period=period)


def print_metrics_block(label, equity, returns, signal=None):
    """Print a clean block of performance metrics for an equity curve."""
    print(f"\n{label}")
    print("-" * 70)
    print(f"  Total return:        {total_return(equity) * 100:+.2f}%")
    print(f"  Annualised return:   {annualised_return(equity) * 100:+.2f}%")
    print(f"  Annualised vol:      {annualised_volatility(returns) * 100:.2f}%")
    print(f"  Sharpe ratio:        {sharpe_ratio(returns):.2f}")
    print(f"  Max drawdown:        {max_drawdown(equity) * 100:.2f}%")
    if signal is not None:
        print(f"  Number of trades:    {count_trades(signal)}")
        stats = trade_stats(returns, signal)
        print(f"  Win rate:            {stats['win_rate'] * 100:.1f}%")
        print(f"  Avg win:             {stats['avg_win'] * 100:+.2f}%")
        print(f"  Avg loss:            {stats['avg_loss'] * 100:+.2f}%")
        print(f"  Profit factor:       {stats['profit_factor']:.2f}")


def backtest_one(ticker, short_window=50, long_window=200, initial_capital=10_000):
    """Run a backtest on a single ticker and print a full performance report."""
    print()
    print("=" * 70)
    print(f"Backtest: {ticker} | MA{short_window}/MA{long_window}")
    print("=" * 70)

    prices = load_prices(ticker)
    if prices.empty:
        print(f"No data for {ticker}. Skipping.")
        return

    # Apply the strategy
    with_signals = moving_average_crossover(
        prices,
        short_window=short_window,
        long_window=long_window,
    )

    # Run the backtest
    results = run_backtest(with_signals, initial_capital=initial_capital)

    # Metadata
    print(f"Period:              {results.index.min().date()} to {results.index.max().date()}")
    print(f"Starting capital:    ${initial_capital:,.2f}")
    print(f"Strategy final:      ${results['equity'].iloc[-1]:,.2f}")
    print(f"Buy-and-hold final:  ${results['buy_hold_equity'].iloc[-1]:,.2f}")

    # Strategy metrics
    print_metrics_block(
        "STRATEGY METRICS",
        results["equity"],
        results["strategy_return"].dropna(),
        signal=results["signal"],
    )

    # Buy-and-hold metrics
    print_metrics_block(
        "BUY-AND-HOLD METRICS",
        results["buy_hold_equity"],
        results["return"].dropna(),
    )


def main():
    tickers = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "0700.HK",
        "0005.HK",
    ]

    # Refresh data (comment this line out if data is already up to date)
    refresh_data(tickers, period="5y")

    # Run backtest on each ticker
    for ticker in tickers:
        backtest_one(ticker, short_window=50, long_window=200)


if __name__ == "__main__":
    main()