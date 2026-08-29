import pytest
from pathlib import Path
from decision_and_risk.paper_trader import PaperTrader
from decision_and_risk.performance_tracker import PerformanceTracker

def test_performance_tracker_metrics(tmp_path, monkeypatch):
    db_file = tmp_path / "test_tracker.db"
    test_trader = PaperTrader(db_path=db_file, initial_balance=2000.0)

    # Monkeypatch global paper_trader in performance_tracker
    from decision_and_risk import performance_tracker as pt_module
    monkeypatch.setattr(pt_module, "paper_trader", test_trader)

    tracker = PerformanceTracker()
    metrics = tracker.get_performance_metrics()
    assert metrics["total_trades"] == 0
    assert metrics["win_rate_pct"] == 0.0

    # Execute a WIN trade
    test_trader.open_position({
        "symbol": "INFY",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 100.0,
        "stop_loss": 90.0,
        "target": 120.0,
        "win_prob_pct": 70.0
    })
    test_trader.update_live_price("INFY", 125.0) # Win +250 tokens

    # Execute a LOSS trade
    test_trader.open_position({
        "symbol": "SBIN",
        "action": "BUY",
        "quantity": 10,
        "entry_price": 50.0,
        "stop_loss": 45.0,
        "target": 60.0,
        "win_prob_pct": 65.0
    })
    test_trader.update_live_price("SBIN", 40.0) # Loss -100 tokens

    metrics_after = tracker.get_performance_metrics()
    assert metrics_after["total_trades"] == 2
    assert metrics_after["winning_trades"] == 1
    assert metrics_after["losing_trades"] == 1
    assert metrics_after["win_rate_pct"] == 50.0
    assert metrics_after["total_pnl"] == 150.0 # +250 - 100
    assert metrics_after["current_balance"] == 2150.0
    assert len(metrics_after["equity_curve"]) == 3
