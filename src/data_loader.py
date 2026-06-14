"""
Data loader module.

Responsible for:
- Downloading historical stock price data from Yahoo Finance
- Storing it in a local SQLite database
- Loading it back as a pandas DataFrame for analysis
"""

import sqlite3
import yfinance as yf
import pandas as pd
from pathlib import Path
# Location of the SQLite database file
DB_PATH = Path(__file__).parent.parent / "data" / "prices.db"


def init_database():
    """
    Create the database file and the prices table if they don't exist yet.
    Safe to call multiple times - won't overwrite existing data.
    """
    # Make sure the data folder exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Open a connection to the database
    # If the file doesn't exist, SQLite creates it automatically
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)

    # Save changes and close the connection
    conn.commit()
    conn.close()

    print(f"Database ready at: {DB_PATH}")
def download_and_store(ticker: str, period: str = "5y"):
    """
    Download price data for a single ticker and store it in the database.

    Args:
        ticker: Stock symbol, e.g. "AAPL" or "0700.HK"
        period: How much history to pull. Common values:
                "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"
                Default is "5y" (5 years of history).
    """
    print(f"Downloading {ticker} for period={period}...")

    # Pull the data from Yahoo Finance
    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)

    # Safety check - bail out if we got nothing
    if data.empty:
        print(f"  No data returned for {ticker}. Skipping.")
        return

    # yfinance sometimes returns multi-level columns - flatten them
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Reset the index so 'Date' becomes a normal column instead of the index
    data = data.reset_index()

    # Add the ticker as a column so each row knows which stock it belongs to
    data["ticker"] = ticker

    # Rename the columns to match our database schema (lowercase)
    data = data.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    # Keep only the columns we want, in the right order
    data = data[["ticker", "date", "open", "high", "low", "close", "volume"]]

    # Convert the date column from a datetime object to a plain string
    data["date"] = data["date"].dt.strftime("%Y-%m-%d")

    # Open a database connection
    conn = sqlite3.connect(DB_PATH)

    # Delete any existing rows for this ticker (so we replace, not duplicate)
    conn.execute("DELETE FROM prices WHERE ticker = ?", (ticker,))

    # Insert all the new rows in one efficient operation
    data.to_sql("prices", conn, if_exists="append", index=False)

    # Save and close
    conn.commit()
    conn.close()

    print(f"  Stored {len(data)} rows for {ticker}")
def load_prices(ticker: str) -> pd.DataFrame:
    """
    Load all price data for a single ticker from the database.

    Args:
        ticker: Stock symbol, e.g. "AAPL"

    Returns:
        A pandas DataFrame indexed by date, with columns:
        open, high, low, close, volume
        Returns an empty DataFrame if the ticker isn't in the database.
    """
    # Open a connection
    conn = sqlite3.connect(DB_PATH)

    # Query the database
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE ticker = ?
        ORDER BY date
    """

    # Use pandas to run the query and load results directly into a DataFrame
    df = pd.read_sql_query(query, conn, params=(ticker,))

    # Close the connection
    conn.close()

    # Convert the date column back to a proper datetime type
    df["date"] = pd.to_datetime(df["date"])

    # Use date as the index (makes time-series operations easier later)
    df = df.set_index("date")

    return df
def bulk_download_and_store(tickers: list[str], period: str = "5y") -> dict:
    """
    Download and store price data for many tickers with error handling.

    Failed tickers are logged but don't stop the overall process.

    Args:
        tickers: List of ticker symbols to download.
        period: How much history to download (default 5 years).

    Returns:
        A summary dictionary:
            {
                "successful": [list of tickers that worked],
                "failed": [list of tickers that failed],
                "total": int
            }
    """
    init_database()

    successful = []
    failed = []
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        # Progress indicator — useful when downloading 500 stocks
        print(f"[{i:3d}/{total}] Downloading {ticker}...", end=" ")

        try:
            download_and_store(ticker, period=period)
            successful.append(ticker)
            print("OK")
        except Exception as e:
            failed.append(ticker)
            print(f"FAILED ({type(e).__name__})")

    # Summary
    print()
    print("=" * 60)
    print(f"Download complete: {len(successful)}/{total} successful")
    if failed:
        print(f"Failed tickers ({len(failed)}): {', '.join(failed[:20])}")
        if len(failed) > 20:
            print(f"  ...and {len(failed) - 20} more")
    print("=" * 60)

    return {
        "successful": successful,
        "failed": failed,
        "total": total,
    }