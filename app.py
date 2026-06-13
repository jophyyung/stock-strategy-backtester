"""
Stock Strategy Backtester — Streamlit dashboard.
Launch with: streamlit run app.py
"""

from pathlib import Path
import streamlit as st
import pandas as pd

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
    trade_stats,
)

from pathlib import Path
from src.data_loader import init_database, download_and_store

# Bootstrap: if no database exists, create one with default tickers
DB_PATH = Path(__file__).parent / "data" / "prices.db"
if not DB_PATH.exists():
    init_database()
    for t in ["AAPL", "MSFT", "GOOGL", "0700.HK", "0005.HK"]:
        download_and_store(t, period="5y")
# ── Page setup ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Strategy Backtester",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Strategy Backtester")
st.markdown(
    "A quantitative backtesting tool for trading strategies on US and HK equities. "
    "Built by [Jophy Yung](https://github.com/jophyyung/stock-strategy-backtester)."
)


# ── Bootstrap database if missing (for cloud deployment) ──────────────────
DB_PATH = Path(__file__).parent / "data" / "prices.db"
if not DB_PATH.exists():
    with st.spinner("First-time setup: downloading market data..."):
        init_database()
        for t in ["AAPL", "MSFT", "GOOGL", "0700.HK", "0005.HK"]:
            download_and_store(t, period="5y")
    st.success("Setup complete. Dashboard ready.")


# ── Sidebar controls ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    ticker = st.selectbox(
        "Select ticker",
        options=["AAPL", "MSFT", "GOOGL", "0700.HK", "0005.HK"],
        index=0,
    )

    strategy = st.selectbox(
        "Select strategy",
        options=[
            "Moving Average Crossover",
            "RSI Mean Reversion",
            "Bollinger Bands",
        ],
        index=0,
    )

    st.markdown("---")
    st.subheader("Strategy Parameters")

    if strategy == "Moving Average Crossover":
        short_window = st.slider("Short MA window (days)", 5, 100, 50, 5)
        long_window = st.slider("Long MA window (days)", 50, 300, 200, 10)
        params = {"short_window": short_window, "long_window": long_window}

    elif strategy == "RSI Mean Reversion":
        rsi_window = st.slider("RSI window (days)", 5, 50, 14, 1)
        oversold = st.slider("Oversold threshold", 10, 40, 30, 1)
        overbought = st.slider("Overbought threshold", 60, 90, 70, 1)
        params = {
            "rsi_window": rsi_window,
            "oversold_threshold": float(oversold),
            "overbought_threshold": float(overbought),
        }

    elif strategy == "Bollinger Bands":
        bb_window = st.slider("Window (days)", 5, 60, 20, 1)
        bb_num_std = st.slider("Number of standard deviations", 1.0, 3.0, 2.0, 0.1)
        params = {"window": bb_window, "num_std": bb_num_std}

    st.markdown("---")
    initial_capital = st.number_input(
        "Initial capital (HK$ / US$)",
        min_value=1000,
        max_value=10_000_000,
        value=10_000,
        step=1000,
    )


# ── Cached data loading and backtest pipeline ─────────────────────────────
@st.cache_data
def load_data(ticker):
    """Load prices for a ticker. Cached so we don't re-query SQLite on every rerun."""
    return load_prices(ticker)


@st.cache_data
def compute_backtest(ticker, strategy, params_tuple, initial_capital):
    """Apply strategy + run backtest. Cached on all inputs."""
    prices = load_data(ticker)
    params = dict(params_tuple)

    if strategy == "Moving Average Crossover":
        with_signals = moving_average_crossover(prices, **params)
    elif strategy == "RSI Mean Reversion":
        with_signals = rsi_mean_reversion(prices, **params)
    elif strategy == "Bollinger Bands":
        with_signals = bollinger_bands(prices, **params)

    return run_backtest(with_signals, initial_capital=initial_capital)


# Run the pipeline
prices = load_data(ticker)
if prices.empty:
    st.error(f"No data found for {ticker}. Try running main.py to download data first.")
    st.stop()

params_tuple = tuple(sorted(params.items()))
results = compute_backtest(ticker, strategy, params_tuple, initial_capital)


# ── Main panel ────────────────────────────────────────────────────────────
st.markdown("---")

# Summary header
col1, col2, col3 = st.columns(3)
col1.metric("Ticker", ticker)
col2.metric("Strategy", strategy)
col3.metric(
    "Period",
    f"{results.index.min().date()} → {results.index.max().date()}",
)

st.markdown("---")


# ── Chart 1: Equity Curve ─────────────────────────────────────────────────
st.subheader("📊 Equity Curve — Strategy vs Buy-and-Hold")

equity_df = pd.DataFrame(
    {
        "Strategy": results["equity"],
        "Buy-and-Hold": results["buy_hold_equity"],
    }
)
st.line_chart(equity_df, height=400)


# ── Chart 2: Price with Indicators ────────────────────────────────────────
st.subheader(f"💹 {ticker} Price with Indicator")

price_df = pd.DataFrame({"Close": results["close"]})

if strategy == "Moving Average Crossover":
    price_df["Short MA"] = results["short_ma"]
    price_df["Long MA"] = results["long_ma"]

elif strategy == "Bollinger Bands":
    price_df["Middle"] = results["bb_middle"]
    price_df["Upper"] = results["bb_upper"]
    price_df["Lower"] = results["bb_lower"]

st.line_chart(price_df, height=400)

# RSI chart shown separately (different y-axis scale)
if strategy == "RSI Mean Reversion":
    st.subheader("RSI Indicator")
    rsi_df = pd.DataFrame({"RSI": results["rsi"]})
    st.line_chart(rsi_df, height=250)


# ── Performance Metrics ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Performance Metrics")

strategy_returns = results["strategy_return"].dropna()
bh_returns = results["return"].dropna()


def fmt_pct(value):
    """Format a decimal as a signed percentage."""
    return f"{value * 100:+.2f}%"


# Strategy metrics
st.markdown(f"##### Strategy: {strategy}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Return", fmt_pct(total_return(results["equity"])))
c2.metric("Annualised Return", fmt_pct(annualised_return(results["equity"])))
c3.metric("Annualised Vol", fmt_pct(annualised_volatility(strategy_returns)))
c4.metric("Sharpe Ratio", f"{sharpe_ratio(strategy_returns):.2f}")
c5.metric("Max Drawdown", fmt_pct(max_drawdown(results["equity"])))

# Benchmark metrics
st.markdown("##### Benchmark: Buy-and-Hold")
b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("Total Return", fmt_pct(total_return(results["buy_hold_equity"])))
b2.metric("Annualised Return", fmt_pct(annualised_return(results["buy_hold_equity"])))
b3.metric("Annualised Vol", fmt_pct(annualised_volatility(bh_returns)))
b4.metric("Sharpe Ratio", f"{sharpe_ratio(bh_returns):.2f}")
b5.metric("Max Drawdown", fmt_pct(max_drawdown(results["buy_hold_equity"])))


# ── Trade statistics ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("##### Trade Statistics")

stats = trade_stats(strategy_returns, results["signal"])
t1, t2, t3, t4, t5 = st.columns(5)
t1.metric("Number of Trades", count_trades(results["signal"]))
t2.metric("Win Rate", f"{stats['win_rate'] * 100:.1f}%")
t3.metric("Avg Win", fmt_pct(stats["avg_win"]))
t4.metric("Avg Loss", fmt_pct(stats["avg_loss"]))
t5.metric(
    "Profit Factor",
    f"{stats['profit_factor']:.2f}" if stats["profit_factor"] != float("inf") else "∞",
)


# ── Quick Read ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("##### Quick Read")

strategy_sharpe = sharpe_ratio(strategy_returns)
bh_sharpe = sharpe_ratio(bh_returns)
sharpe_diff = strategy_sharpe - bh_sharpe

if sharpe_diff > 0.1:
    st.success(
        f"The {strategy} strategy outperformed buy-and-hold on a risk-adjusted basis "
        f"(Sharpe +{sharpe_diff:.2f})."
    )
elif sharpe_diff > -0.1:
    st.info(
        f"The {strategy} strategy performed roughly in line with buy-and-hold "
        f"(Sharpe difference: {sharpe_diff:+.2f})."
    )
else:
    st.warning(
        f"The {strategy} strategy underperformed buy-and-hold on a risk-adjusted basis "
        f"(Sharpe {sharpe_diff:+.2f})."
    )