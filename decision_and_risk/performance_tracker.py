import logging
from typing import Dict, Any, List
from decision_and_risk.paper_trader import paper_trader
from ai_engine.loss_analyzer import loss_analyzer

logger = logging.getLogger("PerformanceTracker")

class PerformanceTracker:
    """
    Win-Probability Calibration & Trading Performance Analytics Engine.
    Tracks live forward-test win rates, calibration curves, equity growth,
    profit factors, and loss post-mortems over time.
    """
    def get_performance_metrics(self) -> Dict[str, Any]:
        trades = paper_trader.trade_history
        total_trades = len(trades)
        
        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "avg_predicted_win_prob": 0.0,
                "calibration_gap_pct": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "current_balance": paper_trader.balance,
                "initial_balance": paper_trader.initial_balance,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "payoff_ratio": 0.0,
                "equity_curve": [{"time": "Start", "equity": paper_trader.initial_balance, "pnl": 0.0}],
                "calibration_buckets": [],
                "recent_trades": [],
                "loss_diagnostics": loss_analyzer.get_all_loss_diagnostics()
            }

        winning_trades = [t for t in trades if t.get("realized_pnl", 0.0) > 0]
        losing_trades = [t for t in trades if t.get("realized_pnl", 0.0) <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate_pct = round((win_count / total_trades) * 100.0, 1)

        # Average Predicted Probability
        pred_probs = [t.get("predicted_win_prob", 0.65) for t in trades]
        avg_pred_prob = (sum(pred_probs) / len(pred_probs)) if pred_probs else 0.65
        avg_pred_prob_pct = round(avg_pred_prob * 100.0, 1)
        calibration_gap = round(win_rate_pct - avg_pred_prob_pct, 1)

        # P&L Calculations
        total_pnl = round(sum(t.get("realized_pnl", 0.0) for t in trades), 2)
        total_pnl_pct = round((total_pnl / paper_trader.initial_balance) * 100.0, 2) if paper_trader.initial_balance > 0 else 0.0

        gross_profit = sum(t.get("realized_pnl", 0.0) for t in winning_trades)
        gross_loss = abs(sum(t.get("realized_pnl", 0.0) for t in losing_trades))

        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)
        avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0
        payoff_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0

        # Build Equity Growth Curve
        equity_curve = [{"time": "Start", "equity": paper_trader.initial_balance, "pnl": 0.0}]
        running_equity = paper_trader.initial_balance
        for t in trades:
            running_equity += t.get("realized_pnl", 0.0)
            equity_curve.append({
                "time": t.get("close_time", "")[-8:] if t.get("close_time") else "Trade",
                "equity": round(running_equity, 2),
                "pnl": t.get("realized_pnl", 0.0),
                "symbol": t.get("symbol", "")
            })

        # Probability Calibration Buckets
        buckets = {
            "50-60%": {"pred_sum": 0.0, "wins": 0, "total": 0},
            "60-70%": {"pred_sum": 0.0, "wins": 0, "total": 0},
            "70-80%": {"pred_sum": 0.0, "wins": 0, "total": 0},
            "80-100%": {"pred_sum": 0.0, "wins": 0, "total": 0},
        }

        for t in trades:
            prob = t.get("predicted_win_prob", 0.65)
            is_win = 1 if t.get("realized_pnl", 0.0) > 0 else 0

            if 0.50 <= prob < 0.60:
                b = buckets["50-60%"]
            elif 0.60 <= prob < 0.70:
                b = buckets["60-70%"]
            elif 0.70 <= prob < 0.80:
                b = buckets["70-80%"]
            else:
                b = buckets["80-100%"]

            b["pred_sum"] += prob
            b["wins"] += is_win
            b["total"] += 1

        calibration_data = []
        for name, data in buckets.items():
            if data["total"] > 0:
                calibration_data.append({
                    "bucket": name,
                    "count": data["total"],
                    "avg_predicted": round((data["pred_sum"] / data["total"]) * 100.0, 1),
                    "actual_win_rate": round((data["wins"] / data["total"]) * 100.0, 1)
                })

        return {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate_pct": win_rate_pct,
            "avg_predicted_win_prob": avg_pred_prob_pct,
            "calibration_gap_pct": calibration_gap,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "current_balance": round(paper_trader.balance, 2),
            "initial_balance": round(paper_trader.initial_balance, 2),
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "payoff_ratio": payoff_ratio,
            "equity_curve": equity_curve,
            "calibration_buckets": calibration_data,
            "recent_trades": trades[-50:], # Last 50 trades
            "loss_diagnostics": loss_analyzer.get_all_loss_diagnostics()
        }

performance_tracker = PerformanceTracker()
