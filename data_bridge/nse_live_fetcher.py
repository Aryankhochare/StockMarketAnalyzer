import time
import logging
from typing import Dict, Any, Optional

try:
    from curl_cffi import requests as req_lib
    HAS_CURL_CFFI = True
except ImportError:
    import requests as req_lib
    HAS_CURL_CFFI = False

logger = logging.getLogger("NSELiveFetcher")

class NSELiveFetcher:
    """
    Direct Live NSE Data Fetcher.
    Uses browser TLS impersonation (curl_cffi) to bypass Cloudflare 403 blocks
    and fetch real-time quotes, derivatives, and option chains.
    """
    BASE_URL = "https://www.nseindia.com"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
    }

    def __init__(self):
        if HAS_CURL_CFFI:
            self.session = req_lib.Session(impersonate="chrome")
        else:
            self.session = req_lib.Session()
        self.session.headers.update(self.HEADERS)
        self.last_cookie_time = 0
        self.cookie_ttl = 300  # Refresh session cookies every 5 minutes
        self.is_offline = False
        self.offline_until = 0

    def _init_cookies(self) -> bool:
        """Initializes cookies by visiting the main home page."""
        now = time.time()
        if now < self.offline_until:
            return False

        if now - self.last_cookie_time > self.cookie_ttl:
            try:
                response = self.session.get(self.BASE_URL, timeout=8)
                if response.status_code == 200:
                    self.last_cookie_time = now
                    if self.is_offline:
                        self.is_offline = False
                        logger.info("NSE Live Connection restored.")
                    return True
                else:
                    # Silence warning and set 30s backoff for 403/429 status codes
                    self.offline_until = now + 30
                    return False
            except Exception as e:
                self.is_offline = True
                self.offline_until = now + 30
                return False
        return not self.is_offline

    def fetch_equity_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch live price quote for an equity symbol (e.g. RELIANCE, TCS, INFY)."""
        if not self._init_cookies():
            return None

        clean_symbol = symbol.replace(".NS", "").upper()
        url = f"{self.BASE_URL}/api/quote-equity?symbol={clean_symbol}"
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                price_info = data.get("priceInfo", {})
                trade_info = data.get("metadata", {})
                
                return {
                    "symbol": clean_symbol,
                    "lastPrice": price_info.get("lastPrice", 0.0),
                    "change": price_info.get("change", 0.0),
                    "pChange": price_info.get("pChange", 0.0),
                    "open": price_info.get("open", 0.0),
                    "high": price_info.get("intraDayHighLow", {}).get("max", 0.0),
                    "low": price_info.get("intraDayHighLow", {}).get("min", 0.0),
                    "previousClose": price_info.get("previousClose", 0.0),
                    "vwap": price_info.get("vwap", price_info.get("lastPrice", 0.0)),
                    "totalTradedVolume": data.get("preOpenMarket", {}).get("totalTradedVolume", 0),
                    "timestamp": trade_info.get("lastUpdateTime", "")
                }
        except Exception:
            self.offline_until = time.time() + 20
        return None

    def fetch_option_chain(self, symbol: str = "NIFTY") -> Optional[Dict[str, Any]]:
        """Fetch real-time option chain data for NIFTY, BANKNIFTY or equities."""
        if not self._init_cookies():
            return None

        clean_symbol = symbol.replace("^NSEI", "NIFTY").replace("^NSEBANK", "BANKNIFTY").replace(".NS", "").upper()
        is_index = clean_symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY", "NIFTY 50", "BANK NIFTY"]
        
        if clean_symbol == "NIFTY 50":
            clean_symbol = "NIFTY"
        elif clean_symbol == "BANK NIFTY":
            clean_symbol = "BANKNIFTY"

        endpoint = "option-chain-indices" if is_index else "option-chain-equities"
        url = f"{self.BASE_URL}/api/{endpoint}?symbol={clean_symbol}"
        
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                records = data.get("records", {})
                filtered = data.get("filtered", {})
                
                underlying_value = records.get("underlyingValue", 0.0)
                tot_call_oi = filtered.get("CE", {}).get("totOI", 0)
                tot_put_oi = filtered.get("PE", {}).get("totOI", 0)
                tot_call_vol = filtered.get("CE", {}).get("totVol", 0)
                tot_put_vol = filtered.get("PE", {}).get("totVol", 0)
                
                pcr = (tot_put_oi / tot_call_oi) if tot_call_oi > 0 else 1.0
                
                return {
                    "symbol": clean_symbol,
                    "underlyingValue": underlying_value,
                    "totalCallOI": tot_call_oi,
                    "totalPutOI": tot_put_oi,
                    "pcr": round(pcr, 4),
                    "totalCallVolume": tot_call_vol,
                    "totalPutVolume": tot_put_vol,
                    "timestamp": records.get("timestamp", "")
                }
        except Exception:
            self.offline_until = time.time() + 20
        return None
