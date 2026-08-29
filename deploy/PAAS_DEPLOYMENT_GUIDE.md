# Option B: 24/7 Cloud PaaS Deployment Guide (Render / Railway)

This guide walks you through deploying the **Autonomous AI Stock Market Analyzer** to the cloud in under 5 minutes so it runs **24/7 continuously even when your laptop is turned off**.

---

## 📱 Step 1: Set Up Free Telegram Alerts (Takes 2 Minutes)

To receive instant trade alerts on your smartphone:

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow prompts to name your bot (e.g. `MyStockAIBot`).
3. BotFather will give you a **Bot Token** (e.g. `123456789:ABCdefGHIjklMNO...`). Copy it.
4. Search for `@userinfobot` on Telegram, click Start, and copy your **Id** (this is your `TELEGRAM_CHAT_ID`, e.g. `987654321`).
5. Open your newly created bot in Telegram and click **Start** or send `/start` so it can message you.

---

## 🚀 Step 2: Deploy to Cloud (Choose Either Render or Railway)

### Method A: Deploy on Render (Recommended Free/Starter Cloud)
1. Push this project to your GitHub account (`git add .`, `git commit -m "deploy 24/7 ai"`, `git push`).
2. Go to [https://render.com](https://render.com) and log in with GitHub.
3. Click **New +** $\rightarrow$ **Web Service** $\rightarrow$ Select your GitHub repository.
4. Configure the service:
   - **Name**: `stock-market-ai`
   - **Runtime**: `Docker`
   - **Instance Type**: Free or Starter
5. Under **Disks (Persistent Storage)**:
   - Click **Add Disk**
   - **Name**: `stock-data`
   - **Mount Path**: `/app/data`
   - **Size**: `1 GB`
6. Under **Environment Variables**, add:
   - `AUTONOMOUS_TRADING_ENABLED` = `True`
   - `AUTONOMOUS_SCAN_INTERVAL` = `30`
   - `MAX_CONCURRENT_POSITIONS` = `3`
   - `TELEGRAM_BOT_TOKEN` = `<your bot token from Step 1>`
   - `TELEGRAM_CHAT_ID` = `<your chat id from Step 1>`
7. Click **Create Web Service**.
8. In 2-3 minutes, Render will build the Docker container and give you a public URL (e.g., `https://stock-market-ai.onrender.com`).

---

### Method B: Deploy on Railway
1. Go to [https://railway.app](https://railway.app) and log in with GitHub.
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo** $\rightarrow$ Select this repository.
3. In your project canvas, click your service $\rightarrow$ **Settings** $\rightarrow$ **Volumes** $\rightarrow$ **Add Volume**:
   - **Mount Path**: `/app/data`
4. Under **Variables**, add:
   - `AUTONOMOUS_TRADING_ENABLED` = `True`
   - `TELEGRAM_BOT_TOKEN` = `<your bot token>`
   - `TELEGRAM_CHAT_ID` = `<your chat id>`
5. Under **Networking**, click **Generate Domain** to get your public dashboard URL.

---

## 📊 Step 3: Access Your Dashboard & Analytics Anywhere

Once deployed, you can turn off your laptop. The AI will trade autonomously in the cloud:

- **Live Trading Cockpit**: `https://your-app-url.onrender.com/`
- **Win-Loss & Calibration Analytics**: `https://your-app-url.onrender.com/analytics`
- **Telegram Notifications**: Your phone will receive live push notifications whenever:
  - 🟢 An AI Trade is Opened (with win probability and risk levels).
  - 🎯 A Target is Hit (Win).
  - 🛑 A Stop Loss is Hit (Loss + AI Post-Mortem Diagnostic).
  - 📈 Daily Performance Summary.

---

## 🧠 How the AI Self-Learning Works During Cloud Run

1. **2,000 Token Starting Capital**: The AI starts with 2,000 Paper Tokens and manages risk with 2% max capital risk per trade.
2. **Persistent Memory**: Because `/app/data` is mounted to a persistent volume, all trade history, token balances, and AI learning memories survive server restarts.
3. **Loss Post-Mortem**: Every time a trade stops out, the AI diagnoses the failure pattern (false breakout, volume exhaustion, or regime shift) and automatically discounts similar setups in future trades.
