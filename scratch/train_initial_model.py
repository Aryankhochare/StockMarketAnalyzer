import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai_engine.model_trainer import ModelTrainer
from data_bridge.data_manager import data_manager

def main():
    print("Fetching benchmark historical candles for NIFTY 50...")
    df = data_manager.get_historical_candles("^NSEI", period="1y", interval="1d")
    if df.empty:
        print("Fallback: Creating synthetic benchmark candles for model training...")
        import pandas as pd
        import numpy as np
        dates = pd.date_range(start="2025-01-01", periods=250, freq="D")
        np.random.seed(42)
        close = 24000.0 + np.cumsum(np.random.randn(250) * 100)
        df = pd.DataFrame({
            "timestamp": dates,
            "open": close + np.random.randn(250) * 20,
            "high": close + np.abs(np.random.randn(250) * 50),
            "low": close - np.abs(np.random.randn(250) * 50),
            "close": close,
            "volume": np.random.randint(100000, 1000000, size=250)
        })

    trainer = ModelTrainer()
    res = trainer.train_model(df)
    print("Training result:", res)

if __name__ == "__main__":
    main()
