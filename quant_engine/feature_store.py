import pandas as pd
from typing import Optional, Dict, Any, Tuple
from quant_engine.technical_features import TechnicalFeatureExtractor
from quant_engine.derivatives_features import DerivativesFeatureExtractor
from quant_engine.multi_timeframe import MultiTimeframeAnalyzer
from quant_engine.candlestick_patterns import CandlestickPatternExtractor

FEATURE_COLUMNS = [
    'return_1d', 'return_5d', 'return_20d',
    'dist_ema_20', 'dist_ema_50',
    'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'atr_pct', 'bb_width', 'bb_position',
    'dist_vwap', 'vol_ratio', 'volatility_20d',
    'pcr', 'pcr_sentiment', 'mtf_score', 'catalyst_score',
    'body_ratio', 'upper_wick_ratio', 'lower_wick_ratio',
    'range_expansion_ratio', 'candle_pattern_score'
]

class FeatureStore:
    """
    Unified Feature Store.
    Generates point-in-time normalized feature matrix for model training and real-time inference.
    """
    def __init__(self):
        self.tech_extractor = TechnicalFeatureExtractor()
        self.deriv_extractor = DerivativesFeatureExtractor()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.candle_extractor = CandlestickPatternExtractor()

    def build_features(
        self,
        df: pd.DataFrame,
        option_snapshot: Optional[Dict[str, Any]] = None,
        catalyst_score: float = 0.0
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if df.empty or len(df) < 15:
            return pd.DataFrame(), pd.DataFrame()

        # Step 1: Compute technical features
        df_full = self.tech_extractor.compute_all_features(df)

        # Step 2: Compute candlestick pattern features & geometric ratios
        df_full = self.candle_extractor.compute_pattern_features(df_full)

        # Step 3: Extract derivatives features
        deriv_features = self.deriv_extractor.extract_option_features(option_snapshot)
        for key, val in deriv_features.items():
            df_full[key] = val

        # Step 4: MTF & News Catalyst features
        mtf_res = self.mtf_analyzer.analyze_alignment(df_full)
        df_full['mtf_score'] = mtf_res['mtf_score']
        df_full['catalyst_score'] = catalyst_score

        # Step 5: Extract feature matrix for ML
        available_cols = [c for c in FEATURE_COLUMNS if c in df_full.columns]
        df_features = df_full[available_cols].copy()

        return df_full, df_features
