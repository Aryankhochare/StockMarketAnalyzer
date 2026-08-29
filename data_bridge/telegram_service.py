import logging
import asyncio
import requests
from typing import Dict, Any, Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED

logger = logging.getLogger("TelegramService")

class TelegramService:
    """
    Telegram Bot Notification Service.
    Dispatches formatted alerts to your smartphone for trade entries, target hits,
    stop-loss hits, loss diagnostics, and daily performance summaries.
    """
    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage" if self.enabled else ""
        if self.enabled:
            logger.info("Telegram Bot Service initialized and active.")
        else:
            logger.info("Telegram Bot Service is disabled (Token or Chat ID not provided).")

    def send_message_sync(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            res = requests.post(self.api_url, json=payload, timeout=5)
            if res.status_code == 200:
                return True
            else:
                logger.warning(f"Telegram API error: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            logger.debug(f"Telegram send error: {e}")
            return False

    async def send_message_async(self, text: str):
        if not self.enabled:
            return
        await asyncio.to_thread(self.send_message_sync, text)

    def notify_trade_opened(self, pos: Dict[str, Any]):
        symbol = pos.get("symbol", "UNKNOWN")
        action = pos.get("action", "BUY")
        qty = pos.get("quantity", 0)
        entry = pos.get("entry_price", 0.0)
        sl = pos.get("stop_loss", 0.0)
        target = pos.get("target", 0.0)
        win_prob = pos.get("predicted_win_prob", 0.0) * 100.0

        icon = "🟢" if action == "BUY" else "🔴"
        msg = (
            f"{icon} *AI TRADE OPENED: {action} {symbol}*\n\n"
            f"• *Quantity:* {qty}\n"
            f"• *Entry Price:* {entry:.2f} tokens\n"
            f"• *Target (TP):* {target:.2f} tokens\n"
            f"• *Stop Loss (SL):* {sl:.2f} tokens\n"
            f"• *AI Win Probability:* {win_prob:.1f}%\n"
            f"• *Time:* {pos.get('open_time', '')}\n\n"
            f"_Autonomous trading daemon active in cloud._"
        )
        self.send_message_sync(msg)

    def notify_trade_closed(self, trade: Dict[str, Any]):
        symbol = trade.get("symbol", "UNKNOWN")
        action = trade.get("action", "BUY")
        exit_price = trade.get("exit_price", 0.0)
        pnl = trade.get("realized_pnl", 0.0)
        pnl_pct = trade.get("realized_pnl_pct", 0.0)
        reason = trade.get("close_reason", "MANUAL")
        diagnosis = trade.get("loss_diagnosis", "")

        if reason == "TARGET_HIT" or pnl > 0:
            header = "🎯 *TRADE WIN: TARGET HIT!*"
            status_icon = "✅"
        else:
            header = "🛑 *TRADE LOSS: STOP-LOSS HIT!*"
            status_icon = "❌"

        msg = (
            f"{status_icon} {header}\n\n"
            f"• *Symbol:* {symbol} ({action})\n"
            f"• *Exit Price:* {exit_price:.2f} tokens\n"
            f"• *Realized P&L:* {pnl:+.2f} tokens ({pnl_pct:+.2f}%)\n"
            f"• *Close Reason:* {reason}\n"
            f"• *Time:* {trade.get('close_time', '')}\n"
        )

        if diagnosis:
            msg += f"\n🧠 *AI Loss Diagnostic & Learning:*\n_{diagnosis}_\n"

        self.send_message_sync(msg)

    def notify_daily_summary(self, summary: Dict[str, Any]):
        equity = summary.get("total_equity", 0.0)
        cash = summary.get("cash_balance", 0.0)
        pnl = summary.get("total_pnl", 0.0)
        pnl_pct = summary.get("total_pnl_pct", 0.0)
        active_cnt = summary.get("active_positions_count", 0)
        closed_cnt = summary.get("closed_trades_count", 0)

        icon = "📈" if pnl >= 0 else "📉"
        msg = (
            f"{icon} *AI 24/7 PAPER TRADING SUMMARY*\n\n"
            f"• *Current Equity:* {equity:.2f} tokens\n"
            f"• *Cash Balance:* {cash:.2f} tokens\n"
            f"• *Total P&L:* {pnl:+.2f} tokens ({pnl_pct:+.2f}%)\n"
            f"• *Active Open Trades:* {active_cnt}\n"
            f"• *Total Completed Trades:* {closed_cnt}\n\n"
            f"Check dashboard /analytics for detailed calibration curves."
        )
        self.send_message_sync(msg)

telegram_service = TelegramService()
