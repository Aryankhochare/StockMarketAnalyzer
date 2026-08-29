import os
import joblib
import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit
from quant_engine.feature_store import FeatureStore, FEATURE_COLUMNS
from config import MODELS_DIR

logger = logging.getLogger("ModelTrainer")

MODEL_FILE = MODELS_DIR / "stock_ai_model.pkl"

class ModelTrainer:
    """
    Quantitative AI Model Trainer.
    Trains Gradient Boosting models on historical point-in-time features to predict
    future directional return classes:
    0: BEARISH (Return < -0.5%)
    1: NEUTRAL/FLAT (-0.5% <= Return <= +0.5%)
    2: BULLISH (Return > +0.5%)
    """
    def __init__(self):
        self.feature_store = FeatureStore()

    def prepare_training_data(self, df_raw: pd.DataFrame, forward_period: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """Calculates features and creates forward return labels."""
        if df_raw.empty or len(df_raw) < 50:
            return pd.DataFrame(), pd.Series(dtype=int)

        df_full, df_features = self.feature_store.build_features(df_raw)
        
        # Calculate forward return target
        future_close = df_full['close'].shift(-forward_period)
        future_return = (future_close - df_full['close']) / df_full['close']
        
        # Create discrete 3-class target: 0 (BEAR), 1 (FLAT), 2 (BULL)
        conditions = [
            (future_return < -0.005),
            (future_return >= -0.005) & (future_return <= 0.005),
            (future_return > 0.005)
        ]
        choices = [0, 1, 2] # 0: Bear, 1: Flat, 2: Bull
        y = pd.Series(np.select(conditions, choices, default=1), index=df_full.index)

        # Drop last `forward_period` rows where target is NaN
        valid_mask = ~future_return.isna()
        X = df_features[valid_mask]
        y = y[valid_mask]

        return X, y

    def train_model(self, df_historical: pd.DataFrame) -> Dict[str, Any]:
        """Trains HistGradientBoostingClassifier and saves weights to disk."""
        X, y = self.prepare_training_data(df_historical)
        if X.empty or len(X) < 30:
            logger.warning("Insufficient data to train AI model.")
            return {"status": "FAILED", "reason": "Insufficient data"}

        # Time series cross validation split
        tscv = TimeSeriesSplit(n_splits=3)
        train_scores = []

        model = HistGradientBoostingClassifier(
            max_iter=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )

        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model.fit(X_tr, y_tr)
            score = model.score(X_val, y_val)
            train_scores.append(score)

        # Final fit on full historical data
        model.fit(X, y)

        # Save trained weights
        joblib.dump({"model": model, "feature_names": list(X.columns)}, MODEL_FILE)
        logger.info(f"AI Model trained successfully. Avg Validation Accuracy: {np.mean(train_scores):.4f}")

        return {
            "status": "SUCCESS",
            "val_accuracy": round(float(np.mean(train_scores)), 4),
            "samples": len(X),
            "model_path": str(MODEL_FILE)
        }
