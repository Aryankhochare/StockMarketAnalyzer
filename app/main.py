import asyncio
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from config import DEFAULT_WATCHLIST, BASE_DIR
from data_bridge.browser_extension_bridge import bridge_manager
from data_bridge.data_manager import data_manager
from data_bridge.telegram_service import telegram_service
from data_bridge.market_calendar import market_calendar
from ai_engine.model_trainer import ModelTrainer
from ai_engine.ensemble_model import ensemble_model
from quant_engine.news_event_engine import news_event_engine
from backtesting.walk_forward import walk_forward_backtester
from decision_and_risk.decision_engine import decision_engine
from decision_and_risk.paper_trader import paper_trader
from decision_and_risk.performance_tracker import performance_tracker
from decision_and_risk.autonomous_trader import autonomous_trader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StockAnalyzerApp")

app = FastAPI(title="Autonomous AI Stock Market Decision Platform")

# Mount Static and Templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

# Background polling loop for live data
async def background_nse_poller():
    """Periodically fetches quotes for watchlist symbols with network backoff."""
    while True:
        try:
            if data_manager.nse_fetcher.is_offline:
                await asyncio.sleep(15)
                continue

            for item in DEFAULT_WATCHLIST:
                symbol = item["symbol"]
                symbol_type = item.get("type", "EQUITY")
                
                quote = None
                if symbol_type == "INDEX":
                    opt = data_manager.nse_fetcher.fetch_option_chain(symbol)
                    if opt and opt.get("underlyingValue", 0) > 0:
                        quote = {
                            "lastPrice": opt["underlyingValue"],
                            "change": 0.0,
                            "pChange": 0.0,
                            "open": opt["underlyingValue"],
                            "high": opt["underlyingValue"],
                            "low": opt["underlyingValue"],
                            "totalTradedVolume": 0,
                            "timestamp": opt.get("timestamp", "")
                        }
                else:
                    quote = data_manager.nse_fetcher.fetch_equity_quote(symbol)

                if quote and quote.get("lastPrice", 0) > 0:
                    payload = {
                        "symbol": symbol,
                        "price": quote["lastPrice"],
                        "change": quote.get("change", 0),
                        "pChange": quote.get("pChange", 0),
                        "open": quote.get("open", 0),
                        "high": quote.get("high", 0),
                        "low": quote.get("low", 0),
                        "volume": quote.get("totalTradedVolume", 0),
                        "timestamp": quote.get("timestamp", ""),
                        "source": "NSE_LIVE_FETCHER"
                    }
                    await bridge_manager.process_incoming_tick(payload)
                    
                    # Update paper trader open positions with live price
                    paper_trader.update_live_price(symbol, float(quote["lastPrice"]))
                    
                await asyncio.sleep(2.0) # Pause between symbol requests
        except Exception as e:
            logger.debug(f"Background NSE poller status: {e}")
        await asyncio.sleep(10) # Wait before next cycle

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Autonomous AI Stock Analyzer Platform with 24/7 Cloud Paper Trading...")
    asyncio.create_task(background_nse_poller())
    autonomous_trader.start()

# Health check route for cloud PaaS (Render / Railway)
@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy", "autonomous_active": autonomous_trader.is_active})

# HTML Dashboard & Analytics Routes
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics_page(request: Request):
    return templates.TemplateResponse(request=request, name="analytics.html")

# API Routes
@app.get("/api/watchlist")
async def get_watchlist():
    return JSONResponse(content=DEFAULT_WATCHLIST)

@app.get("/api/candles")
async def get_candles(symbol: str = "NIFTY 50", ticker: str = "^NSEI"):
    df = data_manager.get_latest_data(symbol, ticker)
    if df.empty:
        return JSONResponse(content={"candles": []})
    
    records = df[["timestamp", "open", "high", "low", "close", "volume"]].to_dict(orient="records")
    # Convert timestamp objects to string
    for r in records:
        r["timestamp"] = str(r["timestamp"])
    return JSONResponse(content={"candles": records})

@app.get("/api/analyze")
async def analyze_symbol(symbol: str = "NIFTY 50", ticker: str = "^NSEI"):
    df = data_manager.get_latest_data(symbol, ticker)
    option_snapshot = data_manager.get_option_chain_snapshot(symbol)
    signal = decision_engine.evaluate_trade(symbol, df, option_snapshot)
    return JSONResponse(content=signal)

@app.post("/api/train")
async def train_ai_model():
    trainer = ModelTrainer()
    df_hist = data_manager.get_historical_candles("^NSEI", period="1y", interval="1d")
    r1 = trainer.train_model(df_hist)
    r2 = ensemble_model.train_and_calibrate(df_hist)
    return JSONResponse(content={"baseline": r1, "ensemble": r2})

@app.get("/api/backtest")
async def run_backtest(symbol: str = "NIFTY 50", ticker: str = "^NSEI"):
    df_hist = data_manager.get_historical_candles(ticker, period="1y", interval="1d")
    res = walk_forward_backtester.run_backtest(symbol, df_hist)
    return JSONResponse(content=res)

@app.get("/api/news-catalysts")
async def get_news_catalysts(symbol: str = "NIFTY 50"):
    catalysts = news_event_engine.analyze_headlines()
    symbol_catalyst = news_event_engine.get_symbol_catalyst(symbol)
    return JSONResponse(content={"all_catalysts": catalysts, "symbol_catalyst": symbol_catalyst})

@app.get("/api/india-vix")
async def get_india_vix():
    vix = data_manager.get_india_vix_snapshot()
    return JSONResponse(content=vix)

@app.get("/api/market-status")
async def get_market_session_status():
    status = market_calendar.get_session_status()
    return JSONResponse(content=status)

@app.post("/api/paper-trade")
async def execute_paper_trade(payload: Dict[str, Any]):
    result = paper_trader.open_position(payload)
    return JSONResponse(content=result)

@app.get("/api/paper-summary")
async def get_paper_summary():
    return JSONResponse(content=paper_trader.get_summary())

@app.get("/api/analytics")
async def get_analytics_metrics():
    return JSONResponse(content=performance_tracker.get_performance_metrics())

@app.get("/api/autonomous/status")
async def get_autonomous_status():
    return JSONResponse(content=autonomous_trader.get_status())

@app.post("/api/autonomous/toggle")
async def toggle_autonomous_trading():
    is_active = autonomous_trader.toggle()
    return JSONResponse(content={"is_active": is_active, "status": "ACTIVE" if is_active else "PAUSED"})

@app.post("/api/account/reset")
async def reset_account(tokens: float = 2000.0):
    paper_trader.reset_account(tokens)
    return JSONResponse(content={"status": "RESET_SUCCESS", "new_balance": tokens})

# WebSocket Endpoints
@app.websocket("/ws/live-ticks")
async def websocket_live_ticks(websocket: WebSocket):
    await bridge_manager.connect_extension(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await bridge_manager.process_incoming_tick(data)
    except WebSocketDisconnect:
        bridge_manager.disconnect_extension(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in live-ticks endpoint: {e}")
        bridge_manager.disconnect_extension(websocket)

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await bridge_manager.connect_dashboard(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        bridge_manager.disconnect_dashboard(websocket)
    except Exception as e:
        bridge_manager.disconnect_dashboard(websocket)
