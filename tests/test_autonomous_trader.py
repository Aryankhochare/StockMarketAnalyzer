import pytest
from decision_and_risk.autonomous_trader import autonomous_trader

def test_autonomous_trader_status_and_toggle():
    status = autonomous_trader.get_status()
    assert "is_active" in status
    assert "scan_interval_seconds" in status
    assert "max_concurrent_positions" in status

    initial_active = autonomous_trader.is_active
    toggled = autonomous_trader.toggle()
    assert toggled != initial_active

    # Restore initial state
    autonomous_trader.toggle()
