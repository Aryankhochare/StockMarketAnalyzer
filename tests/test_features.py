import pytest
import pandas as pd
import numpy as np
from quant_engine.technical_features import TechnicalFeatureExtractor
from quant_engine.feature_store import FeatureStore

def create_sample_candles(n: int = 50) -> pd.DataFrame:
    dates = pd.date_range(start="2026-01-01", periods=n, freq="D")
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(n))
    high = close + np.random.rand(n) * 2.0
    low = close - np.random.rand(n) * 2.0
    open_p = close + np.random.randn(n) * 0.5
    volume = np.random.randint(1000, 50000, size=n)

    return pd.DataFrame({
        "timestamp": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })

def test_technical_feature_computation():
    extractor = TechnicalFeatureExtractor()
    df = create_sample_candles(50)
    df_features = extractor.compute_all_features(df)

    assert "rsi_14" in df_features.columns
    assert "macd" in df_features.columns
    assert "atr_14" in df_features.columns
    assert "vwap" in df_features.columns
    assert len(df_features) == 50
    assert not df_features["rsi_14"].isna().any()

def test_feature_store_matrix():
    store = FeatureStore()
    df = create_sample_candles(50)
    df_full, df_features = store.build_features(df, {"pcr": 1.2})

    assert not df_features.empty
    assert "pcr" in df_features.columns
    assert df_features["pcr"].iloc[-1] == 1.2
