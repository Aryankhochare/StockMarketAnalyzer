import os
import joblib
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
from quant_engine.feature_store import FeatureStore
from config import MODELS_DIR

logger = logging.getLogger("EnsembleModel")
ENSEMBLE_FILE = MODELS_DIR / "calibrated_ensemble_model.pkl"

class CalibratedEnsembleModel:
    """
    Multi-Model Voting Ensemble & Probability Calibration Engine.
    Combines HistGradientBoosting + RandomForest with CalibratedClassifierCV
    to guarantee reliable, empirical win-probability predictions.
    """
    def __init__(self):
        self.feature_store = FeatureStore()
        self.calibrated_model = None
        self._load_model()

    def _load_model(self):
        try:
            if ENSEMBLE_FILE.exists():
                artifact = joblib.load(ENSEMBLE_FILE)
                self.calibrated_model = artifact.get("model")
                logger.info("Calibrated Ensemble Model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading Calibrated Ensemble Model: {e}")

    def prepare_training_data(self, df_raw: pd.DataFrame, forward_period: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        if df_raw.empty or len(df_raw) < 50:
            return pd.DataFrame(), pd.Series(dtype=int)

        df_full, df_features = self.feature_store.build_features(df_raw)
        
        future_close = df_full['close'].shift(-forward_period)
        future_return = (future_close - df_full['close']) / df_full['close']
        
        conditions = [
            (future_return < -0.005),
            (future_return >= -0.005) & (future_return <= 0.005),
            (future_return > 0.005)
        ]
        choices = [0, 1, 2] # 0: Bear, 1: Flat, 2: Bull
        y = pd.Series(np.select(conditions, choices, default=1), index=df_full.index)

        valid_mask = ~future_return.isna()
        X = df_features[valid_mask]
        y = y[valid_mask]

        return X, y

    def train_and_calibrate(self, df_historical: pd.DataFrame) -> Dict[str, Any]:
        """Trains Multi-Model Voting Ensemble and calibrates probabilities."""
        X, y = self.prepare_training_data(df_historical)
        if X.empty or len(X) < 40:
            return {"status": "FAILED", "reason": "Insufficient historical data"}

        # Base Estimators for Voting Ensemble
        m1 = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.05, max_depth=5, random_state=42)
        m2 = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)

        ensemble = VotingClassifier(
            estimators=[('hgb', m1), ('rf', m2)],
            voting='soft'
        )

        # Calibrated Classifier
        calibrated = CalibratedClassifierCV(estimator=ensemble, method='sigmoid', cv=3)
        calibrated.fit(X, y)

        self.calibrated_model = calibrated

        # Save artifact
        joblib.dump({"model": calibrated, "features": list(X.columns)}, ENSEMBLE_FILE)
        logger.info(f"Calibrated Ensemble Model trained on {len(X)} samples.")

        return {
            "status": "SUCCESS",
            "samples": len(X),
            "model_file": str(ENSEMBLE_FILE)
        }

    def predict_proba(self, X_features: pd.DataFrame) -> Tuple[float, float, float]:
        """Returns calibrated probabilities (prob_bear, prob_flat, prob_bull)."""
        if self.calibrated_model is None or X_features.empty:
            return 0.33, 0.34, 0.33

        try:
            probs = self.calibrated_model.predict_proba(X_features)[0]
            classes = self.calibrated_model.classes_
            
            prob_dict = {cls: prob for cls, prob in zip(classes, probs)}
            prob_bear = float(prob_dict.get(0, 0.33))
            prob_flat = float(prob_dict.get(1, 0.34))
            prob_bull = float(prob_dict.get(2, 0.33))
            
            return prob_bear, prob_flat, prob_bull
        except Exception as e:
            logger.error(f"Ensemble inference error: {e}")
            return 0.33, 0.34, 0.33

# Global Instance
ensemble_model = CalibratedEnsembleModel()
