document.addEventListener("DOMContentLoaded", () => {
    let currentSymbol = "NIFTY 50";
    let currentTicker = "^NSEI";
    let chart, candlestickSeries;
    let ws;

    // Initialize TradingView Lightweight Chart
    function initChart() {
        const container = document.getElementById("chart-panel");
        container.innerHTML = "";
        
        chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 380,
            layout: {
                background: { color: '#0B0F17' },
                textColor: '#9CA3AF',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            }
        });

        candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10B981',
            downColor: '#EF4444',
            borderVisible: false,
            wickUpColor: '#10B981',
            wickDownColor: '#EF4444'
        });

        window.addEventListener('resize', () => {
            chart.applyOptions({ width: container.clientWidth });
        });
    }

    // Fetch and Load Candles
    async function loadCandles(symbol, ticker) {
        currentSymbol = symbol;
        currentTicker = ticker;
        document.getElementById("chart-title").innerText = `${symbol} (Intraday Real-time)`;

        try {
            const res = await fetch(`/api/candles?symbol=${symbol}&ticker=${ticker}`);
            const data = await res.json();
            if (data.candles && data.candles.length > 0) {
                const formatted = data.candles.map(c => ({
                    time: new Date(c.timestamp).getTime() / 1000,
                    open: c.open,
                    high: c.high,
                    low: c.low,
                    close: c.close
                })).sort((a, b) => a.time - b.time);
                
                candlestickSeries.setData(formatted);
                const latest = formatted[formatted.length - 1];
                document.getElementById("chart-price").innerText = `₹${latest.close.toFixed(2)}`;
            }

            fetchAISignal(symbol, ticker);
            fetchNewsCatalysts(symbol);
        } catch (e) {
            console.error("Error loading candles:", e);
        }
    }

    // Fetch News Catalysts
    async function fetchNewsCatalysts(symbol) {
        try {
            const res = await fetch(`/api/news-catalysts?symbol=${symbol}`);
            const data = await res.json();
            const info = data.symbol_catalyst || {};

            document.getElementById("news-sector").innerText = info.sector || "GENERAL";
            const score = info.catalyst_score || 0.0;
            const scoreEl = document.getElementById("news-score");
            scoreEl.innerText = `${score >= 0 ? '+' : ''}${score.toFixed(2)}`;
            scoreEl.style.color = score > 0 ? '#10B981' : (score < 0 ? '#EF4444' : '#9CA3AF');

            document.getElementById("news-headline").innerText = info.latest_headline || "No recent news events";
        } catch (e) {
            console.error("Error fetching news catalysts:", e);
        }
    }

    // Fetch AI Signal Decision
    async function fetchAISignal(symbol, ticker) {
        try {
            const res = await fetch(`/api/analyze?symbol=${symbol}&ticker=${ticker}`);
            const signal = await res.json();
            renderAICard(signal);
        } catch (e) {
            console.error("Error fetching AI signal:", e);
        }
    }

    // Render AI Decision Card
    function renderAICard(sig) {
        const container = document.getElementById("ai-card-container");
        const action = sig.action || "HOLD";
        const badgeClass = action;
        const mtf = sig.mtf_info || {};

        let html = `
            <div class="decision-card ${action}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; font-size:16px;">${sig.symbol || currentSymbol}</span>
                    <span class="badge ${badgeClass}">${action}</span>
                </div>
                <div style="font-size:12px; color:#9CA3AF;">${sig.reason || 'Scanning market metrics...'}</div>
                
                <div class="details-grid">
                    <div><span style="color:#9CA3AF;">Win Prob:</span> <b>${sig.win_prob_pct || 0}%</b></div>
                    <div><span style="color:#9CA3AF;">MTF Trend:</span> <b>${mtf.alignment || 'NEUTRAL'}</b></div>
                    <div><span style="color:#9CA3AF;">Entry:</span> <b>₹${(sig.entry_price || 0).toFixed(2)}</b></div>
                    <div><span style="color:#9CA3AF;">Quantity:</span> <b>${sig.quantity || 0} shares</b></div>
                    <div><span style="color:#9CA3AF;">Stop Loss:</span> <b style="color:#EF4444;">₹${(sig.stop_loss || 0).toFixed(2)}</b></div>
                    <div><span style="color:#9CA3AF;">Target:</span> <b style="color:#10B981;">₹${(sig.target || 0).toFixed(2)}</b></div>
                </div>
        `;

        if (action === "BUY" || action === "SELL") {
            html += `
                <button class="btn btn-primary" onclick="executePaperTrade('${sig.symbol}', '${action}', ${sig.quantity}, ${sig.entry_price}, ${sig.stop_loss}, ${sig.target})">
                    Execute Paper ${action}
                </button>
            `;
        }

        html += `</div>`;
        container.innerHTML = html;
    }

    // Global Paper Trade Execution
    window.executePaperTrade = async (symbol, action, qty, entry, stop, target) => {
        try {
            const res = await fetch('/api/paper-trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    action: action,
                    quantity: qty,
                    entry_price: entry,
                    stop_loss: stop,
                    target: target
                })
            });
            const result = await res.json();
            if (result.status === "SUCCESS") {
                fetchSummary();
            } else {
                alert(`Trade failed: ${result.reason}`);
            }
        } catch (e) {
            console.error("Error executing paper trade:", e);
        }
    };

    // Fetch Paper Trading Summary
    async function fetchSummary() {
        try {
            const res = await fetch('/api/paper-summary');
            const summary = await res.json();
            
            document.getElementById("nav-equity").innerText = `${summary.total_equity.toLocaleString('en-US', {minimumFractionDigits:2})} Tokens`;
            const pnlVal = summary.total_pnl;
            const daemonEl = document.getElementById("nav-daemon");
            if (daemonEl) daemonEl.innerText = "ACTIVE (24/7)";

            // Render Active Positions Table
            const posBody = document.getElementById("positions-table-body");
            if (summary.active_positions.length === 0) {
                posBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#9CA3AF;">No active open positions</td></tr>`;
            } else {
                posBody.innerHTML = summary.active_positions.map(p => `
                    <tr>
                        <td><b>${p.symbol}</b></td>
                        <td><span class="badge ${p.action}">${p.action}</span></td>
                        <td>${p.quantity}</td>
                        <td>₹${p.entry_price.toFixed(2)}</td>
                        <td>₹${p.current_price.toFixed(2)}</td>
                        <td style="color:#EF4444;">₹${p.stop_loss.toFixed(2)}</td>
                        <td style="color:#10B981;">₹${p.target.toFixed(2)}</td>
                        <td style="color:${p.unrealized_pnl >= 0 ? '#10B981' : '#EF4444'}; font-weight:600;">
                            ${p.unrealized_pnl >= 0 ? '+' : ''}₹${p.unrealized_pnl.toFixed(2)}
                        </td>
                    </tr>
                `).join('');
            }
        } catch (e) {
            console.error("Error fetching paper summary:", e);
        }
    }

    // Connect Dashboard WebSocket
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard`);

        ws.onopen = () => {
            document.getElementById("live-status").innerText = "● Live Stream Active";
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "TICK_UPDATE") {
                const tick = msg.tick;
                if (tick.symbol === currentSymbol) {
                    document.getElementById("chart-price").innerText = `₹${tick.price.toFixed(2)}`;
                    candlestickSeries.update({
                        time: new Date(tick.timestamp).getTime() / 1000,
                        close: tick.price
                    });
                }
                fetchSummary();
            }
        };

        ws.onclose = () => {
            document.getElementById("live-status").innerText = "○ Reconnecting...";
            setTimeout(connectWebSocket, 3000);
        };
    }

    // Load Watchlist Items
    async function loadWatchlist() {
        try {
            const res = await fetch('/api/watchlist');
            const items = await res.json();
            const container = document.getElementById("watchlist-container");
            
            container.innerHTML = items.map(item => `
                <div class="watchlist-item ${item.symbol === currentSymbol ? 'active' : ''}" 
                     onclick="selectWatchlistSymbol('${item.symbol}', '${item.ticker}')">
                    <div>
                        <div class="symbol-name">${item.symbol}</div>
                        <div class="symbol-type">${item.exchange} • ${item.type}</div>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error("Error loading watchlist:", e);
        }
    }

    window.selectWatchlistSymbol = (symbol, ticker) => {
        loadCandles(symbol, ticker);
        loadWatchlist();
    };

    // Run Walk-Forward Backtest Listener
    document.getElementById("btn-backtest").addEventListener("click", async () => {
        const btn = document.getElementById("btn-backtest");
        btn.innerText = "Running...";
        try {
            const res = await fetch(`/api/backtest?symbol=${currentSymbol}&ticker=${currentTicker}`);
            const data = await res.json();
            
            document.getElementById("bt-winrate").innerText = `${data.win_rate_pct}%`;
            document.getElementById("bt-sharpe").innerText = data.sharpe_ratio;
            document.getElementById("bt-drawdown").innerText = `${data.max_drawdown_pct}%`;
            document.getElementById("bt-profitfactor").innerText = data.profit_factor;
        } catch (e) {
            alert("Backtest failed");
        } finally {
            btn.innerText = "Run Backtest";
        }
    });

    // Retrain Model Button Listener
    document.getElementById("btn-train").addEventListener("click", async () => {
        const btn = document.getElementById("btn-train");
        btn.innerText = "Training...";
        try {
            const res = await fetch('/api/train', { method: 'POST' });
            const result = await res.json();
            alert(`Ensemble & Model Training Complete! Samples: ${result.ensemble.samples}`);
        } catch (e) {
            alert("Training failed");
        } finally {
            btn.innerText = "Retrain Models";
        }
    });

    // Initialize Page
    initChart();
    loadWatchlist();
    loadCandles(currentSymbol, currentTicker);
    fetchSummary();
    connectWebSocket();
});
