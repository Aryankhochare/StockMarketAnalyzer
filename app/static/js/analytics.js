document.addEventListener("DOMContentLoaded", () => {
    let equityChart = null;
    let rawTrades = [];

    // Initialize Equity Chart
    function initEquityChart(labels, data) {
        const ctx = document.getElementById("equityChart").getContext("2d");
        if (equityChart) {
            equityChart.destroy();
        }

        equityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Token Balance',
                    data: data,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    fill: true,
                    tension: 0.2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9CA3AF' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9CA3AF' }
                    }
                }
            }
        });
    }

    // Fetch and render analytics data
    async function loadAnalytics() {
        try {
            const res = await fetch('/api/analytics');
            const data = await res.json();

            // Populate Top Metrics
            document.getElementById("card-total-trades").innerText = data.total_trades;
            document.getElementById("card-win-loss-split").innerText = `${data.winning_trades} Wins • ${data.losing_trades} Losses`;

            const winRateEl = document.getElementById("card-win-rate");
            winRateEl.innerText = `${data.win_rate_pct.toFixed(1)}%`;
            winRateEl.className = `metric-value ${data.win_rate_pct >= 50 ? 'green' : 'red'}`;

            document.getElementById("card-predicted-prob").innerText = `AI Expected: ${data.avg_predicted_win_prob.toFixed(1)}% (Gap: ${data.calibration_gap_pct >= 0 ? '+' : ''}${data.calibration_gap_pct.toFixed(1)}%)`;

            const pnlEl = document.getElementById("card-total-pnl");
            pnlEl.innerText = `${data.total_pnl >= 0 ? '+' : ''}${data.total_pnl.toFixed(2)} Tokens`;
            pnlEl.className = `metric-value ${data.total_pnl >= 0 ? 'green' : 'red'}`;

            document.getElementById("card-pnl-pct").innerText = `${data.total_pnl_pct >= 0 ? '+' : ''}${data.total_pnl_pct.toFixed(2)}% Return on Capital`;
            document.getElementById("card-profit-factor").innerText = data.profit_factor.toFixed(2);
            document.getElementById("card-payoff-ratio").innerText = `Avg Win: +${data.avg_win.toFixed(2)} | Avg Loss: -${data.avg_loss.toFixed(2)}`;

            document.getElementById("nav-tokens").innerText = `${data.current_balance.toLocaleString('en-US', {minimumFractionDigits: 2})} Tokens`;

            // Render Equity Chart
            if (data.equity_curve && data.equity_curve.length > 0) {
                const labels = data.equity_curve.map(e => e.time);
                const values = data.equity_curve.map(e => e.equity);
                initEquityChart(labels, values);
            }

            // Render Calibration Table
            const calBody = document.getElementById("calibration-body");
            if (data.calibration_buckets && data.calibration_buckets.length > 0) {
                calBody.innerHTML = data.calibration_buckets.map(b => `
                    <tr>
                        <td><b>${b.bucket}</b></td>
                        <td>${b.count}</td>
                        <td style="color: #3B82F6;">${b.avg_predicted.toFixed(1)}%</td>
                        <td style="color: ${b.actual_win_rate >= b.avg_predicted ? '#10B981' : '#EF4444'}; font-weight:600;">
                            ${b.actual_win_rate.toFixed(1)}%
                        </td>
                    </tr>
                `).join('');
            } else {
                calBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #9CA3AF;">No closed trades yet</td></tr>`;
            }

            // Render AI Loss Diagnostics & Post-Mortem Log
            const lossContainer = document.getElementById("loss-diagnostics-container");
            if (data.loss_diagnostics && data.loss_diagnostics.length > 0) {
                lossContainer.innerHTML = data.loss_diagnostics.map(diag => `
                    <div class="loss-item">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <b>${diag.symbol} (${diag.action}) • Pattern: <span style="color:#F59E0B;">${diag.failure_type}</span></b>
                            <span style="color:#9CA3AF;">${diag.timestamp}</span>
                        </div>
                        <div style="color: #D1D5DB;">${diag.diagnosis}</div>
                        <div style="color: #3B82F6; margin-top: 4px; font-weight: 500;">
                            Adaptive Correction: Applied -${(diag.penalty_weight * 100).toFixed(0)}% dynamic penalty to prevent repeat failure on ${diag.symbol}.
                        </div>
                    </div>
                `).join('');
            } else {
                lossContainer.innerHTML = `
                    <div style="font-size: 13px; color: #9CA3AF; text-align: center; padding: 20px;">
                        No stopped-out trades recorded yet. The AI is running with 0 unhandled loss patterns.
                    </div>
                `;
            }

            // Store raw trades for filtering
            rawTrades = data.recent_trades || [];
            renderTradesTable(rawTrades);

        } catch (e) {
            console.error("Error loading analytics:", e);
        }
    }

    // Render Searchable Trades Table
    function renderTradesTable(trades) {
        const outcome = document.getElementById("filter-outcome").value;
        const tbody = document.getElementById("trades-table-body");

        let filtered = trades;
        if (outcome === "WIN") {
            filtered = trades.filter(t => t.realized_pnl > 0);
        } else if (outcome === "LOSS") {
            filtered = trades.filter(t => t.realized_pnl <= 0);
        }

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: #9CA3AF;">No matching trades found</td></tr>`;
            return;
        }

        tbody.innerHTML = filtered.slice().reverse().map(t => {
            const isWin = t.realized_pnl > 0;
            const prob = t.predicted_win_prob ? (t.predicted_win_prob * 100).toFixed(1) + '%' : '--';
            return `
                <tr>
                    <td style="font-family:monospace; font-size:11px; color:#6B7280;">${t.id ? t.id.slice(-8) : '--'}</td>
                    <td><b>${t.symbol}</b></td>
                    <td><span class="badge ${t.action}">${t.action}</span></td>
                    <td>${t.quantity}</td>
                    <td>${t.entry_price.toFixed(2)}</td>
                    <td>${t.exit_price.toFixed(2)}</td>
                    <td style="font-size:11px; color:#9CA3AF;">TP: ${t.target.toFixed(2)} | SL: ${t.stop_loss.toFixed(2)}</td>
                    <td style="color:#3B82F6; font-weight:600;">${prob}</td>
                    <td>
                        <span class="${isWin ? 'badge-win' : 'badge-loss'}">
                            ${isWin ? '+' : ''}${t.realized_pnl.toFixed(2)} (${t.realized_pnl_pct.toFixed(2)}%)
                        </span>
                    </td>
                    <td><span style="font-size:11px; color:#9CA3AF;">${t.close_reason}</span></td>
                    <td style="font-size:11px; color:#9CA3AF;">${t.close_time}</td>
                </tr>
            `;
        }).join('');
    }

    // Filter Outcome change event
    document.getElementById("filter-outcome").addEventListener("change", () => {
        renderTradesTable(rawTrades);
    });

    // Check autonomous status
    async function checkAutonomousStatus() {
        try {
            const res = await fetch('/api/autonomous/status');
            const data = await res.json();
            const badge = document.getElementById("auto-status");
            const btn = document.getElementById("btn-toggle-auto");
            
            if (data.is_active) {
                badge.innerText = "ACTIVE (24/7)";
                badge.className = "stat-value green";
                btn.innerText = "Pause Daemon";
            } else {
                badge.innerText = "PAUSED";
                badge.className = "stat-value red";
                btn.innerText = "Resume Daemon";
            }
        } catch (e) {
            console.error("Error checking autonomous status:", e);
        }
    }

    // Toggle Autonomous Trading Daemon
    document.getElementById("btn-toggle-auto").addEventListener("click", async () => {
        try {
            const res = await fetch('/api/autonomous/toggle', { method: 'POST' });
            const data = await res.json();
            await checkAutonomousStatus();
        } catch (e) {
            console.error("Error toggling autonomous daemon:", e);
        }
    });

    // Reset Tokens Button
    document.getElementById("btn-reset-tokens").addEventListener("click", async () => {
        if (confirm("Reset paper trading balance to 2,000 Tokens and wipe history for clean validation?")) {
            try {
                await fetch('/api/account/reset?tokens=2000', { method: 'POST' });
                await loadAnalytics();
            } catch (e) {
                console.error("Error resetting account:", e);
            }
        }
    });

    // Initial Load & Polling every 10 seconds
    loadAnalytics();
    checkAutonomousStatus();
    setInterval(() => {
        loadAnalytics();
        checkAutonomousStatus();
    }, 10000);
});
