import pandas as pd
from typing import Dict, Any, Optional

class DerivativesFeatureExtractor:
    """
    Derivatives and Options sentiment feature extractor.
    Processes Put-Call Ratio (PCR), Open Interest (OI) concentration,
    and Futures Basis.
    """
    @staticmethod
    def extract_option_features(option_snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
        if not option_snapshot:
            return {
                "pcr": 1.0,
                "pcr_sentiment": 0.0,
                "total_call_oi": 0.0,
                "total_put_oi": 0.0
            }

        pcr = float(option_snapshot.get("pcr", 1.0))
        
        # Determine sentiment score based on standard Indian market PCR ranges:
        # PCR > 1.2 => Extremely Bullish / Oversold put writing
        # 0.8 <= PCR <= 1.2 => Neutral
        # PCR < 0.8 => Bearish / Call writing dominance
        if pcr >= 1.25:
            sentiment = 1.0  # Strong Bullish
        elif pcr >= 1.0:
            sentiment = 0.5  # Mild Bullish
        elif pcr >= 0.75:
            sentiment = -0.5 # Mild Bearish
        else:
            sentiment = -1.0 # Strong Bearish

        return {
            "pcr": round(pcr, 4),
            "pcr_sentiment": sentiment,
            "total_call_oi": float(option_snapshot.get("totalCallOI", 0)),
            "total_put_oi": float(option_snapshot.get("totalPutOI", 0))
        }
