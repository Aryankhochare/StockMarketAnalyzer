import pytest
import pandas as pd
from pathlib import Path
from ai_engine.loss_analyzer import LossAnalyzer

def test_loss_analyzer_diagnosis_and_penalty(tmp_path):
    db_file = tmp_path / "test_loss.db"
    analyzer = LossAnalyzer(db_path=db_file)

    trade = {
        "id": "TRADE_001",
        "symbol": "TCS",
        "action": "BUY",
        "entry_price": 3500.0,
        "exit_price": 3400.0,
        "realized_pnl": -100.0,
        "realized_pnl_pct": -2.85,
        "close_time": "2026-08-30 10:00:00"
    }

    # Synthetic historical DataFrame showing overbought RSI
    df = pd.DataFrame({
        "close": [3480, 3490, 3500],
        "rsi_14": [68, 72, 75], # Overbought RSI
        "adx_14": [22, 24, 25],
        "volume_ratio": [1.1, 1.2, 0.6], # Volume exhaustion
        "regime": ["BULLISH_TRENDING", "BULLISH_TRENDING", "BULLISH_TRENDING"]
    })

    diagnosis = analyzer.diagnose_loss(trade, df)
    assert "MOMENTUM_EXHAUSTION" in diagnosis or "FALSE_BREAKOUT" in diagnosis
    assert len(analyzer.get_all_loss_diagnostics()) == 1

    # Check adaptive penalty application
    penalty = analyzer.get_adaptive_loss_penalty("TCS", "BULLISH_TRENDING", "BUY")
    assert penalty > 0.0 # Adaptive penalty applied
