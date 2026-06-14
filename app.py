"""
Stock Strategy Backtester & Screener — Streamlit dashboard.
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
from src.screener import (
    get_all_tickers_in_db,
    screen_rsi,
    screen_ma_crossover,
    screen_bollinger,
)


# ── Page setup ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Strategy Backtester",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Strategy Backtester")
st.markdown(
    "A quantitative backtesting and screening tool for US and HK equities. "
    "Built by [Jophy Yung](https://github.com/jophyyung/stock-strategy-backtester)."
)


# ── Bootstrap database if missing ─────────────────────────────────────────
DB_PATH = Path(__file__).parent / "data" / "prices.db"
if not DB_PATH.exists():
    with st.spinner("First-time setup: downloading market data..."):
        init_database()
        for t in ["AAPL", "MSFT", "GOOGL", "0700.HK", "0005.HK"]:
            download_and_store(t, period="5y")
    st.success("Setup complete. Dashboard ready.")


# ── Tab navigation ────────────────────────────────────────────────────────
tab_backtest, tab_screener = st.tabs(["🔬 Backtester", "🔍 Screener"])


# ═════════════════════════════════════════════════════════════════════════
# TAB 1: BACKTESTER (existing functionality)
# ═════════════════════════════════════════════════════════════════════════
with tab_backtest:

    # ── Sidebar-like controls in the tab ──────────────────────────────────
    col_controls, col_charts = st.columns([1, 3])

    with col_controls:
        st.subheader("⚙️ Configuration")

        all_tickers = get_all_tickers_in_db()
        if not all_tickers:
            all_tickers = ["AAPL", "MSFT", "GOOGL", "0700.HK", "0005.HK"]

        ticker = st.selectbox(
            "Select ticker",
            options=all_tickers,
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

        st.markdown("**Strategy Parameters**")

        if strategy == "Moving Average Crossover":
            short_window = st.slider("Short MA", 5, 100, 50, 5)
            long_window = st.slider("Long MA", 50, 300, 200, 10)
            params = {"short_window": short_window, "long_window": long_window}

        elif strategy == "RSI Mean Reversion":
            rsi_window = st.slider("RSI window", 5, 50, 14, 1)
            oversold = st.slider("Oversold", 10, 40, 30, 1)
            overbought = st.slider("Overbought", 60, 90, 70, 1)
            params = {
                "rsi_window": rsi_window,
                "oversold_threshold": float(oversold),
                "overbought_threshold": float(overbought),
            }

        elif strategy == "Bollinger Bands":
            bb_window = st.slider("Window", 5, 60, 20, 1)
            bb_num_std = st.slider("# Std Dev", 1.0, 3.0, 2.0, 0.1)
            params = {"window": bb_window, "num_std": bb_num_std}

        initial_capital = st.number_input(
            "Initial capital",
            min_value=1000,
            max_value=10_000_000,
            value=10_000,
            step=1000,
        )

    # ── Cached pipeline ────────────────────────────────────────────────────
    @st.cache_data
    def load_data(ticker):
        return load_prices(ticker)

    @st.cache_data
    def compute_backtest(ticker, strategy, params_tuple, initial_capital):
        prices = load_data(ticker)
        params = dict(params_tuple)

        if strategy == "Moving Average Crossover":
            with_signals = moving_average_crossover(prices, **params)
        elif strategy == "RSI Mean Reversion":
            with_signals = rsi_mean_reversion(prices, **params)
        elif strategy == "Bollinger Bands":
            with_signals = bollinger_bands(prices, **params)

        return run_backtest(with_signals, initial_capital=initial_capital)

    prices = load_data(ticker)

    if prices.empty:
        with col_charts:
            st.error(f"No data found for {ticker}.")
    else:
        params_tuple = tuple(sorted(params.items()))
        results = compute_backtest(ticker, strategy, params_tuple, initial_capital)

        with col_charts:
            # Summary
            c1, c2, c3 = st.columns(3)
            c1.metric("Ticker", ticker)
            c2.metric("Strategy", strategy)
            c3.metric(
                "Period",
                f"{results.index.min().date()} → {results.index.max().date()}",
            )

            # Equity curve
            st.subheader("📊 Equity Curve")
            equity_df = pd.DataFrame({
                "Strategy": results["equity"],
                "Buy-and-Hold": results["buy_hold_equity"],
            })
            st.line_chart(equity_df, height=350)

            # Price with indicators
            st.subheader(f"💹 {ticker} Price")
            price_df = pd.DataFrame({"Close": results["close"]})

            if strategy == "Moving Average Crossover":
                price_df["Short MA"] = results["short_ma"]
                price_df["Long MA"] = results["long_ma"]
            elif strategy == "Bollinger Bands":
                price_df["Middle"] = results["bb_middle"]
                price_df["Upper"] = results["bb_upper"]
                price_df["Lower"] = results["bb_lower"]

            st.line_chart(price_df, height=350)

            if strategy == "RSI Mean Reversion":
                st.subheader("RSI")
                st.line_chart(pd.DataFrame({"RSI": results["rsi"]}), height=200)

        # Metrics below the columns
        st.markdown("---")
        st.subheader("📋 Performance Metrics")

        strategy_returns = results["strategy_return"].dropna()
        bh_returns = results["return"].dropna()

        def fmt_pct(value):
            return f"{value * 100:+.2f}%"

        st.markdown(f"##### Strategy: {strategy}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Return", fmt_pct(total_return(results["equity"])))
        m2.metric("Annualised", fmt_pct(annualised_return(results["equity"])))
        m3.metric("Volatility", fmt_pct(annualised_volatility(strategy_returns)))
        m4.metric("Sharpe", f"{sharpe_ratio(strategy_returns):.2f}")
        m5.metric("Max Drawdown", fmt_pct(max_drawdown(results["equity"])))

        st.markdown("##### Buy-and-Hold")
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.metric("Total Return", fmt_pct(total_return(results["buy_hold_equity"])))
        b2.metric("Annualised", fmt_pct(annualised_return(results["buy_hold_equity"])))
        b3.metric("Volatility", fmt_pct(annualised_volatility(bh_returns)))
        b4.metric("Sharpe", f"{sharpe_ratio(bh_returns):.2f}")
        b5.metric("Max Drawdown", fmt_pct(max_drawdown(results["buy_hold_equity"])))

        # Trade stats
        st.markdown("##### Trade Statistics")
        stats = trade_stats(strategy_returns, results["signal"])
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("Trades", count_trades(results["signal"]))
        t2.metric("Win Rate", f"{stats['win_rate'] * 100:.1f}%")
        t3.metric("Avg Win", fmt_pct(stats["avg_win"]))
        t4.metric("Avg Loss", fmt_pct(stats["avg_loss"]))
        t5.metric(
            "Profit Factor",
            f"{stats['profit_factor']:.2f}" if stats["profit_factor"] != float("inf") else "∞",
        )


# ═════════════════════════════════════════════════════════════════════════
# TAB 2: SCREENER (new)
# ═════════════════════════════════════════════════════════════════════════
with tab_screener:

    st.subheader("🔍 Stock Screener")
    st.markdown(
        "Scan all stocks in the database against technical filters to find "
        "candidates matching your criteria. Results are **starting points** "
        "for further research, not buy recommendations."
    )

    all_tickers_screener = get_all_tickers_in_db()
    st.info(f"📊 {len(all_tickers_screener)} stocks currently in the database")

    # ── Filter selection ──────────────────────────────────────────────────
    filter_type = st.selectbox(
        "Select filter",
        options=[
            "RSI Oversold (RSI below threshold)",
            "RSI Overbought (RSI above threshold)",
            "Recent Golden Cross (MA short crossed above long)",
            "Below Bollinger Lower Band",
            "Above Bollinger Upper Band",
        ],
    )

    # ── Filter-specific controls ──────────────────────────────────────────
    col_a, col_b = st.columns(2)

    if "RSI" in filter_type:
        with col_a:
            rsi_threshold = st.slider("RSI threshold", 10, 90, 30, 1)
        with col_b:
            rsi_window_sc = st.slider("RSI window (days)", 5, 50, 14, 1)

    elif "Golden Cross" in filter_type:
        with col_a:
            short_w = st.slider("Short MA", 5, 100, 50, 5)
            lookback = st.slider("Lookback days", 1, 30, 5, 1)
        with col_b:
            long_w = st.slider("Long MA", 50, 300, 200, 10)

    elif "Bollinger" in filter_type:
        with col_a:
            bb_window_sc = st.slider("Window", 5, 60, 20, 1)
        with col_b:
            bb_std_sc = st.slider("# Std Dev", 1.0, 3.0, 2.0, 0.1)

    # ── Run scan button ────────────────────────────────────────────────────
    if st.button("🚀 Run Scan", type="primary"):
        with st.spinner("Scanning all stocks..."):
            if filter_type.startswith("RSI Oversold"):
                results_df = screen_rsi(
                    threshold=rsi_threshold,
                    direction="below",
                    rsi_window=rsi_window_sc,
                )
            elif filter_type.startswith("RSI Overbought"):
                results_df = screen_rsi(
                    threshold=rsi_threshold,
                    direction="above",
                    rsi_window=rsi_window_sc,
                )
            elif filter_type.startswith("Recent Golden Cross"):
                results_df = screen_ma_crossover(
                    short_window=short_w,
                    long_window=long_w,
                    lookback_days=lookback,
                )
            elif filter_type.startswith("Below Bollinger Lower"):
                results_df = screen_bollinger(
                    position="below_lower",
                    window=bb_window_sc,
                    num_std=bb_std_sc,
                )
            elif filter_type.startswith("Above Bollinger Upper"):
                results_df = screen_bollinger(
                    position="above_upper",
                    window=bb_window_sc,
                    num_std=bb_std_sc,
                )

        if results_df.empty:
            st.warning("No stocks match the current criteria.")
        else:
            st.success(f"Found {len(results_df)} matching stocks")
            st.dataframe(
                results_df,
                use_container_width=True,
                hide_index=False,
            )

            # Download as CSV
            csv = results_df.to_csv(index=False)
            st.download_button(
                "📥 Download as CSV",
                csv,
                f"screener_results_{filter_type[:20]}.csv",
                "text/csv",
            )

    st.markdown("---")
    st.caption(
        "⚠️ Disclaimer: This screener identifies stocks matching technical "
        "criteria. Results are for educational and research purposes only. "
        "Always do additional analysis before considering any investment."
    )