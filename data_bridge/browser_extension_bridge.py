import json
import logging
import asyncio
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("BrowserExtensionBridge")

class BrowserExtensionBridge:
    """
    WebSocket bridge manager.
    Receives real-time browser scraped ticks/quotes from Chrome extension,
    stores them in a live cache, and broadcasts them to UI dashboard subscribers.
    """
    def __init__(self):
        self.extension_connections: Set[WebSocket] = set()
        self.dashboard_connections: Set[WebSocket] = set()
        self.live_tick_cache: Dict[str, Dict[str, Any]] = {}

    async def connect_extension(self, websocket: WebSocket):
        await websocket.accept()
        self.extension_connections.add(websocket)
        logger.info("Chrome Extension Live Data Bridge connected.")

    def disconnect_extension(self, websocket: WebSocket):
        self.extension_connections.remove(websocket)
        logger.info("Chrome Extension Live Data Bridge disconnected.")

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        # Send initial snapshot of live tick cache
        if self.live_tick_cache:
            await websocket.send_text(json.dumps({
                "type": "CACHE_SNAPSHOT",
                "data": self.live_tick_cache
            }))
        logger.info("Web Dashboard subscriber connected.")

    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_connections.remove(websocket)
        logger.info("Web Dashboard subscriber disconnected.")

    async def process_incoming_tick(self, payload: Dict[str, Any]):
        """Processes tick sent from browser extension or scraper engine."""
        symbol = payload.get("symbol")
        if not symbol:
            return

        self.live_tick_cache[symbol] = {
            "symbol": symbol,
            "price": float(payload.get("price", 0.0)),
            "change": float(payload.get("change", 0.0)),
            "pChange": float(payload.get("pChange", 0.0)),
            "open": float(payload.get("open", 0.0)),
            "high": float(payload.get("high", 0.0)),
            "low": float(payload.get("low", 0.0)),
            "volume": int(payload.get("volume", 0)),
            "timestamp": payload.get("timestamp"),
            "source": payload.get("source", "BROWSER_BRIDGE")
        }

        # Broadcast tick update to UI dashboards
        message = json.dumps({
            "type": "TICK_UPDATE",
            "symbol": symbol,
            "tick": self.live_tick_cache[symbol]
        })
        
        await self.broadcast_to_dashboards(message)

    async def broadcast_to_dashboards(self, message: str):
        disconnected = set()
        for connection in self.dashboard_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending tick to dashboard client: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.dashboard_connections.remove(conn)

    def get_tick(self, symbol: str) -> Dict[str, Any]:
        return self.live_tick_cache.get(symbol, {})

# Global Singleton Instance
bridge_manager = BrowserExtensionBridge()
