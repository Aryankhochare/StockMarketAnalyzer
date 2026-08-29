import pandas as pd
from typing import Dict, Any

class RegimeDetector:
    """
    Market Regime Classifier.
    Categorizes current market environment into:
    - BULLISH_TRENDING
    - BEARISH_TRENDING
    - SIDEWAYS
    - HIGH_VOLATILITY
    """
    def detect_regime(self, df_full: pd.DataFrame) -> Dict[str, Any]:
        if df_full.empty or len(df_full) < 20:
            return {"regime": "NEUTRAL", "volatility_state": "NORMAL", "score": 0.0}

        latest = df_full.iloc[-1]
        close = latest['close']
        ema_20 = latest.get('ema_20', close)
        ema_50 = latest.get('ema_50', close)
        rsi = latest.get('rsi_14', 50.0)
        volatility = latest.get('volatility_20d', 0.01)
        bb_width = latest.get('bb_width', 0.05)

        # Volatility Classification
        if volatility > 0.025 or bb_width > 0.08:
            vol_state = "HIGH"
        elif volatility < 0.008:
            vol_state = "LOW"
        else:
            vol_state = "NORMAL"

        # Regime Classification logic
        if close > ema_20 > ema_50 and rsi > 55:
            regime = "BULLISH_TRENDING"
            score = 1.0
        elif close < ema_20 < ema_50 and rsi < 45:
            regime = "BEARISH_TRENDING"
            score = -1.0
        elif vol_state == "HIGH":
            regime = "HIGH_VOLATILITY"
            score = 0.0
        else:
            regime = "SIDEWAYS"
            score = 0.0

        return {
            "regime": regime,
            "volatility_state": vol_state,
            "score": score,
            "rsi": round(rsi, 2),
            "volatility_20d": round(volatility, 4)
        }
