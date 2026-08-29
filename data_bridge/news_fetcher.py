import logging
import xml.etree.ElementTree as ET
import requests
from typing import List, Dict, Any

logger = logging.getLogger("NewsFetcher")

class NewsFetcher:
    """
    Live Financial News & RSS Feeds Collector.
    Pulls real-time financial headlines for NSE equities, sectors, and macroeconomic events.
    """
    FEEDS = [
        {"name": "GoogleNewsNSE", "url": "https://news.google.com/rss/search?q=NSE+stock+market+India&hl=en-IN&gl=IN&ceid=IN:en"},
        {"name": "GoogleNewsSectors", "url": "https://news.google.com/rss/search?q=Indian+sector+economy+banking+IT+pharma&hl=en-IN&gl=IN&ceid=IN:en"}
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def fetch_latest_headlines(self, limit: int = 15) -> List[Dict[str, Any]]:
        headlines = []
        for feed in self.FEEDS:
            try:
                res = requests.get(feed["url"], headers=self.HEADERS, timeout=5)
                if res.status_code == 200:
                    root = ET.fromstring(res.content)
                    for item in root.findall(".//item")[:limit]:
                        title = item.find("title")
                        pub_date = item.find("pubDate")
                        link = item.find("link")
                        
                        if title is not None and title.text:
                            headlines.append({
                                "source": feed["name"],
                                "headline": title.text.strip(),
                                "pub_date": pub_date.text.strip() if pub_date is not None else "",
                                "url": link.text.strip() if link is not None else ""
                            })
            except Exception as e:
                logger.debug(f"Could not fetch news feed {feed['name']}: {e}")
        return headlines

# Global Instance
news_fetcher = NewsFetcher()
