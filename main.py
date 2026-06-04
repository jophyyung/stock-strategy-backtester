"""
Main entry point for the stock backtester.

Phase 2: Backtest Engine
Loads price data, applies a strategy, runs a backtest,
and prints a performance summary.
"""

from src.data_loader import init_database, download_and_store, load_prices
from src.strategy import moving_average_crossover
from src.backtester import run_backtest


def refresh_data(tickers, period="5y"):
    """Initialise the database and download/refresh price data for given tickers."""
    print("=" * 60)
    print("Refreshing price data...")
    print("=" * 60)
    init_database()
    for ticker in tickers:
        download_and_store(ticker, period=period)


def backtest_one(ticker, short_window=50, long_window=200, initial_capital=10_000):
    """Run a backtest on a single ticker and print summary stats."""
    print()
    print("=" * 60)
    print(f"Backtest: {ticker} | MA{short_window}/MA{long_window}")
    print("=" * 60)

    prices = load_prices(ticker)
    if prices.empty:
        print(f"No data for {ticker}. Skipping.")
        return

    with_signals = moving_average_crossover(
        prices,
        short_window=short_window,
        long_window=long_window
    )

    results = run_backtest(with_signals, initial_capital=initial_capital)

    final_strategy = results["equity"].iloc[-1]
    final_buy_hold = results["buy_hold_equity"].iloc[-1]

    strategy_return_pct = (final_strategy / initial_capital - 1) * 100
    buy_hold_return_pct = (final_buy_hold / initial_capital - 1) * 100

    print(f"Period: {results.index.min().date()} to {results.index.max().date()}")
    print(f"Starting capital:        ${initial_capital:>12,.2f}")
    print(f"Strategy final value:    ${final_strategy:>12,.2f}  ({strategy_return_pct:+.2f}%)")
    print(f"Buy-and-hold final value:${final_buy_hold:>12,.2f}  ({buy_hold_return_pct:+.2f}%)")

    # Count number of "trades" (signal transitions from 0 to 1)
    signal_transitions = (with_signals["signal"].diff() == 1).sum()
    print(f"Number of buy signals:   {signal_transitions}")


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