import pandas as pd
import pandas_ta as ta
import numpy as np
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pytz
from .base import data_client

def get_stock_features(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch stock data and calculate features for ML model to predict price.
    Returns DataFrame with OHLCV, technical indicators, and target (next day's close).
    """
    end_date = datetime(2024, 12, 31, tzinfo=pytz.UTC)
    start_date = end_date - timedelta(days=days)
    
    request = StockBarsRequest(
        symbol_or_symbols=symbol.upper(),
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )
    
    bars = data_client.get_stock_bars(request)
    if bars is None or bars.df is None:
        return pd.DataFrame()
    df = bars.df.copy()
    
    if df.empty:
        return pd.DataFrame()
    
    # Basic price features
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close']).diff()
    
    # Volume features
    df['volume_sma_20'] = ta.sma(df['volume'], length=20)
    df['volume_ratio'] = df['volume'] / df['volume_sma_20']
    
    # Trend indicators
    try:
        df['SMA_10'] = ta.sma(df['close'], length=min(10, len(df)))
        df['SMA_20'] = ta.sma(df['close'], length=min(20, len(df)))
        df['SMA_50'] = ta.sma(df['close'], length=min(50, len(df)))
        df['EMA_12'] = ta.ema(df['close'], length=min(12, len(df)))
        df['EMA_26'] = ta.ema(df['close'], length=min(26, len(df)))
    except Exception:
        pass  # Skip if calculation fails
    
    # Momentum indicators
    try:
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['RSI_7'] = ta.rsi(df['close'], length=7)
        df['RSI_21'] = ta.rsi(df['close'], length=21)
    except Exception:
        pass
    
    # MACD
    try:
        macd = ta.macd(df['close'])
        if macd is not None:
            df['MACD'] = macd['MACD']
            df['MACD_signal'] = macd['MACDs']
            df['MACD_hist'] = macd['MACDh']
    except Exception:
        pass
    
    # Bollinger Bands
    try:
        bb = ta.bbands(df['close'], length=20)
        if bb is not None:
            df['BB_upper'] = bb['BBU_20_2.0']
            df['BB_middle'] = bb['BBM_20_2.0']
            df['BB_lower'] = bb['BBL_20_2.0']
            df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
    except Exception:
        pass
    
    # Volatility
    try:
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['volatility'] = df['returns'].rolling(20).std()
    except Exception:
        pass
    
    # Stochastic Oscillator
    try:
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None:
            df['stoch_k'] = stoch['STOCHk_14_3_3']
            df['stoch_d'] = stoch['STOCHd_14_3_3']
    except Exception:
        pass
    
    # Williams %R
    try:
        df['williams_r'] = ta.willr(df['high'], df['low'], df['close'], length=14)
    except Exception:
        pass
    
    # On-Balance Volume
    try:
        df['obv'] = ta.obv(df['close'], df['volume'])
    except Exception:
        pass
    
    # Target: next day's close price (shifted)
    df['target'] = df['close'].shift(-1)
    
    # Note: Not dropping NaN to preserve data for short periods
    return df