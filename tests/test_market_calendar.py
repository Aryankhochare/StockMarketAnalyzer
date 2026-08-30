import datetime
from data_bridge.market_calendar import MarketCalendar

def test_market_calendar_session_detection(monkeypatch):
    cal = MarketCalendar()

    # 1. Test Sunday (Weekend)
    sunday_dt = datetime.datetime(2026, 8, 30, 14, 0, 0, tzinfo=cal.tz) # Sunday 2:00 PM IST
    monkeypatch.setattr(cal, "get_current_ist_time", lambda: sunday_dt)
    assert cal.is_market_open() is False
    status = cal.get_session_status()
    assert status["is_open"] is False
    assert "Weekend" in status["status"]
    assert status["offline_learning_active"] is True

    # 2. Test Monday at 11:30 AM (Live Trading Hours)
    monday_open_dt = datetime.datetime(2026, 8, 31, 11, 30, 0, tzinfo=cal.tz) # Monday 11:30 AM IST
    monkeypatch.setattr(cal, "get_current_ist_time", lambda: monday_open_dt)
    assert cal.is_market_open() is True
    status_open = cal.get_session_status()
    assert status_open["is_open"] is True
    assert status_open["badge_type"] == "OPEN"
    assert status_open["offline_learning_active"] is False

    # 3. Test Monday at 8:30 PM (Post-Market)
    monday_closed_dt = datetime.datetime(2026, 8, 31, 20, 30, 0, tzinfo=cal.tz) # Monday 8:30 PM IST
    monkeypatch.setattr(cal, "get_current_ist_time", lambda: monday_closed_dt)
    assert cal.is_market_open() is False
    status_closed = cal.get_session_status()
    assert status_closed["badge_type"] == "POST_MARKET"
    assert status_closed["offline_learning_active"] is True
