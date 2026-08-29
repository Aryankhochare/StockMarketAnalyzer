import pytest
import pandas as pd
import numpy as np
from decision_and_risk.decision_engine import DecisionEngine
from tests.test_features import create_sample_candles

def test_decision_engine_evaluation():
    engine = DecisionEngine()
    df = create_sample_candles(60)

    res = engine.evaluate_trade("NIFTY 50", df, {"pcr": 1.3})

    assert "action" in res
    assert res["action"] in ["BUY", "SELL", "HOLD"]
    assert "entry_price" in res
