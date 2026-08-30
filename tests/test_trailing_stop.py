import pytest
from pathlib import Path
from decision_and_risk.paper_trader import PaperTrader

def test_trailing_stop_and_break_even_long(tmp_path):
    db_file = tmp_path / "test_trail.db"
    trader = PaperTrader(db_path=db_file, initial_balance=2000.0)

    # 1. Open Long Trade: Entry=100, SL=90 (Risk=10, ATR=6.67), Target=130
    signal = {
        "symbol": "RELIANCE",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 100.0,
        "stop_loss": 90.0,
        "target": 130.0,
        "atr": 5.0,
        "win_prob_pct": 70.0
    }
    res = trader.open_position(signal)
    assert res["status"] == "SUCCESS"
    pos = trader.active_positions["RELIANCE"]
    assert pos["trailing_stop"] == 90.0
    assert pos["is_break_even"] == 0

    # 2. Price climbs to 110 (+1R profit reached, Risk=10)
    update_1 = trader.update_live_price("RELIANCE", 110.0)
    assert update_1 is not None
    assert pos["is_break_even"] == 1
    assert pos["trailing_stop"] >= 100.0 # Break-Even activated!

    # 3. Price climbs further to 120 (Peak=120, ATR=5 -> Trail = 120 - 1.5*5 = 112.5)
    update_2 = trader.update_live_price("RELIANCE", 120.0)
    assert pos["peak_price"] == 120.0
    assert pos["trailing_stop"] == 112.5 # Trailing Stop ratcheted to 112.5!

    # 4. Price pulls back from 120 down to 111 (crosses 112.5 trailing stop)
    exit_res = trader.update_live_price("RELIANCE", 111.0)
    assert exit_res is not None
    assert exit_res["status"] == "CLOSED"
    assert exit_res["trade"]["close_reason"] == "TRAILING_STOP_HIT"
    assert exit_res["trade"]["realized_pnl"] == 110.0 # Exit at 111 -> (111 - 100) * 10 = +110 profit!
    assert trader.balance == 2110.0

def test_trailing_stop_short(tmp_path):
    db_file = tmp_path / "test_trail_short.db"
    trader = PaperTrader(db_path=db_file, initial_balance=2000.0)

    # 1. Open Short Trade: Entry=200, SL=210 (Risk=10, ATR=5), Target=170
    signal = {
        "symbol": "TCS",
        "action": "SELL",
        "quantity": 10,
        "entry_price": 200.0,
        "stop_loss": 210.0,
        "target": 170.0,
        "atr": 5.0,
        "win_prob_pct": 68.0
    }
    trader.open_position(signal)
    pos = trader.active_positions["TCS"]

    # 2. Price drops to 190 (+1R profit reached)
    trader.update_live_price("TCS", 190.0)
    assert pos["is_break_even"] == 1
    assert pos["trailing_stop"] <= 200.0

    # 3. Price drops to 180 (Trough=180, ATR=5 -> Trail = 180 + 1.5*5 = 187.5)
    trader.update_live_price("TCS", 180.0)
    assert pos["trailing_stop"] == 187.5

    # 4. Price bounces to 189 (crosses 187.5 trailing stop)
    exit_res = trader.update_live_price("TCS", 189.0)
    assert exit_res["status"] == "CLOSED"
    assert exit_res["trade"]["close_reason"] == "TRAILING_STOP_HIT"
    assert exit_res["trade"]["realized_pnl"] == 110.0 # (200 - 189) * 10 = +110 profit!
