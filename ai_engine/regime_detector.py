import pandas as pd
from typing import Dict, Any, Optional
from config import HIGH_VIX_THRESHOLD, LOW_VIX_THRESHOLD

class RegimeDetector:
    """
    Market Regime & India VIX Volatility Classifier.
    Categorizes current market environment into:
    - BULLISH_TRENDING
    - BEARISH_TRENDING
    - SIDEWAYS
    - HIGH_VOLATILITY / TURBULENT
    """
    def detect_regime(
        self,
        df_full: pd.DataFrame,
        vix_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if df_full.empty or len(df_full) < 15:
            return {"regime": "NEUTRAL", "volatility_state": "NORMAL", "score": 0.0, "vix_info": {}}

        latest = df_full.iloc[-1]
        close = latest['close']
        ema_20 = latest.get('ema_20', close)
        ema_50 = latest.get('ema_50', close)
        rsi = latest.get('rsi_14', 50.0)
        volatility = latest.get('volatility_20d', 0.01)
        bb_width = latest.get('bb_width', 0.05)

        # India VIX Metrics
        vix_val = 14.5
        vix_change = 0.0
        if vix_snapshot:
            vix_val = float(vix_snapshot.get("vix", 14.5))
            vix_change = float(vix_snapshot.get("change_pct", 0.0))

        vix_shock = vix_val >= HIGH_VIX_THRESHOLD or vix_change >= 8.0

        # Volatility Classification
        if volatility > 0.025 or bb_width > 0.08 or vix_shock:
            vol_state = "HIGH"
        elif volatility < 0.008 or vix_val < LOW_VIX_THRESHOLD:
            vol_state = "LOW"
        else:
            vol_state = "NORMAL"

        # Regime Classification logic
        if vix_shock:
            regime = "HIGH_VOLATILITY_TURBULENT"
            score = -0.5 if vix_change > 0 else 0.0
        elif close > ema_20 > ema_50 and rsi > 55:
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
            "volatility_20d": round(volatility, 4),
            "vix_info": {
                "vix": round(vix_val, 2),
                "change_pct": round(vix_change, 2),
                "is_vix_shock": vix_shock
            }
        }
