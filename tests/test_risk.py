import pytest
from decision_and_risk.risk_engine import RiskEngine

def test_position_sizing_buy():
    engine = RiskEngine(account_balance=500000.0) # ₹5,00,000
    entry_price = 2500.0
    atr = 25.0 # ATR = 25
    
    res = engine.calculate_position_size_and_levels(entry_price, "BUY", atr)

    assert res["allowed"] is True
    assert res["stop_loss"] == 2462.5 # 2500 - (1.5 * 25)
    assert res["target"] == 2562.5   # 2500 + (2.5 * 25)
    assert res["quantity"] > 0
    assert res["risk_reward_ratio"] >= 1.5

def test_daily_drawdown_limit_exceeded():
    engine = RiskEngine(account_balance=500000.0)
    engine.daily_pnl = -20000.0 # Breaches ₹15,000 max daily loss (3%)

    res = engine.calculate_position_size_and_levels(2500.0, "BUY", 25.0)

    assert res["allowed"] is False
    assert "limit" in res["reason"].lower()
