import logging
import pandas as pd
from typing import Dict, Any
from config import (
    INITIAL_ACCOUNT_BALANCE,
    MAX_RISK_PER_TRADE_PCT,
    MAX_DAILY_DRAWDOWN_PCT,
    MIN_RISK_REWARD_RATIO
)

logger = logging.getLogger("RiskEngine")

class RiskEngine:
    """
    Deterministic Risk Management Engine.
    Enforces strict risk gates that CANNOT be bypassed by the AI model:
    1. Capital Risk per Trade (Max 1.5% of account balance)
    2. Dynamic ATR-based Stop Loss & Target calculation
    3. Minimum Risk-to-Reward Ratio (Min 1:1.5)
    4. Account Portfolio Drawdown Limit
    """
    def __init__(self, account_balance: float = INITIAL_ACCOUNT_BALANCE):
        self.account_balance = account_balance
        self.daily_pnl = 0.0

    def calculate_position_size_and_levels(
        self,
        entry_price: float,
        direction: str,
        atr: float
    ) -> Dict[str, Any]:
        """
        Calculates exact shares/quantity, stop loss, and target price.
        ATR multiplier for stop loss = 1.5 * ATR
        Target multiplier = 2.5 * ATR (Risk-Reward = 1.67)
        """
        if entry_price <= 0 or atr <= 0:
            return {"allowed": False, "reason": "Invalid price or ATR"}

        # Check maximum account drawdown limit
        max_daily_loss = self.account_balance * (MAX_DAILY_DRAWDOWN_PCT / 100.0)
        if self.daily_pnl <= -max_daily_loss:
            return {"allowed": False, "reason": f"Daily loss limit (₹{max_daily_loss:.2f}) breached"}

        # Calculate max capital risk amount for this trade
        max_risk_amount = self.account_balance * (MAX_RISK_PER_TRADE_PCT / 100.0)

        # Stop distance based on 1.5 x ATR
        stop_distance = round(1.5 * atr, 2)
        target_distance = round(2.5 * atr, 2)

        if direction == "BUY":
            stop_loss = round(entry_price - stop_distance, 2)
            target = round(entry_price + target_distance, 2)
        elif direction == "SELL":
            stop_loss = round(entry_price + stop_distance, 2)
            target = round(entry_price - target_distance, 2)
        else:
            return {"allowed": False, "reason": "Neutral direction"}

        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(target - entry_price)

        if risk_per_share <= 0:
            return {"allowed": False, "reason": "Zero risk distance"}

        # Risk-to-Reward check
        risk_reward_ratio = reward_per_share / risk_per_share
        if risk_reward_ratio < MIN_RISK_REWARD_RATIO:
            return {"allowed": False, "reason": f"Risk-Reward ({risk_reward_ratio:.2f}) below threshold ({MIN_RISK_REWARD_RATIO})"}

        # Position Sizing: Number of shares/units = (Max Risk Amount) / (Risk per Share)
        calculated_qty = max_risk_amount / risk_per_share
        
        # Cap position value so it doesn't exceed 40% of total capital
        max_position_value = self.account_balance * 0.40
        max_qty_by_cap = max_position_value / entry_price if entry_price > 0 else 1.0
        
        raw_quantity = min(calculated_qty, max_qty_by_cap)
        if entry_price > 500:
            quantity = max(0.01, round(raw_quantity, 4))
        else:
            quantity = max(1, int(raw_quantity))

        total_position_value = round(quantity * entry_price, 2)
        total_risk_amount = round(quantity * risk_per_share, 2)

        return {
            "allowed": True,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "risk_per_share": round(risk_per_share, 2),
            "reward_per_share": round(reward_per_share, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "total_position_value": total_position_value,
            "total_risk_amount": total_risk_amount
        }

# Global Instance
risk_engine = RiskEngine()
