import logging
import pandas as pd
from typing import Dict, Any, Optional
from quant_engine.feature_store import FeatureStore
from quant_engine.news_event_engine import news_event_engine
from quant_engine.multi_timeframe import MultiTimeframeAnalyzer
from quant_engine.relative_strength import RelativeStrengthAnalyzer
from ai_engine.ensemble_model import ensemble_model
from ai_engine.regime_detector import RegimeDetector
from ai_engine.loss_analyzer import loss_analyzer
from ai_engine.shap_explainer import explainable_ai

logger = logging.getLogger("AIPredictor")

class AIPredictor:
    """
    Real-Time AI Inference Engine.
    Combines Calibrated Ensemble Model, Multi-Timeframe Alignment,
    Sector News Catalysts, and Market Regime Classification.
    """
    def __init__(self):
        self.feature_store = FeatureStore()
        self.regime_detector = RegimeDetector()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.rs_analyzer = RelativeStrengthAnalyzer()

    def predict(self, symbol: str, df_full: pd.DataFrame, option_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        regime_info = self.regime_detector.detect_regime(df_full)
        mtf_info = self.mtf_analyzer.analyze_alignment(df_full)
        news_info = news_event_engine.get_symbol_catalyst(symbol)
        catalyst_score = news_info.get("catalyst_score", 0.0)

        if df_full.empty or len(df_full) < 15:
            return {
                "signal": "NEUTRAL",
                "prob_bull": 0.33,
                "prob_bear": 0.33,
                "prob_flat": 0.34,
                "confidence": 0.0,
                "expected_return_pct": 0.0,
                "regime_info": regime_info,
                "mtf_info": mtf_info,
                "news_info": news_info
            }

        # Build feature matrix including news catalyst score
        _, df_features = self.feature_store.build_features(df_full, option_snapshot, catalyst_score)
        latest_features = df_features.iloc[-1:]

        # Run Calibrated Ensemble prediction
        prob_bear, prob_flat, prob_bull = ensemble_model.predict_proba(latest_features)

        # Apply News Catalyst & MTF Adjustments to win probabilities
        if catalyst_score > 0.3:
            prob_bull = min(0.95, prob_bull + 0.10)
        elif catalyst_score < -0.3:
            prob_bear = min(0.95, prob_bear + 0.10)

        if mtf_info["mtf_score"] >= 0.6:
            prob_bull = min(0.95, prob_bull + 0.08)
        elif mtf_info["mtf_score"] <= -0.6:
            prob_bear = min(0.95, prob_bear + 0.08)

        # Apply Adaptive Loss Learning Penalties
        bull_penalty = loss_analyzer.get_adaptive_loss_penalty(symbol, regime_info.get("regime", ""), "BUY")
        bear_penalty = loss_analyzer.get_adaptive_loss_penalty(symbol, regime_info.get("regime", ""), "SELL")
        prob_bull = max(0.05, prob_bull - bull_penalty)
        prob_bear = max(0.05, prob_bear - bear_penalty)

        total = prob_bull + prob_bear + prob_flat
        prob_bull = round(prob_bull / total, 4)
        prob_bear = round(prob_bear / total, 4)
        prob_flat = round(prob_flat / total, 4)

        confidence = max(prob_bull, prob_bear, prob_flat)
        expected_return_pct = round((prob_bull * 1.8) - (prob_bear * 1.8), 2)

        action = "BUY" if prob_bull > prob_bear and prob_bull >= 0.52 else ("SELL" if prob_bear > prob_bull and prob_bear >= 0.52 else "HOLD")
        attribution = explainable_ai.explain_prediction(latest_features.iloc[0], confidence, action)

        return {
            "symbol": symbol,
            "prob_bull": prob_bull,
            "prob_bear": prob_bear,
            "prob_flat": prob_flat,
            "confidence": confidence,
            "expected_return_pct": expected_return_pct,
            "regime_info": regime_info,
            "mtf_info": mtf_info,
            "news_info": news_info,
            "factor_attribution": attribution
        }

# Global Instance
ai_predictor = AIPredictor()
