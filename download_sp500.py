"""
One-time script to download all S&P 500 stocks into the local database.

Run with: python download_sp500.py
"""

from src.universe import get_sp500_tickers
from src.data_loader import bulk_download_and_store


print("Fetching current S&P 500 ticker list...")
tickers = get_sp500_tickers()
print(f"Got {len(tickers)} tickers.")
print()

print(f"Starting bulk download (this will take 15-30 minutes)...")
print()

result = bulk_download_and_store(tickers, period="5y")

print()
print(f"Done. {len(result['successful'])} stocks now in database.")