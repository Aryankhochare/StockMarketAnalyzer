import pytest
import pandas as pd
from ai_engine.shap_explainer import explainable_ai

def test_shap_explainer_factor_attribution():
    # Synthetic feature row for a bullish setup
    row = pd.Series({
        "rsi_14": 65.0,        # Bullish momentum (>50)
        "vol_ratio": 2.2,       # Volume surge (>1.0)
        "mtf_score": 0.8,       # Bullish MTF alignment
        "catalyst_score": 0.5,  # Bullish news catalyst
        "dist_vwap": 0.015,     # Trading above VWAP
        "pcr": 1.25,            # Bullish option PCR
        "bb_position": 0.75,
        "candle_pattern_score": 1.0
    })

    attribution = explainable_ai.explain_prediction(row, win_prob=0.74, action="BUY")

    assert "top_drivers" in attribution
    assert "top_drags" in attribution
    assert "all_attributions" in attribution
    assert len(attribution["top_drivers"]) > 0

    driver_labels = [d["label"] for d in attribution["top_drivers"]]
    assert any("Volume" in l or "RSI" in l or "Multi-Timeframe" in l for l in driver_labels)
    assert all(d["is_positive"] is True for d in attribution["top_drivers"])

def test_shap_explainer_bearish_setup():
    row = pd.Series({
        "rsi_14": 35.0,        # Bearish momentum (<50)
        "vol_ratio": 1.8,       # High volume on drop
        "mtf_score": -0.8,      # Bearish MTF
        "catalyst_score": -0.4, # Negative news catalyst
        "dist_vwap": -0.02,     # Below VWAP
        "pcr": 0.7              # Bearish PCR
    })

    attribution = explainable_ai.explain_prediction(row, win_prob=0.71, action="SELL")
    assert len(attribution["top_drivers"]) > 0
    # For SELL, lower RSI, negative MTF, and negative news should be positive drivers of the SELL decision
    driver_features = [d["feature_name"] for d in attribution["top_drivers"]]
    assert "rsi_14" in driver_features or "mtf_score" in driver_features or "catalyst_score" in driver_features
