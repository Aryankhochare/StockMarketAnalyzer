import pytest
import pandas as pd
import numpy as np
from ai_engine.ensemble_model import CalibratedEnsembleModel
from tests.test_features import create_sample_candles

def test_calibrated_ensemble_training_and_prediction():
    ensemble = CalibratedEnsembleModel()
    df = create_sample_candles(60)

    # Train model
    res = ensemble.train_and_calibrate(df)
    assert res["status"] == "SUCCESS"

    # Inference test
    from quant_engine.feature_store import FeatureStore
    store = FeatureStore()
    _, df_feat = store.build_features(df)
    
    p_bear, p_flat, p_bull = ensemble.predict_proba(df_feat.iloc[-1:])

    assert 0.0 <= p_bear <= 1.0
    assert 0.0 <= p_flat <= 1.0
    assert 0.0 <= p_bull <= 1.0
    assert abs((p_bear + p_flat + p_bull) - 1.0) < 0.01
