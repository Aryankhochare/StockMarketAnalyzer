import pytest
import pandas as pd
from ai_engine.regime_detector import RegimeDetector
from decision_and_risk.risk_engine import RiskEngine

def test_vix_regime_classification():
    detector = RegimeDetector()
    df = pd.DataFrame({
        "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115],
        "ema_20": [100]*16,
        "ema_50": [95]*16,
        "rsi_14": [60]*16,
        "volatility_20d": [0.01]*16,
        "bb_width": [0.03]*16
    })

    # Normal VIX
    res_normal = detector.detect_regime(df, {"vix": 14.2, "change_pct": -1.5})
    assert res_normal["regime"] == "BULLISH_TRENDING"
    assert res_normal["vix_info"]["is_vix_shock"] is False

    # Elevated VIX Shock (>18.0)
    res_shock = detector.detect_regime(df, {"vix": 21.5, "change_pct": 12.0})
    assert "TURBULENT" in res_shock["regime"] or "HIGH_VOLATILITY" in res_shock["regime"]
    assert res_shock["vix_info"]["is_vix_shock"] is True

def test_vix_risk_scaling():
    engine = RiskEngine(account_balance=10000.0)

    # Standard risk sizing under normal VIX (Max risk 2% = 200 tokens)
    normal_eval = engine.calculate_position_size_and_levels(100.0, "BUY", 10.0, {"vix": 14.0, "change_pct": 0.0})
    normal_risk_amount = normal_eval["total_risk_amount"]

    # Scaled risk sizing under elevated VIX (>18, Max risk scaled down 40% = 120 tokens)
    shock_eval = engine.calculate_position_size_and_levels(100.0, "BUY", 10.0, {"vix": 22.0, "change_pct": 10.0})
    shock_risk_amount = shock_eval["total_risk_amount"]

    # Elevated VIX should reduce risk exposure
    assert shock_risk_amount < normal_risk_amount
