"""
Universe module.

Provides functions to retrieve lists of stock tickers
(e.g. the S&P 500 constituents) from public sources.
"""

import io
import urllib.request

import pandas as pd


SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Wikipedia blocks requests without a proper User-Agent header,
# so we set one that identifies us as a normal browser-like client
USER_AGENT = (
    "Mozilla/5.0 (compatible; StockBacktester/1.0; "
    "+https://github.com/jophyyung/stock-strategy-backtester)"
)


def _fetch_wikipedia_html(url: str) -> str:
    """Fetch HTML content from a Wikipedia URL with a proper User-Agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def get_sp500_tickers() -> list[str]:
    """
    Fetch the current list of S&P 500 ticker symbols from Wikipedia.

    Returns:
        A list of ticker symbols (e.g. ['AAPL', 'MSFT', 'GOOGL', ...]).
        Tickers with dots (like 'BRK.B') are converted to dashes ('BRK-B')
        because that's the format yfinance expects.

    Raises:
        Exception: if the Wikipedia page cannot be reached or parsed.
    """
    html = _fetch_wikipedia_html(SP500_WIKI_URL)
    tables = pd.read_html(io.StringIO(html))
    sp500_table = tables[0]

    tickers = sp500_table["Symbol"].tolist()
    tickers = [t.replace(".", "-") for t in tickers]

    return tickers


def get_sp500_companies() -> pd.DataFrame:
    """
    Fetch the full S&P 500 constituent table with company names, sectors,
    and other metadata.

    Returns:
        DataFrame with columns including Symbol, Security, GICS Sector,
        GICS Sub-Industry, Headquarters Location, etc.
    """
    html = _fetch_wikipedia_html(SP500_WIKI_URL)
    tables = pd.read_html(io.StringIO(html))
    df = tables[0]

    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)

    return df