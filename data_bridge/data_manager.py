import logging
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Optional, Dict, Any
from data_bridge.nse_live_fetcher import NSELiveFetcher
from data_bridge.browser_extension_bridge import bridge_manager

logger = logging.getLogger("DataManager")

class DataManager:
    """
    Unified Data Manager.
    Fetches historical OHLCV candles, updates the latest candle with real-time
    live ticks from NSELiveFetcher or Browser Extension Bridge, and delivers
    clean point-in-time DataFrames for feature calculation and AI modeling.
    """
    def __init__(self):
        self.nse_fetcher = NSELiveFetcher()

    def get_historical_candles(self, ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """
        Fetch historical candles via yfinance.
        ticker example: '^NSEI' for NIFTY, 'RELIANCE.NS' for RELIANCE.
        """
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty:
                logger.warning(f"No historical data returned for ticker {ticker}")
                return pd.DataFrame()
            
            # Reset index to make Date/Datetime a column
            df = df.reset_index()
            
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
                
            # Rename standard columns
            df = df.rename(columns={
                "Date": "timestamp",
                "Datetime": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            # Ensure float data types
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            return df
        except Exception as e:
            logger.error(f"Error fetching historical candles for {ticker}: {e}")
            return pd.DataFrame()

    def get_latest_data(self, symbol: str, ticker: str, interval: str = "1d") -> pd.DataFrame:
        """
        Get historical candles merged with real-time live tick data.
        """
        df = self.get_historical_candles(ticker, period="3mo", interval=interval)
        if df.empty:
            return pd.DataFrame()

        # Check for real-time tick from Browser Bridge
        live_tick = bridge_manager.get_tick(symbol)
        
        # If no browser tick, check direct NSE fetcher
        if not live_tick or live_tick.get("price", 0) == 0:
            quote = self.nse_fetcher.fetch_equity_quote(symbol)
            if quote and quote.get("lastPrice", 0) > 0:
                live_tick = {
                    "symbol": symbol,
                    "price": quote["lastPrice"],
                    "open": quote["open"],
                    "high": quote["high"],
                    "low": quote["low"],
                    "volume": quote["totalTradedVolume"],
                    "timestamp": quote["timestamp"]
                }

        # Inject real-time tick as the latest row if present
        if live_tick and live_tick.get("price", 0) > 0:
            latest_price = float(live_tick["price"])
            
            # Create a synthetic latest row or update last candle
            last_idx = df.index[-1]
            df.loc[last_idx, "close"] = latest_price
            if live_tick.get("high") and live_tick["high"] > df.loc[last_idx, "high"]:
                df.loc[last_idx, "high"] = float(live_tick["high"])
            if live_tick.get("low") and live_tick["low"] < df.loc[last_idx, "low"]:
                df.loc[last_idx, "low"] = float(live_tick["low"])
            if live_tick.get("volume"):
                df.loc[last_idx, "volume"] = float(live_tick["volume"])

        return df

    def get_option_chain_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch live option chain PCR and open interest snapshot."""
        return self.nse_fetcher.fetch_option_chain(symbol)

# Global Instance
data_manager = DataManager()
