import pytest
from backtesting.walk_forward import WalkForwardBacktester
from tests.test_features import create_sample_candles

def test_walk_forward_backtest():
    backtester = WalkForwardBacktester()
    df = create_sample_candles(50)

    res = backtester.run_backtest("RELIANCE", df)

    assert res["status"] == "SUCCESS"
    assert "win_rate_pct" in res
    assert "sharpe_ratio" in res
    assert "max_drawdown_pct" in res
    assert "final_equity" in res
