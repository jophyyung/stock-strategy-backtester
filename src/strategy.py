"""
Strategy module.

Implements trading strategies that take historical price data
and produce buy/sell signals based on technical indicators.

Current strategies:
- Moving Average Crossover (golden/death cross)
"""

import pandas as pd

def moving_average_crossover(
    prices: pd.DataFrame,
    short_window: int = 50,
    long_window: int = 200
) -> pd.DataFrame:
    """
    Compute moving average crossover signals.

    A 'golden cross' occurs when the short MA crosses above the long MA (buy signal).
    A 'death cross' occurs when the short MA crosses below the long MA (sell signal).

    Args:
        prices: DataFrame with at least a 'close' column, indexed by date.
        short_window: Lookback period for the short moving average (default 50 days).
        long_window: Lookback period for the long moving average (default 200 days).

    Returns:
        A new DataFrame (copy of input) with these added columns:
        - short_ma: Short moving average
        - long_ma: Long moving average
        - signal: 1 when short_ma > long_ma (in market), else 0 (out of market)
    """
    # Sanity check the inputs
    if short_window >= long_window:
        raise ValueError(
            f"short_window ({short_window}) must be less than long_window ({long_window})"
        )

    # Work on a copy so we don't mutate the caller's DataFrame
    df = prices.copy()

    # Compute the moving averages on the closing price
    df["short_ma"] = df["close"].rolling(window=short_window).mean()
    df["long_ma"] = df["close"].rolling(window=long_window).mean()

    # Generate the signal
    # When short_ma > long_ma, we want to be in the market (signal = 1)
    # Otherwise, we want to be out of the market (signal = 0)
    df["signal"] = (df["short_ma"] > df["long_ma"]).astype(int)

    return df
def rsi_mean_reversion(
    prices: pd.DataFrame,
    rsi_window: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
) -> pd.DataFrame:
    """
    Compute RSI-based mean reversion signals.

    The RSI (Relative Strength Index) is a momentum oscillator that measures
    the speed and magnitude of recent price changes. It ranges from 0 to 100.

    Trading logic:
    - When RSI crosses below the oversold threshold, enter the market (signal=1)
    - When RSI crosses above the overbought threshold, exit the market (signal=0)
    - Between signals, hold the previous position

    Args:
        prices: DataFrame with at least a 'close' column, indexed by date.
        rsi_window: Lookback period for RSI calculation (default 14 days).
        oversold_threshold: RSI level below which we enter long (default 30).
        overbought_threshold: RSI level above which we exit (default 70).

    Returns:
        A new DataFrame (copy of input) with these added columns:
        - rsi: Computed RSI values (0-100)
        - signal: 1 when in market, 0 when out of market
    """
    # Sanity check the thresholds
    if oversold_threshold >= overbought_threshold:
        raise ValueError(
            f"oversold_threshold ({oversold_threshold}) must be less than "
            f"overbought_threshold ({overbought_threshold})"
        )

    # Work on a copy so we don't mutate the caller's DataFrame
    df = prices.copy()

    # Step 1: Compute daily price changes
    delta = df["close"].diff()

    # Step 2: Split changes into gains and losses
    # Gains are positive changes (losses are zero); losses are absolute negative changes
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Step 3: Compute rolling average of gains and losses
    avg_gain = gains.rolling(window=rsi_window).mean()
    avg_loss = losses.rolling(window=rsi_window).mean()

    # Step 4: Compute RS and RSI
    # Guard against divide-by-zero (no losses → infinite RS → RSI of 100)
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # Step 5: Generate signals from RSI
    # Build the signal column day by day, holding the previous position when
    # there's no clear signal
    signal = pd.Series(0, index=df.index)
    in_position = 0

    for i in range(len(df)):
        rsi_value = df["rsi"].iloc[i]

        if pd.isna(rsi_value):
            # Not enough history yet, stay out of market
            signal.iloc[i] = 0
            continue

        if rsi_value < oversold_threshold:
            in_position = 1  # Oversold → buy / hold
        elif rsi_value > overbought_threshold:
            in_position = 0  # Overbought → sell / stay out

        # Otherwise (in the neutral zone), hold the previous position
        signal.iloc[i] = in_position

    df["signal"] = signal

    return df
def bollinger_bands(
    prices: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """
    Compute Bollinger Band-based mean reversion signals.

    Bollinger Bands plot a moving average with bands at +/- num_std standard
    deviations above and below. Prices touching the lower band are considered
    unusually cheap (buy signal); prices at the upper band are unusually
    expensive (sell signal).

    Trading logic:
    - When close crosses below the lower band, enter the market (signal=1)
    - When close crosses above the upper band, exit the market (signal=0)
    - Between bands, hold the previous position

    Args:
        prices: DataFrame with at least a 'close' column, indexed by date.
        window: Lookback period for the moving average and standard deviation
                (default 20 days).
        num_std: Number of standard deviations for the bands (default 2.0).

    Returns:
        A new DataFrame (copy of input) with these added columns:
        - bb_middle: The middle band (moving average)
        - bb_upper: The upper band
        - bb_lower: The lower band
        - signal: 1 when in market, 0 when out of market
    """
    # Sanity check
    if num_std <= 0:
        raise ValueError(f"num_std must be positive, got {num_std}")

    # Work on a copy
    df = prices.copy()

    # Compute the middle band (simple moving average)
    df["bb_middle"] = df["close"].rolling(window=window).mean()

    # Compute the rolling standard deviation
    rolling_std = df["close"].rolling(window=window).std()

    # Compute the upper and lower bands
    df["bb_upper"] = df["bb_middle"] + (num_std * rolling_std)
    df["bb_lower"] = df["bb_middle"] - (num_std * rolling_std)

    # Generate signals
    # Build the signal column day by day, holding the previous position when
    # there's no clear signal
    signal = pd.Series(0, index=df.index)
    in_position = 0

    for i in range(len(df)):
        close = df["close"].iloc[i]
        upper = df["bb_upper"].iloc[i]
        lower = df["bb_lower"].iloc[i]

        if pd.isna(upper) or pd.isna(lower):
            # Not enough history yet, stay out of market
            signal.iloc[i] = 0
            continue

        if close < lower:
            in_position = 1  # Below lower band → buy / hold
        elif close > upper:
            in_position = 0  # Above upper band → sell / stay out

        # Otherwise (between bands), hold the previous position
        signal.iloc[i] = in_position

    df["signal"] = signal

    return df