import time
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from config import (
    INITIAL_ACCOUNT_BALANCE,
    PAPER_DB_PATH,
    TRAILING_STOP_ENABLED,
    TRAILING_STOP_ATR_MULTIPLIER,
    BREAK_EVEN_TRIGGER_R
)

logger = logging.getLogger("PaperTrader")

class PaperTrader:
    """
    SQLite-Persistent Paper Trading Execution Simulator.
    Tracks active positions, monitors live tick updates against target & stop-loss levels,
    executes orders, and updates paper account token balance with complete crash resilience.
    """
    def __init__(self, db_path: Path = PAPER_DB_PATH, initial_balance: float = INITIAL_ACCOUNT_BALANCE):
        self.db_path = Path(db_path)
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        
        # Ensure parent dir exists & initialize database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_state()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Account State Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_state (
                    id INTEGER PRIMARY KEY,
                    balance REAL NOT NULL,
                    initial_balance REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 2. Active Positions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_positions (
                    symbol TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    initial_stop_loss REAL NOT NULL,
                    target REAL NOT NULL,
                    peak_price REAL NOT NULL,
                    trailing_stop REAL NOT NULL,
                    is_break_even INTEGER DEFAULT 0,
                    atr REAL DEFAULT 0.0,
                    unrealized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl_pct REAL DEFAULT 0.0,
                    predicted_win_prob REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    open_time TEXT NOT NULL,
                    raw_data TEXT
                )
            """)

            # Add columns if migrating from older schema
            try:
                cursor.execute("ALTER TABLE active_positions ADD COLUMN initial_stop_loss REAL DEFAULT 0.0")
            except Exception: pass
            try:
                cursor.execute("ALTER TABLE active_positions ADD COLUMN peak_price REAL DEFAULT 0.0")
            except Exception: pass
            try:
                cursor.execute("ALTER TABLE active_positions ADD COLUMN trailing_stop REAL DEFAULT 0.0")
            except Exception: pass
            try:
                cursor.execute("ALTER TABLE active_positions ADD COLUMN is_break_even INTEGER DEFAULT 0")
            except Exception: pass
            try:
                cursor.execute("ALTER TABLE active_positions ADD COLUMN atr REAL DEFAULT 0.0")
            except Exception: pass
            
            # 3. Trade History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    target REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    realized_pnl_pct REAL NOT NULL,
                    close_reason TEXT NOT NULL,
                    open_time TEXT NOT NULL,
                    close_time TEXT NOT NULL,
                    predicted_win_prob REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    loss_diagnosis TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def _load_state(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Load balance
                cursor.execute("SELECT balance, initial_balance FROM account_state WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    self.balance = float(row["balance"])
                    self.initial_balance = float(row["initial_balance"])
                else:
                    self.balance = self.initial_balance
                    cursor.execute(
                        "INSERT INTO account_state (id, balance, initial_balance, updated_at) VALUES (1, ?, ?, ?)",
                        (self.balance, self.initial_balance, time.strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    conn.commit()

                # Load active positions
                self.active_positions.clear()
                cursor.execute("SELECT * FROM active_positions")
                for pos_row in cursor.fetchall():
                    pos_dict = dict(pos_row)
                    if pos_dict.get("raw_data"):
                        try:
                            extra = json.loads(pos_dict["raw_data"])
                            pos_dict.update(extra)
                        except Exception:
                            pass
                    self.active_positions[pos_dict["symbol"]] = pos_dict

                # Load trade history
                self.trade_history.clear()
                cursor.execute("SELECT * FROM trade_history ORDER BY close_time ASC")
                for th_row in cursor.fetchall():
                    self.trade_history.append(dict(th_row))

            logger.info(f"Loaded PaperTrader state: Balance={self.balance:.2f} Tokens, Open Positions={len(self.active_positions)}, Closed Trades={len(self.trade_history)}")
        except Exception as e:
            logger.error(f"Error loading state from DB: {e}")

    def _save_account_state(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE account_state SET balance = ?, updated_at = ? WHERE id = 1",
                    (self.balance, time.strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving account state: {e}")

    def open_position(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        symbol = signal.get("symbol")
        action = signal.get("action")
        quantity = signal.get("quantity", 0)
        entry_price = signal.get("entry_price", 0.0)

        if not symbol or action not in ["BUY", "SELL"] or quantity <= 0:
            return {"status": "FAILED", "reason": "Invalid trade signal payload"}

        if symbol in self.active_positions:
            return {"status": "IGNORED", "reason": f"Position already open for {symbol}"}

        position_cost = quantity * entry_price
        if position_cost > self.balance:
            # Dynamically adjust quantity if balance allows at least 1 unit
            adj_qty = int(self.balance / entry_price) if entry_price > 0 else 0
            if adj_qty >= 1:
                quantity = adj_qty
                position_cost = quantity * entry_price
            else:
                return {"status": "FAILED", "reason": f"Insufficient token balance ({self.balance:.2f} tokens available, need {position_cost:.2f})"}

        pos_id = f"PAPER_{int(time.time()*1000)}"
        win_prob = signal.get("win_prob_pct", signal.get("win_prob", 0.0))
        if win_prob > 1.0:
            win_prob = win_prob / 100.0

        confidence = signal.get("confidence_pct", signal.get("confidence", 0.0))
        if confidence > 1.0:
            confidence = confidence / 100.0

        initial_sl = round(float(signal.get("stop_loss", 0.0)), 2)
        target = round(float(signal.get("target", 0.0)), 2)
        risk_dist = abs(entry_price - initial_sl)
        atr_val = float(signal.get("atr", risk_dist / 1.5 if risk_dist > 0 else entry_price * 0.015))

        position = {
            "id": pos_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "entry_price": round(entry_price, 2),
            "stop_loss": initial_sl,
            "initial_stop_loss": initial_sl,
            "target": target,
            "peak_price": round(entry_price, 2),
            "trailing_stop": initial_sl,
            "is_break_even": 0,
            "atr": round(atr_val, 2),
            "current_price": round(entry_price, 2),
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "predicted_win_prob": round(win_prob, 4),
            "confidence": round(confidence, 4),
            "open_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Save to SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO active_positions (
                        symbol, action, quantity, entry_price, current_price,
                        stop_loss, initial_stop_loss, target, peak_price, trailing_stop,
                        is_break_even, atr, unrealized_pnl, unrealized_pnl_pct,
                        predicted_win_prob, confidence, open_time, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, action, quantity, position["entry_price"], position["current_price"],
                    position["stop_loss"], position["initial_stop_loss"], position["target"],
                    position["peak_price"], position["trailing_stop"], position["is_break_even"],
                    position["atr"], 0.0, 0.0,
                    position["predicted_win_prob"], position["confidence"], position["open_time"],
                    json.dumps(signal)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist open position: {e}")

        self.active_positions[symbol] = position
        logger.info(f"[Paper Trade OPENED] {action} {quantity} {symbol} @ {entry_price:.2f} tokens (SL: {initial_sl}, TP: {target}, Win Prob: {win_prob*100:.1f}%)")
        return {"status": "SUCCESS", "position": position}

    def update_live_price(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Updates open position P&L with live tick and checks for stop-loss, trailing stop, or target hits."""
        if symbol not in self.active_positions or current_price <= 0:
            return None

        pos = self.active_positions[symbol]
        pos["current_price"] = round(current_price, 2)
        
        entry = pos["entry_price"]
        qty = pos["quantity"]
        action = pos["action"]
        initial_sl = pos.get("initial_stop_loss", pos["stop_loss"])
        target = pos["target"]
        atr_val = pos.get("atr", abs(entry - initial_sl) / 1.5 if abs(entry - initial_sl) > 0 else entry * 0.015)
        risk_dist = abs(entry - initial_sl)

        # ----------------------------------------------------
        # BUY Positions Logic (Trailing Stop & Break-Even)
        # ----------------------------------------------------
        if action == "BUY":
            pnl = (current_price - entry) * qty
            pnl_pct = ((current_price - entry) / entry) * 100.0 if entry > 0 else 0.0
            
            # Update Peak High Price
            pos["peak_price"] = max(pos.get("peak_price", entry), current_price)
            
            # 1. Break-Even Ratchet: Trigger when price gains +1.0R profit
            if risk_dist > 0 and current_price >= entry + (BREAK_EVEN_TRIGGER_R * risk_dist):
                if not pos.get("is_break_even"):
                    pos["is_break_even"] = 1
                    pos["trailing_stop"] = max(pos.get("trailing_stop", initial_sl), entry)
                    pos["stop_loss"] = pos["trailing_stop"]
                    logger.info(f"[Break-Even Activated] {symbol} moved to risk-free stop at ₹{entry:.2f}")

            # 2. Dynamic Chandelier/ATR Trailing Stop
            if TRAILING_STOP_ENABLED and atr_val > 0:
                calculated_trail = round(pos["peak_price"] - (TRAILING_STOP_ATR_MULTIPLIER * atr_val), 2)
                current_effective_sl = pos.get("trailing_stop", pos["stop_loss"])
                if calculated_trail > current_effective_sl:
                    pos["trailing_stop"] = calculated_trail
                    pos["stop_loss"] = calculated_trail

            effective_sl = pos.get("trailing_stop", pos["stop_loss"])

            # Check Exit Triggers
            if current_price >= target:
                return self.close_position(symbol, current_price, "TARGET_HIT")
            elif current_price <= effective_sl:
                if effective_sl > entry:
                    reason = "TRAILING_STOP_HIT"
                elif pos.get("is_break_even"):
                    reason = "BREAK_EVEN_HIT"
                else:
                    reason = "STOP_LOSS_HIT"
                return self.close_position(symbol, current_price, reason)
                
        # ----------------------------------------------------
        # SELL Positions Logic (Trailing Stop & Break-Even)
        # ----------------------------------------------------
        elif action == "SELL":
            pnl = (entry - current_price) * qty
            pnl_pct = ((entry - current_price) / entry) * 100.0 if entry > 0 else 0.0
            
            # Update Trough Low Price
            pos["peak_price"] = min(pos.get("peak_price", entry), current_price)
            
            # 1. Break-Even Ratchet: Trigger when price drops +1.0R profit
            if risk_dist > 0 and current_price <= entry - (BREAK_EVEN_TRIGGER_R * risk_dist):
                if not pos.get("is_break_even"):
                    pos["is_break_even"] = 1
                    pos["trailing_stop"] = min(pos.get("trailing_stop", initial_sl), entry)
                    pos["stop_loss"] = pos["trailing_stop"]
                    logger.info(f"[Break-Even Activated] {symbol} moved to risk-free stop at ₹{entry:.2f}")

            # 2. Dynamic Chandelier/ATR Trailing Stop
            if TRAILING_STOP_ENABLED and atr_val > 0:
                calculated_trail = round(pos["peak_price"] + (TRAILING_STOP_ATR_MULTIPLIER * atr_val), 2)
                current_effective_sl = pos.get("trailing_stop", pos["stop_loss"])
                if calculated_trail < current_effective_sl:
                    pos["trailing_stop"] = calculated_trail
                    pos["stop_loss"] = calculated_trail

            effective_sl = pos.get("trailing_stop", pos["stop_loss"])

            # Check Exit Triggers
            if current_price <= target:
                return self.close_position(symbol, current_price, "TARGET_HIT")
            elif current_price >= effective_sl:
                if effective_sl < entry:
                    reason = "TRAILING_STOP_HIT"
                elif pos.get("is_break_even"):
                    reason = "BREAK_EVEN_HIT"
                else:
                    reason = "STOP_LOSS_HIT"
                return self.close_position(symbol, current_price, reason)

        pos["unrealized_pnl"] = round(pnl, 2)
        pos["unrealized_pnl_pct"] = round(pnl_pct, 2)
        return pos

    def close_position(self, symbol: str, exit_price: float, reason: str = "MANUAL_CLOSE", loss_diagnosis: str = "") -> Dict[str, Any]:
        if symbol not in self.active_positions:
            return {"status": "FAILED", "reason": "No active position found"}

        pos = self.active_positions.pop(symbol)
        entry = pos["entry_price"]
        qty = pos["quantity"]
        action = pos["action"]

        if action == "BUY":
            realized_pnl = (exit_price - entry) * qty
        else:
            realized_pnl = (entry - exit_price) * qty

        realized_pnl_pct = (realized_pnl / (entry * qty)) * 100.0 if (entry * qty) > 0 else 0.0
        self.balance += realized_pnl
        self._save_account_state()

        closed_trade = {
            "id": pos.get("id", f"PAPER_{int(time.time()*1000)}"),
            "symbol": symbol,
            "action": action,
            "quantity": qty,
            "entry_price": round(entry, 2),
            "exit_price": round(exit_price, 2),
            "stop_loss": round(pos.get("stop_loss", 0.0), 2),
            "target": round(pos.get("target", 0.0), 2),
            "realized_pnl": round(realized_pnl, 2),
            "realized_pnl_pct": round(realized_pnl_pct, 2),
            "close_reason": reason,
            "open_time": pos.get("open_time", time.strftime("%Y-%m-%d %H:%M:%S")),
            "close_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "predicted_win_prob": pos.get("predicted_win_prob", 0.0),
            "confidence": pos.get("confidence", 0.0),
            "loss_diagnosis": loss_diagnosis
        }

        # Update SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM active_positions WHERE symbol = ?", (symbol,))
                cursor.execute("""
                    INSERT INTO trade_history (
                        id, symbol, action, quantity, entry_price, exit_price,
                        stop_loss, target, realized_pnl, realized_pnl_pct,
                        close_reason, open_time, close_time, predicted_win_prob,
                        confidence, loss_diagnosis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    closed_trade["id"], symbol, action, qty, entry, exit_price,
                    closed_trade["stop_loss"], closed_trade["target"],
                    closed_trade["realized_pnl"], closed_trade["realized_pnl_pct"],
                    reason, closed_trade["open_time"], closed_trade["close_time"],
                    closed_trade["predicted_win_prob"], closed_trade["confidence"],
                    loss_diagnosis
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error persisting closed trade: {e}")

        self.trade_history.append(closed_trade)
        logger.info(f"[Paper Trade CLOSED] {symbol} @ {exit_price:.2f} | Reason: {reason} | PnL: {realized_pnl:+.2f} Tokens")
        return {"status": "CLOSED", "trade": closed_trade}

    def get_summary(self) -> Dict[str, Any]:
        total_unrealized_pnl = sum(p.get("unrealized_pnl", 0.0) for p in self.active_positions.values())
        total_equity = self.balance + total_unrealized_pnl
        total_pnl = total_equity - self.initial_balance
        pnl_pct = (total_pnl / self.initial_balance) * 100.0 if self.initial_balance > 0 else 0.0

        return {
            "cash_balance": round(self.balance, 2),
            "total_equity": round(total_equity, 2),
            "initial_balance": round(self.initial_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(pnl_pct, 2),
            "active_positions_count": len(self.active_positions),
            "active_positions": list(self.active_positions.values()),
            "closed_trades_count": len(self.trade_history),
            "closed_trades": self.trade_history[-20:] # Return last 20 closed trades
        }

    def reset_account(self, tokens: float = INITIAL_ACCOUNT_BALANCE):
        """Resets account balance and wipes active positions for clean testing."""
        self.initial_balance = float(tokens)
        self.balance = float(tokens)
        self.active_positions.clear()
        self.trade_history.clear()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM active_positions")
                cursor.execute("DELETE FROM trade_history")
                cursor.execute("UPDATE account_state SET balance = ?, initial_balance = ? WHERE id = 1", (tokens, tokens))
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting database: {e}")

# Global Instance
paper_trader = PaperTrader()
