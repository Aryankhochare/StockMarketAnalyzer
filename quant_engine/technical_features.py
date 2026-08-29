import pandas as pd
import numpy as np

class TechnicalFeatureExtractor:
    """
    Vectorized quantitative technical feature extractor.
    Calculates moving averages, RSI, MACD, ATR, VWAP, Bollinger Bands,
    momentum, and volatility acceleration metrics.
    """
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.bfill().fillna(0.0)

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        volume = df['volume'].replace(0, 1.0)
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap.bfill().fillna(df['close'])

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adds all technical indicator features to the given DataFrame."""
        if df.empty or len(df) < 15:
            return df

        data = df.copy()
        close = data['close']
        
        # Returns & Momentum
        data['return_1d'] = close.pct_change(1).fillna(0.0)
        data['return_5d'] = close.pct_change(5).fillna(0.0)
        data['return_20d'] = close.pct_change(20).fillna(0.0)

        # Exponential Moving Averages
        data['ema_9'] = close.ewm(span=9, adjust=False).mean()
        data['ema_20'] = close.ewm(span=20, adjust=False).mean()
        data['ema_50'] = close.ewm(span=50, adjust=False).mean()
        data['ema_200'] = close.ewm(span=200, adjust=False).mean()

        # Distance from Moving Averages
        data['dist_ema_20'] = (close - data['ema_20']) / data['ema_20']
        data['dist_ema_50'] = (close - data['ema_50']) / data['ema_50']

        # Oscillators & Momentum
        data['rsi_14'] = self.calculate_rsi(close, 14)
        macd, macd_sig, macd_hist = self.calculate_macd(close)
        data['macd'] = macd
        data['macd_signal'] = macd_sig
        data['macd_hist'] = macd_hist

        # Volatility & ATR
        data['atr_14'] = self.calculate_atr(data, 14)
        data['atr_pct'] = data['atr_14'] / close

        # Bollinger Bands
        bb_middle = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        data['bb_upper'] = bb_middle + (2 * bb_std)
        data['bb_lower'] = bb_middle - (2 * bb_std)
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / bb_middle.replace(0, np.nan)
        data['bb_position'] = (close - data['bb_lower']) / (data['bb_upper'] - data['bb_lower']).replace(0, np.nan)

        # VWAP & Distance from VWAP
        data['vwap'] = self.calculate_vwap(data)
        data['dist_vwap'] = (close - data['vwap']) / data['vwap'].replace(0, np.nan)

        # Volume Acceleration
        vol = data['volume'].replace(0, 1.0)
        data['vol_sma_20'] = vol.rolling(window=20).mean()
        data['vol_ratio'] = vol / data['vol_sma_20'].replace(0, np.nan)

        # Rolling Volatility (20-period standard deviation of log returns)
        log_ret = np.log(close / close.shift(1).replace(0, np.nan))
        data['volatility_20d'] = log_ret.rolling(window=20).std().fillna(0.0)

        # Fill any remaining NaNs cleanly
        data = data.bfill().ffill().fillna(0.0)
        return data
