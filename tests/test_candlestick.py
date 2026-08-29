import pytest
import pandas as pd
from quant_engine.candlestick_patterns import CandlestickPatternExtractor
from tests.test_features import create_sample_candles

def test_candlestick_microstructure_and_patterns():
    extractor = CandlestickPatternExtractor()
    df = create_sample_candles(50)

    df_patterns = extractor.compute_pattern_features(df)

    assert "body_ratio" in df_patterns.columns
    assert "upper_wick_ratio" in df_patterns.columns
    assert "lower_wick_ratio" in df_patterns.columns
    assert "range_expansion_ratio" in df_patterns.columns
    assert "candle_pattern_score" in df_patterns.columns

    # Verify ratios are bounded between 0 and 1
    assert (df_patterns["body_ratio"] >= 0.0).all()
    assert (df_patterns["body_ratio"] <= 1.0).all()
