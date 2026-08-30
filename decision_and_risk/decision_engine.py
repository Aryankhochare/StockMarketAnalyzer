import logging
import pandas as pd
from typing import Dict, Any, Optional
from ai_engine.predictor import ai_predictor
from decision_and_risk.risk_engine import risk_engine
from config import (
    MIN_MODEL_CONFIDENCE,
    ESTIMATED_TRANSACTION_COST_PCT,
    ESTIMATED_SLIPPAGE_PCT
)

logger = logging.getLogger("DecisionEngine")

class DecisionEngine:
    """
    Final Trading Decision Engine.
    Evaluates:
    - AI Calibrated Ensemble probabilities & win confidence
    - Market regime & Multi-Timeframe alignment
    - News event shocks & sector catalysts
    - Net Expected Value (EV) after transaction costs & slippage
    - Risk engine position sizing and stop/target validation
    """
    def evaluate_trade(
        self,
        symbol: str,
        df_full: pd.DataFrame,
        option_snapshot: Optional[Dict[str, Any]] = None,
        vix_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if df_full.empty or len(df_full) < 15:
            return {
                "symbol": symbol,
                "action": "HOLD",
                "reason": "Insufficient data",
                "confidence": 0.0
            }

        latest_row = df_full.iloc[-1]
        entry_price = float(latest_row['close'])
        atr = float(latest_row.get('atr_14', entry_price * 0.015))

        # Step 1: Run AI Predictor (Ensemble + MTF + News Catalysts)
        prediction = ai_predictor.predict(symbol, df_full, option_snapshot)
        prob_bull = prediction["prob_bull"]
        prob_bear = prediction["prob_bear"]
        confidence = prediction["confidence"]
        regime_info = prediction["regime_info"]
        mtf_info = prediction.get("mtf_info", {})
        news_info = prediction.get("news_info", {})

        # Event Risk Filter Check
        if news_info.get("event_risk_flag"):
            return {
                "symbol": symbol,
                "action": "HOLD",
                "reason": f"Event Risk Gate Blocked: High-impact negative news shock ({news_info.get('latest_headline')})",
                "confidence": round(confidence * 100, 1),
                "entry_price": entry_price,
                "prediction": prediction
            }

        # Determine signal direction based on highest probability
        if prob_bull >= 0.52 and prob_bull > prob_bear:
            action = "BUY"
            win_prob = prob_bull
        elif prob_bear >= 0.52 and prob_bear > prob_bull:
            action = "SELL"
            win_prob = prob_bear
        else:
            return {
                "symbol": symbol,
                "action": "HOLD",
                "reason": f"No strong directional consensus (Bull: {prob_bull*100:.1f}%, Bear: {prob_bear*100:.1f}%)",
                "confidence": round(confidence * 100, 1),
                "entry_price": entry_price,
                "prediction": prediction
            }

        # Step 2: Check Risk Engine for levels & position sizing with VIX scaling
        risk_evaluation = risk_engine.calculate_position_size_and_levels(entry_price, action, atr, vix_snapshot)
        if not risk_evaluation["allowed"]:
            return {
                "symbol": symbol,
                "action": "HOLD",
                "reason": f"Risk Gate Blocked: {risk_evaluation['reason']}",
                "confidence": round(confidence * 100, 1),
                "entry_price": entry_price,
                "prediction": prediction
            }

        # Step 3: Calculate Net Expected Value (EV) after transaction costs & slippage
        total_costs_pct = (ESTIMATED_TRANSACTION_COST_PCT + ESTIMATED_SLIPPAGE_PCT) / 100.0
        reward_pct = (risk_evaluation["reward_per_share"] / entry_price) - total_costs_pct
        risk_pct = (risk_evaluation["risk_per_share"] / entry_price) + total_costs_pct

        expected_value_pct = (win_prob * reward_pct) - ((1.0 - win_prob) * risk_pct)

        if expected_value_pct <= 0:
            return {
                "symbol": symbol,
                "action": "HOLD",
                "reason": f"Negative Net Expected Value after costs ({expected_value_pct*100:.2f}%)",
                "confidence": round(confidence * 100, 1),
                "entry_price": entry_price,
                "prediction": prediction
            }

        # Final Approved Trade Signal
        return {
            "symbol": symbol,
            "action": action,
            "reason": f"Calibrated {action} signal in {regime_info['regime']} regime | MTF: {mtf_info.get('alignment', 'NEUTRAL')}",
            "confidence_pct": round(confidence * 100, 1),
            "win_prob_pct": round(win_prob * 100, 1),
            "expected_value_pct": round(expected_value_pct * 100, 2),
            "entry_price": entry_price,
            "quantity": risk_evaluation["quantity"],
            "stop_loss": risk_evaluation["stop_loss"],
            "target": risk_evaluation["target"],
            "atr": risk_evaluation.get("atr", atr),
            "risk_reward_ratio": risk_evaluation["risk_reward_ratio"],
            "total_position_value": risk_evaluation["total_position_value"],
            "regime_info": regime_info,
            "mtf_info": mtf_info,
            "news_info": news_info,
            "factor_attribution": prediction.get("factor_attribution", {})
        }

# Global Instance
decision_engine = DecisionEngine()
