import pandas as pd
from typing import Dict, Any

class MultiTimeframeAnalyzer:
    """
    Multi-Timeframe Trend Alignment Analyzer.
    Evaluates moving average structure, RSI momentum, and price location across time horizons.
    Outputs an MTF alignment score between -1.0 (All Bearish) and +1.0 (All Bullish).
    """
    def analyze_alignment(self, df_candles: pd.DataFrame) -> Dict[str, Any]:
        if df_candles.empty or len(df_candles) < 20:
            return {"mtf_score": 0.0, "alignment": "NEUTRAL"}

        latest = df_candles.iloc[-1]
        close = latest['close']
        ema_9 = latest.get('ema_9', close)
        ema_20 = latest.get('ema_20', close)
        ema_50 = latest.get('ema_50', close)
        rsi = latest.get('rsi_14', 50.0)

        score = 0.0
        
        # Short-term momentum check (EMA 9 vs EMA 20)
        if close > ema_9 > ema_20:
            score += 0.35
        elif close < ema_9 < ema_20:
            score -= 0.35

        # Medium-term trend check (EMA 20 vs EMA 50)
        if ema_20 > ema_50:
            score += 0.35
        elif ema_20 < ema_50:
            score -= 0.35

        # RSI Momentum filter
        if rsi > 55:
            score += 0.30
        elif rsi < 45:
            score -= 0.30

        score = max(-1.0, min(1.0, score))

        if score >= 0.6:
            alignment = "STRONG_BULLISH"
        elif score <= -0.6:
            alignment = "STRONG_BEARISH"
        else:
            alignment = "MIXED_NEUTRAL"

        return {
            "mtf_score": round(score, 2),
            "alignment": alignment,
            "rsi": round(rsi, 2)
        }
