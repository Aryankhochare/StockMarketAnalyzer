// Background Service Worker managing WebSocket connection to AI Backend
let socket = null;
let isConnected = false;
const WS_URL = "ws://127.0.0.1:8000/ws/live-ticks";

function connectWebSocket() {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return;
    }

    try {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            console.log("[AI Bridge Background] WebSocket Connected to backend");
            isConnected = true;
        };

        socket.onclose = () => {
            console.log("[AI Bridge Background] WebSocket Disconnected. Reconnecting in 3s...");
            isConnected = false;
            setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = (err) => {
            console.error("[AI Bridge Background] WebSocket Error:", err);
            socket.close();
        };
    } catch (e) {
        console.error("[AI Bridge Background] Failed to connect WebSocket:", e);
        setTimeout(connectWebSocket, 5000);
    }
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "LIVE_TICK") {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(message.payload));
            sendResponse({ status: "SENT" });
        } else {
            sendResponse({ status: "DISCONNECTED" });
        }
    }
    return true;
});

// Initialize WebSocket connection
connectWebSocket();
