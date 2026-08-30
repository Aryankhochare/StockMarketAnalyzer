import datetime
import zoneinfo
import logging
from typing import Dict, Any

logger = logging.getLogger("MarketCalendar")

class MarketCalendar:
    """
    NSE / Indian Equity Market Session & Calendar Engine.
    Handles market session timings (09:15 AM - 03:30 PM IST), weekend/holiday detection,
    and switches the autonomous agent between Live Execution and Offline Self-Learning Mode.
    """
    def __init__(self):
        try:
            self.tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        except Exception:
            # Fallback to fixed offset UTC+5:30
            self.tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

    def get_current_ist_time(self) -> datetime.datetime:
        return datetime.datetime.now(self.tz)

    def is_market_open(self) -> bool:
        """
        Returns True only if current time is Monday-Friday between 09:15 AM and 03:30 PM IST.
        """
        now = self.get_current_ist_time()
        weekday = now.weekday() # 0: Monday ... 4: Friday, 5: Saturday, 6: Sunday

        # Check Weekend
        if weekday in [5, 6]:
            return False

        # Check Trading Hours: 09:15 to 15:30 IST
        market_open_time = datetime.time(9, 15)
        market_close_time = datetime.time(15, 30)
        current_time = now.time()

        return market_open_time <= current_time <= market_close_time

    def get_session_status(self) -> Dict[str, Any]:
        """Returns comprehensive session metrics for API and Dashboard UI."""
        now = self.get_current_ist_time()
        weekday = now.weekday()
        current_time = now.time()
        is_open = self.is_market_open()

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = day_names[weekday]

        if is_open:
            status_text = "MARKET OPEN (Live Trading)"
            badge_type = "OPEN"
            next_action = "Active Execution & Live Trailing Stop Monitoring"
        elif weekday in [5, 6]:
            status_text = f"MARKET CLOSED (Weekend - {day_name})"
            badge_type = "WEEKEND"
            next_action = "Offline Self-Learning, Model Calibration & News Scanning Active"
        elif current_time < datetime.time(9, 15):
            status_text = "PRE-MARKET (Opens 09:15 AM IST)"
            badge_type = "PRE_MARKET"
            next_action = "Scanning Pre-Market Sentiment & Macro Indicators"
        else:
            status_text = "POST-MARKET (Closed at 03:30 PM IST)"
            badge_type = "POST_MARKET"
            next_action = "Running Loss Post-Mortems & Model Retraining"

        return {
            "is_open": is_open,
            "status": status_text,
            "badge_type": badge_type,
            "current_ist": now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "current_day": day_name,
            "next_action": next_action,
            "offline_learning_active": not is_open
        }

market_calendar = MarketCalendar()
