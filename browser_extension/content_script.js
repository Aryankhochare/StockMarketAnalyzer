// Content Script to scrape live quotes/ticks from financial web pages
(function() {
    console.log("[AI Stock Analyzer Bridge] Content script active on:", window.location.hostname);

    function extractNSEData() {
        if (!window.location.hostname.includes("nseindia.com")) return null;
        
        try {
            const priceEl = document.querySelector("#quoteLtp, .price-info .last-price");
            const symbolEl = document.querySelector("#equitySymbol, .symbol-name");
            
            if (priceEl && symbolEl) {
                const price = parseFloat(priceEl.innerText.replace(/,/g, ''));
                const symbol = symbolEl.innerText.trim();
                return { symbol, price, source: "NSE_WEB" };
            }
        } catch (e) {
            console.error("Error scraping NSE web:", e);
        }
        return null;
    }

    function extractTradingViewData() {
        if (!window.location.hostname.includes("tradingview.com")) return null;
        
        try {
            const priceEl = document.querySelector("[class*='last-'], [class*='js-symbol-last']");
            const symbolEl = document.querySelector("[class*='title-'], [class*='js-symbol-header']");
            
            if (priceEl) {
                const price = parseFloat(priceEl.innerText.replace(/,/g, ''));
                const symbol = symbolEl ? symbolEl.innerText.split(' ')[0].trim() : "ACTIVE_SYMBOL";
                return { symbol, price, source: "TRADINGVIEW_WEB" };
            }
        } catch (e) {
            console.error("Error scraping TradingView web:", e);
        }
        return null;
    }

    function scanAndSend() {
        let tick = extractNSEData() || extractTradingViewData();
        if (tick && tick.price && !isNaN(tick.price)) {
            tick.timestamp = new Date().toISOString();
            chrome.runtime.sendMessage({ type: "LIVE_TICK", payload: tick });
        }
    }

    // Interval to scan active webpage DOM every 1.5 seconds
    setInterval(scanAndSend, 1500);
})();
