import re
import logging
from typing import List, Dict, Any, Optional
from data_bridge.news_fetcher import news_fetcher

logger = logging.getLogger("NewsEventEngine")

# Keywords for Event Structuring
SECTOR_MAP = {
    "IT": ["tcs", "infosys", "infy", "wipro", "hcltech", "techm", "software", "it sector"],
    "BANKING": ["hdfc", "icici", "sbin", "sbi", "axis", "kotak", "rbi", "bank", "nbfc"],
    "AUTO": ["tatamotors", "maruti", "mahindra", "m&m", "auto", "ev sales", "vehicle"],
    "ENERGY": ["reliance", "ongc", "ntpc", "powergrid", "oil", "gas", "energy"],
    "PHARMA": ["sunpharma", "cipla", "drreddy", "pharma", "fda", "drug"]
}

BULLISH_KEYWORDS = ["profit up", "revenue surges", "order win", "contract", "gains", "record high", "upgrade", "growth", "secures", "approval"]
BEARISH_KEYWORDS = ["penalty", "investigation", "sebi", "fda warning", "profit falls", "downgrade", "decline", "resigns", "lawsuit", "loss"]

class NewsEventEngine:
    """
    Structured Live News & Event Catalyst Engine.
    Transforms unstructured financial headlines into structured sector & stock catalysts.
    """
    def __init__(self):
        self.cached_catalysts: Dict[str, Dict[str, Any]] = {}

    def analyze_headlines(self, headlines: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """Parses headlines and returns catalyst scores per symbol/sector."""
        if headlines is None:
            headlines = news_fetcher.fetch_latest_headlines()

        catalysts: Dict[str, Dict[str, Any]] = {}

        for item in headlines:
            text = item.get("headline", "").lower()
            if not text:
                continue

            # Determine Bullish / Bearish Sentiment & Severity
            score = 0.0
            event_type = "GENERAL_NEWS"

            for kw in BULLISH_KEYWORDS:
                if kw in text:
                    score += 0.4
                    event_type = "BULLISH_CATALYST"

            for kw in BEARISH_KEYWORDS:
                if kw in text:
                    score -= 0.5
                    event_type = "BEARISH_SHOCK"

            score = max(-1.0, min(1.0, score))

            # Match Sectors & Stocks
            for sector, keywords in SECTOR_MAP.items():
                if any(kw in text for kw in keywords):
                    if sector not in catalysts:
                        catalysts[sector] = {"score": 0.0, "events": [], "risk_flag": False}
                    catalysts[sector]["score"] = max(-1.0, min(1.0, catalysts[sector]["score"] + score))
                    catalysts[sector]["events"].append(item["headline"])
                    if score <= -0.5:
                        catalysts[sector]["risk_flag"] = True

        self.cached_catalysts = catalysts
        return catalysts

    def get_symbol_catalyst(self, symbol: str) -> Dict[str, Any]:
        """Returns catalyst score and risk flag for a specific stock symbol."""
        clean_symbol = symbol.replace(".NS", "").upper()
        
        # Determine symbol sector
        target_sector = None
        for sector, keywords in SECTOR_MAP.items():
            if any(clean_symbol.lower() in kw for kw in keywords):
                target_sector = sector
                break

        if not self.cached_catalysts:
            self.analyze_headlines()

        sector_info = self.cached_catalysts.get(target_sector, {"score": 0.0, "events": [], "risk_flag": False})
        
        return {
            "symbol": clean_symbol,
            "sector": target_sector or "GENERAL",
            "catalyst_score": round(sector_info["score"], 2),
            "event_risk_flag": sector_info["risk_flag"],
            "latest_headline": sector_info["events"][0] if sector_info["events"] else "No recent high-impact events"
        }

# Global Instance
news_event_engine = NewsEventEngine()
