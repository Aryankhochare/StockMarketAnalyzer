import pandas as pd
from typing import Dict, Any

class RelativeStrengthAnalyzer:
    """
    Relative Strength & Sector Outperformance Analyzer.
    Measures individual stock momentum vs NIFTY benchmark.
    """
    def calculate_relative_strength(self, df_stock: pd.DataFrame, df_benchmark: pd.DataFrame) -> Dict[str, Any]:
        if df_stock.empty or df_benchmark.empty or len(df_stock) < 10:
            return {"rs_score": 0.0, "status": "NEUTRAL"}

        stock_ret_5d = float(df_stock.iloc[-1].get("return_5d", 0.0))
        bench_ret_5d = float(df_benchmark.iloc[-1].get("return_5d", 0.0)) if "return_5d" in df_benchmark.columns else 0.0

        diff = stock_ret_5d - bench_ret_5d

        if diff > 0.02:
            rs_score = 1.0  # Strong Outperformer
            status = "OUTPERFORMING"
        elif diff < -0.02:
            rs_score = -1.0 # Underperformer
            status = "UNDERPERFORMING"
        else:
            rs_score = 0.0
            status = "MATCHING_BENCHMARK"

        return {
            "rs_score": rs_score,
            "status": status,
            "alpha_5d_pct": round(diff * 100, 2)
        }
