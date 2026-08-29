import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from decision_and_risk.decision_engine import decision_engine
from config import INITIAL_ACCOUNT_BALANCE

logger = logging.getLogger("WalkForwardBacktester")

class WalkForwardBacktester:
    """
    Chronological Walk-Forward Backtester.
    Simulates trading decisions step-by-step over historical candles with fee/slippage modeling.
    Calculates Sharpe Ratio, Sortino Ratio, Win Rate %, Profit Factor, and Max Drawdown.
    """
    def run_backtest(
        self,
        symbol: str,
        df_candles: pd.DataFrame,
        initial_capital: float = INITIAL_ACCOUNT_BALANCE
    ) -> Dict[str, Any]:
        if df_candles.empty or len(df_candles) < 30:
            return {"status": "FAILED", "reason": "Insufficient candles for backtest"}

        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown_pct = 0.0

        trades: List[Dict[str, Any]] = []
        equity_curve: List[float] = [capital]

        min_window = 20
        total_bars = len(df_candles)

        for i in range(min_window, total_bars - 1):
            slice_df = df_candles.iloc[:i]
            current_bar = df_candles.iloc[i]
            next_bar = df_candles.iloc[i + 1]

            # Evaluate decision engine
            sig = decision_engine.evaluate_trade(symbol, slice_df)
            action = sig.get("action")

            if action in ["BUY", "SELL"]:
                entry_price = float(current_bar["close"])
                exit_price = float(next_bar["close"])
                qty = sig.get("quantity", 1)

                if action == "BUY":
                    pnl = (exit_price - entry_price) * qty
                else:
                    pnl = (entry_price - exit_price) * qty

                # Deduct transaction fees & slippage (~0.13%)
                fees = (entry_price * qty * 0.0013)
                net_pnl = pnl - fees
                capital += net_pnl

                trades.append({
                    "bar_index": i,
                    "action": action,
                    "entry": entry_price,
                    "exit": exit_price,
                    "net_pnl": round(net_pnl, 2),
                    "win": net_pnl > 0
                })

            equity_curve.append(capital)
            if capital > peak_capital:
                peak_capital = capital
            
            dd = (peak_capital - capital) / peak_capital
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

        # Compute Performance Summary
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["win"]]
        losing_trades = [t for t in trades if not t["win"]]

        win_rate_pct = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0
        
        gross_profit = sum(t["net_pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["net_pnl"] for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        # Returns analysis
        returns = pd.Series(equity_curve).pct_change().dropna()
        mean_ret = returns.mean()
        std_ret = returns.std()
        downside_std = returns[returns < 0].std()

        sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        sortino = (mean_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
        cagr_pct = ((capital - initial_capital) / initial_capital) * 100.0

        return {
            "symbol": symbol,
            "status": "SUCCESS",
            "total_bars_evaluated": total_bars - min_window,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate_pct": round(win_rate_pct, 2),
            "profit_factor": round(profit_factor, 2),
            "final_equity": round(capital, 2),
            "total_return_pct": round(cagr_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct * 100.0, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2)
        }

# Global Instance
walk_forward_backtester = WalkForwardBacktester()
