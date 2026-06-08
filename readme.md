# Stock Strategy Backtester

A Python-based tool for backtesting trading strategies against historical stock price data.

## Current Status

In active development. Phase 1 complete.

## Progress

- [x] **Phase 1: Data Pipeline** — Download and store 5-year price history for multiple tickers in SQLite
- [x] **Phase 2: Backtest Engine** — Moving average crossover strategy with look-ahead-bias-free returns
- [x] **Phase 3: Performance Metrics** — Sharpe ratio, max drawdown, win rate, profit factor
- [ ] Phase 4: Multiple Strategies — RSI, Bollinger Bands
- [ ] Phase 5: Interactive Dashboard — Streamlit interface
- [ ] Phase 6: Deployment

## Tech Stack

- Python 3.11
- Pandas, NumPy — data manipulation
- yfinance — historical price data
- SQLite — local data storage

## Setup

Clone the repository, create a virtual environment, install dependencies, and run.

    git clone https://github.com/jophyyung/stock-strategy-backtester.git
    cd stock-strategy-backtester
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

## Project Structure

    stock-strategy-backtester/
    ├── data/                  (SQLite database, gitignored)
    ├── src/
    │   ├── __init__.py
    │   └── data_loader.py     (download and storage logic)
    ├── main.py                (entry point)
    ├── requirements.txt
    └── README.md

## Features (Phase 1)

- Downloads historical OHLCV (Open, High, Low, Close, Volume) data via yfinance
- Stores data in a local SQLite database with a composite primary key (ticker + date) to prevent duplicates
- Supports multiple tickers across US and Hong Kong markets (AAPL, MSFT, GOOGL, 0700.HK, 0005.HK)
- Idempotent design — safe to re-run; refreshes existing data without creating duplicates
- Adjusted prices (handles stock splits and dividends automatically)
## Features (Phase 2)

- Implements the classic 50/200-day moving average crossover strategy ("golden cross" / "death cross")
- Backtests strategies on historical data with proper look-ahead bias prevention (signal shifting)
- Computes equity curve, daily returns, and trade count
- Compares strategy performance against a buy-and-hold benchmark
- Modular design: strategy logic and simulation logic are separated for easy extension
## Features (Phase 3)

- Computes industry-standard quantitative performance metrics from any backtest:
  - Total return and annualised return (CAGR)
  - Annualised volatility (using square-root-of-time scaling)
  - Annualised Sharpe ratio
  - Maximum drawdown (peak-to-trough loss)
  - Trade-level statistics: win rate, average win, average loss, profit factor
- All metrics computed cleanly from the backtest output with proper guard clauses against edge cases (zero volatility, zero trades).
- Strategy and buy-and-hold benchmark are compared side-by-side in the main output.

## About

Built as a personal project to apply quantitative coursework (Probability, Statistics, Optimization Methods) to real financial market data.

Jophy Yung — BSc Financial Technology, CUHK