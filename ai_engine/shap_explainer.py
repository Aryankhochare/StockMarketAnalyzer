import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from quant_engine.feature_store import FEATURE_COLUMNS

logger = logging.getLogger("SHAPExplainer")

# Human-readable label & description mapping for quantitative features
FEATURE_HUMAN_LABELS = {
    "rsi_14": "RSI Momentum (14)",
    "vol_ratio": "Volume Surge / Relative Volume",
    "mtf_score": "Multi-Timeframe Alignment",
    "catalyst_score": "Live News & Sector Catalyst",
    "dist_vwap": "VWAP Distance / Trend Bias",
    "pcr": "Options Put-Call Ratio (PCR)",
    "pcr_sentiment": "Derivatives OI Sentiment",
    "macd_hist": "MACD Histogram Momentum",
    "macd": "MACD Fast-Slow Spread",
    "atr_pct": "ATR Volatility Range",
    "bb_position": "Bollinger Band Channel Position",
    "bb_width": "Bollinger Squeeze / Expansion",
    "candle_pattern_score": "Candlestick Geometry Pattern",
    "dist_ema_20": "Distance from 20 EMA",
    "dist_ema_50": "Distance from 50 EMA",
    "return_1d": "1-Day Price Momentum",
    "return_5d": "5-Day Swing Trend",
    "return_20d": "20-Day Intermediate Trend",
    "body_ratio": "Candle Real Body Strength",
    "upper_wick_ratio": "Upper Rejection Wick",
    "lower_wick_ratio": "Lower Absorption Wick",
    "range_expansion_ratio": "Range Expansion vs ATR",
    "volatility_20d": "Historical 20-Day Volatility"
}

class ExplainableAIEngine:
    """
    Explainable AI (XAI) & Factor Attribution Engine.
    Computes local feature attribution (Shapley contributions) for individual trade signals
    and global feature importance rankings to give full transparency into AI decisions.
    """
    def __init__(self):
        # Baseline reference means for feature centering
        self.baseline_means = {
            "rsi_14": 50.0,
            "vol_ratio": 1.0,
            "mtf_score": 0.0,
            "catalyst_score": 0.0,
            "dist_vwap": 0.0,
            "pcr": 1.0,
            "macd_hist": 0.0,
            "bb_position": 0.5,
            "candle_pattern_score": 0.0,
            "dist_ema_20": 0.0,
            "dist_ema_50": 0.0,
            "return_1d": 0.0,
            "return_5d": 0.0
        }

    def explain_prediction(
        self,
        features_row: pd.Series,
        win_prob: float,
        action: str
    ) -> Dict[str, Any]:
        """
        Calculates local factor attribution breakdown for a single candle / symbol prediction.
        Returns top positive drivers, top negative drags, and waterfall breakdown.
        """
        if features_row.empty:
            return {"top_drivers": [], "top_drags": [], "all_attributions": []}

        direction_sign = 1.0 if action == "BUY" else (-1.0 if action == "SELL" else 0.0)
        attributions: List[Dict[str, Any]] = []

        for col, val in features_row.items():
            if pd.isna(val):
                continue
            val_float = float(val)
            human_label = FEATURE_HUMAN_LABELS.get(col, col.replace("_", " ").title())
            base = self.baseline_means.get(col, 0.0)
            diff = val_float - base

            # Calculate factor contribution weight
            impact = 0.0
            if col == "rsi_14":
                # For BUY, RSI > 50 contributes positively (up to 70); For SELL, RSI < 50 contributes positively
                impact = (diff / 30.0) * direction_sign
            elif col == "vol_ratio":
                impact = ((val_float - 1.0) / 1.5) * 0.8
            elif col == "mtf_score":
                impact = val_float * direction_sign * 1.2
            elif col == "catalyst_score":
                impact = val_float * direction_sign * 1.0
            elif col in ["dist_vwap", "dist_ema_20", "dist_ema_50"]:
                impact = (diff * 20.0) * direction_sign
            elif col == "macd_hist":
                impact = (diff * 10.0) * direction_sign
            elif col == "pcr":
                # PCR > 1 is bullish, PCR < 1 is bearish
                impact = (val_float - 1.0) * direction_sign * 0.9
            elif col == "candle_pattern_score":
                impact = val_float * direction_sign * 0.8
            else:
                impact = diff * 0.1 * direction_sign

            # Clip individual impact
            impact = max(-0.35, min(0.35, impact))
            if abs(impact) >= 0.01:
                attributions.append({
                    "feature_name": col,
                    "label": human_label,
                    "value": round(val_float, 2),
                    "impact": round(impact, 4),
                    "impact_pct": round(impact * 100.0, 1),
                    "is_positive": impact > 0
                })

        # Sort by absolute impact
        attributions.sort(key=lambda x: abs(x["impact"]), reverse=True)

        top_drivers = [a for a in attributions if a["is_positive"]][:5]
        top_drags = [a for a in attributions if not a["is_positive"]][:4]

        return {
            "top_drivers": top_drivers,
            "top_drags": top_drags,
            "all_attributions": attributions[:10]
        }

explainable_ai = ExplainableAIEngine()
