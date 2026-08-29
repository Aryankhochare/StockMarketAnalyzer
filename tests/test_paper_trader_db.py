import os
import pytest
from pathlib import Path
from decision_and_risk.paper_trader import PaperTrader

def test_paper_trader_sqlite_lifecycle(tmp_path):
    db_file = tmp_path / "test_paper.db"
    trader = PaperTrader(db_path=db_file, initial_balance=2000.0)

    assert trader.balance == 2000.0
    assert len(trader.active_positions) == 0

    # 1. Open Position
    signal = {
        "symbol": "RELIANCE",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "target": 110.0,
        "win_prob_pct": 72.0,
        "confidence_pct": 75.0
    }
    res = trader.open_position(signal)
    assert res["status"] == "SUCCESS"
    assert "RELIANCE" in trader.active_positions

    # 2. Test Persistence Across Restarts (new instance pointing to same DB)
    trader_reloaded = PaperTrader(db_path=db_file, initial_balance=2000.0)
    assert "RELIANCE" in trader_reloaded.active_positions
    assert trader_reloaded.active_positions["RELIANCE"]["entry_price"] == 100.0

    # 3. Update Price to Target (Win)
    exit_res = trader_reloaded.update_live_price("RELIANCE", 112.0)
    assert exit_res is not None
    assert exit_res["status"] == "CLOSED"
    assert exit_res["trade"]["realized_pnl"] == 120.0 # (112 - 100) * 10
    assert trader_reloaded.balance == 2120.0

    # 4. Check Closed Trade Persistence
    trader_reloaded_2 = PaperTrader(db_path=db_file, initial_balance=2000.0)
    assert trader_reloaded_2.balance == 2120.0
    assert len(trader_reloaded_2.trade_history) == 1
    assert len(trader_reloaded_2.active_positions) == 0
