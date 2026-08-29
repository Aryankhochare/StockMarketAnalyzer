import pandas as pd
import numpy as np
from typing import Dict, Any

class CandlestickPatternExtractor:
    """
    Exhaustive Quantitative Candlestick Microstructure & Pattern Extractor.
    Computes continuous geometric ratios (prevents overfitting) and identifies
    major single, dual, and triple candlestick price action patterns.
    """

    def compute_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 5:
            return df

        data = df.copy()
        open_p = data['open']
        high = data['high']
        low = data['low']
        close = data['close']

        # 1. Continuous Geometric Microstructure Ratios (Prevents Overfitting)
        total_range = (high - low).replace(0, np.nan)
        body = (close - open_p).abs()
        
        data['body_ratio'] = (body / total_range).fillna(0.0).clip(0.0, 1.0)
        data['upper_wick_ratio'] = ((high - data[['open', 'close']].max(axis=1)) / total_range).fillna(0.0).clip(0.0, 1.0)
        data['lower_wick_ratio'] = ((data[['open', 'close']].min(axis=1) - low) / total_range).fillna(0.0).clip(0.0, 1.0)
        
        # Range Expansion vs 20-period ATR
        atr = data.get('atr_14', total_range.rolling(14).mean()).replace(0, np.nan)
        data['range_expansion_ratio'] = (total_range / atr).fillna(1.0)

        # Consecutive Momentum Streak
        is_green = (close > open_p).astype(int)
        is_red = (close < open_p).astype(int)
        
        streak = pd.Series(0, index=data.index)
        cur_streak = 0
        for idx in range(len(data)):
            if is_green.iloc[idx]:
                cur_streak = cur_streak + 1 if cur_streak > 0 else 1
            elif is_red.iloc[idx]:
                cur_streak = cur_streak - 1 if cur_streak < 0 else -1
            else:
                cur_streak = 0
            streak.iloc[idx] = cur_streak
        data['consecutive_streak'] = streak

        # 2. Pattern Classification Flags (-1.0 Bearish, 0.0 Neutral, +1.0 Bullish)
        pattern_score = pd.Series(0.0, index=data.index)

        # Prev Candle Shifts
        prev_open = open_p.shift(1)
        prev_close = close.shift(1)
        prev_body = (prev_close - prev_open).abs()

        prev2_open = open_p.shift(2)
        prev2_close = close.shift(2)

        for i in range(2, len(data)):
            score = 0.0
            b_ratio = data['body_ratio'].iloc[i]
            u_ratio = data['upper_wick_ratio'].iloc[i]
            l_ratio = data['lower_wick_ratio'].iloc[i]
            
            c_close = close.iloc[i]
            c_open = open_p.iloc[i]
            p_close = prev_close.iloc[i]
            p_open = prev_open.iloc[i]

            # Single Candle Patterns
            # Marubozu (Strong Conviction)
            if b_ratio > 0.85:
                score += 0.4 if c_close > c_open else -0.4

            # Hammer / Pin Bar (Buying Demand Rejection Tail)
            if l_ratio > 0.60 and b_ratio < 0.30:
                score += 0.5

            # Shooting Star (Overhead Selling Rejection)
            if u_ratio > 0.60 and b_ratio < 0.30:
                score -= 0.5

            # Two Candle Patterns
            # Bullish Engulfing
            if (p_close < p_open) and (c_close > c_open) and (c_close >= p_open) and (c_open <= p_close):
                score += 0.6

            # Bearish Engulfing
            if (p_close > p_open) and (c_close < c_open) and (c_close <= p_open) and (c_open >= p_close):
                score -= 0.6

            # Piercing Line / Dark Cloud Cover
            if (p_close < p_open) and (c_close > c_open) and (c_open < p_close) and (c_close > (p_open + p_close)/2):
                score += 0.45

            if (p_close > p_open) and (c_close < c_open) and (c_open > p_close) and (c_close < (p_open + p_close)/2):
                score -= 0.45

            # Inside Bar Breakout
            if (high.iloc[i] < high.iloc[i-1]) and (low.iloc[i] > low.iloc[i-1]):
                score += 0.2 if c_close > c_open else -0.2

            # Three Candle Patterns
            # Morning Star
            if (prev2_close.iloc[i] < prev2_open.iloc[i]) and (prev_body.iloc[i] < (high.iloc[i-1]-low.iloc[i-1])*0.3) and (c_close > c_open) and (c_close > (prev2_open.iloc[i] + prev2_close.iloc[i])/2):
                score += 0.7

            # Evening Star
            if (prev2_close.iloc[i] > prev2_open.iloc[i]) and (prev_body.iloc[i] < (high.iloc[i-1]-low.iloc[i-1])*0.3) and (c_close < c_open) and (c_close < (prev2_open.iloc[i] + prev2_close.iloc[i])/2):
                score -= 0.7

            pattern_score.iloc[i] = max(-1.0, min(1.0, score))

        data['candle_pattern_score'] = pattern_score.fillna(0.0)
        return data

# Global Instance
candlestick_extractor = CandlestickPatternExtractor()
