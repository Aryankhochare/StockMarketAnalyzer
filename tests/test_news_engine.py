import pytest
from quant_engine.news_event_engine import NewsEventEngine

def test_news_event_parsing():
    engine = NewsEventEngine()
    sample_headlines = [
        {"source": "Test", "headline": "TCS reports strong Q3 profit up 15% with massive IT order win"},
        {"source": "Test", "headline": "SEBI penalty and investigation on generic bank firm"}
    ]

    catalysts = engine.analyze_headlines(sample_headlines)
    
    assert "IT" in catalysts
    assert catalysts["IT"]["score"] > 0.0

    symbol_info = engine.get_symbol_catalyst("TCS.NS")
    assert symbol_info["sector"] == "IT"
