"""
Main entry point for the stock backtester.

Phase 1: Data Pipeline
Downloads historical stock data for a set of tickers
and stores it in a local SQLite database.
"""

from src.data_loader import init_database, download_and_store, load_prices


def main():
    # Step 1: Make sure the database and table exist
    print("=" * 60)
    print("Setting up database...")
    print("=" * 60)
    init_database()

    # Step 2: Download data for a list of tickers
    print()
    print("=" * 60)
    print("Downloading stock data...")
    print("=" * 60)

    tickers = [
        "AAPL",      # Apple - US tech
        "MSFT",      # Microsoft - US tech
        "GOOGL",     # Alphabet (Google) - US tech
        "0700.HK",   # Tencent - Hong Kong tech
        "0005.HK",   # HSBC - Hong Kong banking
    ]

    for ticker in tickers:
        download_and_store(ticker, period="5y")

    # Step 3: Sanity check - load one back and show the most recent prices
    print()
    print("=" * 60)
    print("Verification: most recent AAPL prices")
    print("=" * 60)

    df = load_prices("AAPL")
    print(df.tail(10))
    print()
    print(f"Total rows for AAPL: {len(df)}")
    print(f"Date range: {df.index.min().date()} to {df.index.max().date()}")


if __name__ == "__main__":
    main()