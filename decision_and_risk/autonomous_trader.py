import asyncio
import logging
from typing import Dict, Any
from config import (
    DEFAULT_WATCHLIST,
    AUTONOMOUS_TRADING_ENABLED,
    AUTONOMOUS_SCAN_INTERVAL_SECONDS,
    MAX_CONCURRENT_POSITIONS
)
from data_bridge.data_manager import data_manager
from data_bridge.market_calendar import market_calendar
from decision_and_risk.decision_engine import decision_engine
from decision_and_risk.paper_trader import paper_trader
from ai_engine.loss_analyzer import loss_analyzer
from ai_engine.ensemble_model import ensemble_model
from quant_engine.news_event_engine import news_event_engine
from data_bridge.telegram_service import telegram_service

logger = logging.getLogger("AutonomousTrader")

class AutonomousTrader:
    """
    24/7 Autonomous Paper Trading Daemon.
    Continuously scans market symbols in the background, evaluates AI signals,
    executes paper trades automatically, tracks open positions, runs loss post-mortems,
    and sends Telegram alerts without requiring any manual interaction.
    """
    def __init__(self):
        self.is_active = AUTONOMOUS_TRADING_ENABLED
        self.scan_interval = AUTONOMOUS_SCAN_INTERVAL_SECONDS
        self.max_concurrent_positions = MAX_CONCURRENT_POSITIONS
        self.task: asyncio.Task = None
        self.last_scan_time = ""

    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._trading_loop())
            logger.info("Autonomous Trading Daemon started.")

    def stop(self):
        self.is_active = False
        if self.task and not self.task.done():
            self.task.cancel()
            logger.info("Autonomous Trading Daemon stopped.")

    def toggle(self) -> bool:
        self.is_active = not self.is_active
        logger.info(f"Autonomous Trading active status changed to: {self.is_active}")
        return self.is_active

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "scan_interval_seconds": self.scan_interval,
            "max_concurrent_positions": self.max_concurrent_positions,
            "current_open_positions": len(paper_trader.active_positions),
            "last_scan_time": self.last_scan_time
        }

    async def _trading_loop(self):
        import time
        logger.info("Entering 24/7 Autonomous Trading & Offline Learning Engine...")
        last_learning_time = 0

        while True:
            try:
                if not self.is_active:
                    await asyncio.sleep(5)
                    continue

                session_info = market_calendar.get_session_status()
                is_open = session_info["is_open"]
                self.last_scan_time = time.strftime("%Y-%m-%d %H:%M:%S")

                # =========================================================================
                # 🌙 1. OFFLINE / WEEKEND MODE (Market Closed) -> Self-Learning & Research
                # =========================================================================
                if not is_open:
                    now_ts = time.time()
                    # Run self-learning cycle every 10 minutes (600s) during off-hours
                    if now_ts - last_learning_time >= 600:
                        last_learning_time = now_ts
                        logger.info(f"[{session_info['status']}] Running Autonomous Offline Self-Learning & Research Cycle...")
                        try:
                            # 1. News & Event scanning for Monday / next opening catalysts
                            news_event_engine.analyze_headlines()
                            
                            # 2. Historical loss analysis review & dynamic penalty consolidation
                            loss_diagnostics = loss_analyzer.get_all_loss_diagnostics()
                            
                            # 3. Model recalibration on latest historical candles
                            df_hist = data_manager.get_historical_candles("^NSEI", period="1y", interval="1d")
                            if not df_hist.empty:
                                ensemble_model.train_and_calibrate(df_hist)
                            
                            logger.info(f"Offline Learning Cycle Complete: Refined penalties from {len(loss_diagnostics)} historical loss patterns.")
                        except Exception as learn_err:
                            logger.debug(f"Offline learning task notice: {learn_err}")

                    await asyncio.sleep(60) # Sleep 1 minute before checking session status again
                    continue

                # =========================================================================
                # ☀️ 2. LIVE MARKET HOURS (09:15 AM - 03:30 PM IST) -> Live Execution
                # =========================================================================
                vix_snapshot = data_manager.get_india_vix_snapshot()
                
                for item in DEFAULT_WATCHLIST:
                    symbol = item["symbol"]
                    ticker = item.get("ticker", symbol)

                    try:
                        # 1. Fetch latest data
                        df = data_manager.get_latest_data(symbol, ticker)
                        if df.empty or len(df) < 15:
                            continue

                        latest_close = float(df.iloc[-1]["close"])

                        # 2. If position is already open for this symbol, update live price & check exits
                        if symbol in paper_trader.active_positions:
                            updated = paper_trader.update_live_price(symbol, latest_close)
                            if updated and updated.get("status") == "CLOSED":
                                closed_trade = updated["trade"]
                                # If trade was a loss, run AI post-mortem diagnosis
                                if closed_trade.get("realized_pnl", 0.0) <= 0:
                                    diagnosis = loss_analyzer.diagnose_loss(closed_trade, df)
                                    closed_trade["loss_diagnosis"] = diagnosis
                                
                                # Send Telegram Alert
                                telegram_service.notify_trade_closed(closed_trade)
                            continue

                        # 3. If under max concurrent positions limit, evaluate new AI trade opportunity
                        if len(paper_trader.active_positions) < self.max_concurrent_positions:
                            option_snapshot = data_manager.get_option_chain_snapshot(symbol)
                            signal = decision_engine.evaluate_trade(symbol, df, option_snapshot, vix_snapshot)

                            action = signal.get("action")
                            if action in ["BUY", "SELL"]:
                                logger.info(f"Autonomous signal triggered for {symbol}: {action} | Win Prob: {signal.get('win_prob_pct')}%")
                                result = paper_trader.open_position(signal)
                                
                                if result.get("status") == "SUCCESS":
                                    pos = result["position"]
                                    telegram_service.notify_trade_opened(pos)

                    except Exception as sym_err:
                        logger.debug(f"Error processing symbol {symbol} in autonomous loop: {sym_err}")

                    await asyncio.sleep(1.5) # Gentle pause between symbols

                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Autonomous Trading loop: {e}")
                await asyncio.sleep(self.scan_interval)

autonomous_trader = AutonomousTrader()
