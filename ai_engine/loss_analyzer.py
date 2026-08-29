import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
from config import PAPER_DB_PATH

logger = logging.getLogger("LossAnalyzer")

class LossAnalyzer:
    """
    AI Loss Post-Mortem & Adaptive Self-Learning Engine.
    Analyzes stopped-out trades to diagnose root causes (false breakouts, regime shifts,
    volume exhaustion, adverse catalysts) and maintains an adaptive memory of loss patterns
    to discount repeat failure setups in future inference.
    """
    def __init__(self, db_path: Path = PAPER_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loss_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    diagnosis TEXT NOT NULL,
                    penalty_weight REAL DEFAULT 0.05,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def diagnose_loss(
        self,
        trade: Dict[str, Any],
        df_history: Optional[pd.DataFrame] = None
    ) -> str:
        """
        Performs post-mortem root-cause analysis on a losing trade.
        """
        symbol = trade.get("symbol", "UNKNOWN")
        action = trade.get("action", "BUY")
        entry_price = trade.get("entry_price", 0.0)
        exit_price = trade.get("exit_price", 0.0)
        pnl_pct = trade.get("realized_pnl_pct", 0.0)
        
        failure_type = "UNEXPECTED_VOLATILITY"
        diagnosis_reasons = []

        if df_history is not None and not df_history.empty:
            latest = df_history.iloc[-1]
            rsi = float(latest.get("rsi_14", 50.0))
            adx = float(latest.get("adx_14", 20.0))
            vol_ratio = float(latest.get("volume_ratio", 1.0))
            regime = str(latest.get("regime", "RANGING"))

            # Check Overextension
            if action == "BUY" and rsi > 70:
                failure_type = "MOMENTUM_EXHAUSTION"
                diagnosis_reasons.append("Overbought RSI (>70) triggered mean-reversion pullback")
            elif action == "SELL" and rsi < 30:
                failure_type = "OVERSOLD_BOUNCE"
                diagnosis_reasons.append("Oversold RSI (<30) triggered short-covering bounce")

            # Check Low Volume Breakout
            if vol_ratio < 0.8:
                failure_type = "FALSE_BREAKOUT"
                diagnosis_reasons.append(f"Volume exhaustion ({vol_ratio:.2f}x avg) failed to sustain price move")

            # Check Weak Trend / Choppy Market
            if adx < 18:
                failure_type = "CHOPPY_REGIME_WHIPSAW"
                diagnosis_reasons.append(f"Weak trend strength (ADX={adx:.1f}) resulted in range-bound stop hunt")
        else:
            regime = "HIGH_VOLATILITY"

        if not diagnosis_reasons:
            if action == "BUY":
                diagnosis_reasons.append(f"Bearish momentum overwhelmed support at {exit_price:.2f} (Loss: {pnl_pct:.2f}%)")
            else:
                diagnosis_reasons.append(f"Bullish surge broke resistance at {exit_price:.2f} (Loss: {pnl_pct:.2f}%)")

        full_diagnosis = f"[{failure_type}] " + " | ".join(diagnosis_reasons)

        # Save pattern into database for adaptive learning memory
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO loss_patterns (
                        trade_id, symbol, action, regime, failure_type, diagnosis, penalty_weight, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.get("id", "TRADE"),
                    symbol,
                    action,
                    regime,
                    failure_type,
                    full_diagnosis,
                    0.05,
                    trade.get("close_time", "")
                ))
                conn.commit()
            logger.info(f"AI Post-Mortem Diagnosed for {symbol}: {full_diagnosis}")
        except Exception as e:
            logger.error(f"Error saving loss pattern: {e}")

        return full_diagnosis

    def get_adaptive_loss_penalty(self, symbol: str, current_regime: str, action: str) -> float:
        """
        Calculates dynamic confidence penalty based on recent failure patterns in identical setups.
        Returns a discount value (e.g. 0.08 for 8% penalty) to subtract from raw AI probability.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Count recent similar losses in the last 15 loss events
                cursor.execute("""
                    SELECT COUNT(*) as count FROM (
                        SELECT * FROM loss_patterns 
                        WHERE symbol = ? AND action = ?
                        ORDER BY id DESC LIMIT 15
                    )
                """, (symbol, action))
                row = cursor.fetchone()
                loss_count = row["count"] if row else 0
                
                # Penalty: 3% penalty per recent loss setup, capped at 15% max penalty
                penalty = min(0.15, loss_count * 0.03)
                if penalty > 0:
                    logger.info(f"Applying adaptive learning penalty for {symbol} ({action}): -{penalty*100:.1f}% confidence")
                return penalty
        except Exception as e:
            logger.debug(f"Adaptive penalty calculation fallback: {e}")
            return 0.0

    def get_all_loss_diagnostics(self) -> List[Dict[str, Any]]:
        """Returns all recorded loss post-mortems for the analytics page."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM loss_patterns ORDER BY id DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error reading loss diagnostics: {e}")
            return []

loss_analyzer = LossAnalyzer()
