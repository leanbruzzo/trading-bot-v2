"""
DASHBOARD: Servidor web para visualizar P&L e historial de trades.
"""
import json
import os
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

TRADE_HISTORY_FILE = "logs/trade_history.json"
RISK_STATE_FILE    = "logs/risk_state.json"
OPEN_TRADES_FILE   = "logs/open_trades.json"

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {} if path.endswith("state.json") else []

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trading Bot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, sans-serif; background: #0f0f1a; color: #e0e0e0; }
  .header { background: #1a1a2e; padding: 20px 30px; border-bottom: 1px solid #2a2a4a; display: flex; align-items: center; gap: 15px; }
  .header h1 { font-size: 22px; color: #fff; }
  .header .dot { width: 10px; height: 10px; background: #00ff88; border-radius: 50%; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .container { padding: 25px 30px; max-width: 1200px; margin: 0 auto; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }
  .card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }
  .card .label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card .value { font-size: 26px; font-weight: 700; }
  .green { color: #00ff88; }
  .red { color: #ff4466; }
  .white { color: #fff; }
  .chart-card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; margin-bottom: 25px; }
  .chart-card h2 { font-size: 16px; color: #fff; margin-bottom: 15px; }
  .table-card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }
  .table-card h2 { font-size: 16px; color: #fff; margin-bottom: 15px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 10px; color: #888; font-weight: 500; border-bottom: 1px solid #2a2a4a; }
  td { padding: 10px; border-bottom: 1px solid #1a1a2e; }
  tr:hover { background: #22223a; }
  .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-long { background: #00ff8822; color: #00ff88; }
  .badge-short { background: #ff446622; color: #ff4466; }
  .details { font-size: 11px; color: #666; margin-top: 3px; }
  .open-section { margin-bottom: 25px; }
  .open-section h2 { font-size: 16px; color: #fff; margin-bottom: 15px; }
  .refresh { font-size: 12px; color: #555; margin-top: 20px; text-align: center; }
</style>
</head>
<body>
<div class="header">
  <div class="dot"></div>
  <h1>🤖 Trading Bot Dashboard</h1>
</div>
<div class="container">
  <div class="metrics" id="metrics">Cargando...</div>

  <div class="open-section">
    <h2>📂 Posiciones Abiertas</h2>
    <div class="table-card">
      <table>
        <thead><tr><th>Par</th><th>Dirección</th><th>Entrada</th><th>Stop</th><th>TP</th><th>Partial TP</th><th>Desde</th></tr></thead>
        <tbody id="open-tbody"></tbody>
      </table>
    </div>
  </div>

  <div class="chart-card">
    <h2>📈 P&L Acumulado</h2>
    <canvas id="pnlChart" height="80"></canvas>
  </div>

  <div class="table-card">
    <h2>📋 Historial de Trades</h2>
    <table>
      <thead>
        <tr>
          <th>Fecha</th><th>Par</th><th>Dir.</th><th>Entrada</th>
          <th>Salida</th><th>P&L</th><th>Duración</th><th>Motivo</th><th>Análisis</th>
        </tr>
      </thead>
      <tbody id="history-tbody"></tbody>
    </table>
  </div>
  <div class="refresh">Actualización automática cada 60 segundos</div>
</div>

<script>
let pnlChart = null;

async function loadData() {
  const res  = await fetch("/api/data");
  const data = await res.json();

  // ── Métricas ──────────────────────────────────────────────────────────────
  const { state, history, open_trades } = data;
  const wins     = history.filter(t => t.pnl > 0).length;
  const winrate  = history.length > 0 ? ((wins / history.length) * 100).toFixed(1) : 0;
  const totalPnl = history.reduce((a, t) => a + t.pnl, 0);
  const avgPnl   = history.length > 0 ? (totalPnl / history.length).toFixed(2) : 0;

  document.getElementById("metrics").innerHTML = `
    <div class="card">
      <div class="label">P&L Total</div>
      <div class="value ${totalPnl >= 0 ? 'green' : 'red'}">${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}</div>
    </div>
    <div class="card">
      <div class="label">P&L Hoy</div>
      <div class="value ${state.daily_pnl >= 0 ? 'green' : 'red'}">${state.daily_pnl >= 0 ? '+' : ''}$${(state.daily_pnl || 0).toFixed(2)}</div>
    </div>
    <div class="card">
      <div class="label">Win Rate</div>
      <div class="value white">${winrate}%</div>
    </div>
    <div class="card">
      <div class="label">Total Trades</div>
      <div class="value white">${history.length}</div>
    </div>
    <div class="card">
      <div class="label">P&L Promedio</div>
      <div class="value ${avgPnl >= 0 ? 'green' : 'red'}">${avgPnl >= 0 ? '+' : ''}$${avgPnl}</div>
    </div>
    <div class="card">
      <div class="label">Posiciones Abiertas</div>
      <div class="value white">${Object.keys(open_trades).length}</div>
    </div>
  `;

  // ── Posiciones abiertas ───────────────────────────────────────────────────
  const openTbody = document.getElementById("open-tbody");
  const openKeys  = Object.keys(open_trades);
  if (openKeys.length === 0) {
    openTbody.innerHTML = `<tr><td colspan="7" style="color:#555;text-align:center;padding:20px">Sin posiciones abiertas</td></tr>`;
  } else {
    openTbody.innerHTML = openKeys.map(symbol => {
      const t = open_trades[symbol];
      const partial = t.partial_done ? "✅ Tomado" : "⏳ Pendiente";
      const since   = t.opened_at ? t.opened_at.replace("T", " ").slice(0, 16) : "-";
      return `<tr>
        <td><b>${symbol}</b></td>
        <td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
        <td>$${t.entry.toLocaleString()}</td>
        <td>$${t.stop.toLocaleString()}</td>
        <td>$${t.tp.toLocaleString()}</td>
        <td>${partial}</td>
        <td>${since}</td>
      </tr>`;
    }).join("");
  }

  // ── Gráfico P&L acumulado ─────────────────────────────────────────────────
  const sorted  = [...history].sort((a, b) => new Date(a.closed_at) - new Date(b.closed_at));
  const labels  = sorted.map(t => t.closed_at.replace("T", " ").slice(0, 16));
  let cumPnl    = 0;
  const values  = sorted.map(t => { cumPnl += t.pnl; return +cumPnl.toFixed(2); });
  const colors  = values.map(v => v >= 0 ? "#00ff88" : "#ff4466");

  if (pnlChart) pnlChart.destroy();
  const ctx = document.getElementById("pnlChart").getContext("2d");
  pnlChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "P&L Acumulado (USDT)",
        data: values,
        borderColor: "#00ff88",
        backgroundColor: "rgba(0,255,136,0.08)",
        pointBackgroundColor: colors,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      plugins: { legend: { labels: { color: "#888" } } },
      scales: {
        x: { ticks: { color: "#555", maxTicksLimit: 8 }, grid: { color: "#1a1a2e" } },
        y: { ticks: { color: "#888" }, grid: { color: "#2a2a4a" } }
      }
    }
  });

  // ── Historial de trades ───────────────────────────────────────────────────
  const tbody = document.getElementById("history-tbody");
  if (history.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="color:#555;text-align:center;padding:20px">Sin trades registrados aún</td></tr>`;
  } else {
    const reversed = [...history].reverse();
    tbody.innerHTML = reversed.map(t => {
      const pnlColor = t.pnl >= 0 ? "green" : "red";
      const ao       = t.analysis_open  || {};
      const ac       = t.analysis_close || {};
      const analysis = `
        <div class="details">
          🔵 <b>Apertura:</b> régimen=${ao.regime||'-'} RSI=${ao.rsi||'-'} score=${ao.combined_score||'-'} vol=${ao.volume_confirm ? '✅' : '❌'}
        </div>
        <div class="details">
          🔴 <b>Cierre:</b> régimen=${ac.regime||'-'} RSI=${ac.rsi||'-'} score=${ac.combined_score||'-'}
        </div>`;
      return `<tr>
        <td>${t.closed_at ? t.closed_at.replace("T"," ").slice(0,16) : '-'}</td>
        <td><b>${t.symbol}</b></td>
        <td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
        <td>$${(t.entry_price||0).toLocaleString()}</td>
        <td>$${(t.exit_price||0).toLocaleString()}</td>
        <td class="${pnlColor}"><b>${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}</b></td>
        <td>${t.duration_hours ? t.duration_hours.toFixed(1)+'h' : '-'}</td>
        <td><i>${t.reason_close||'-'}</i></td>
        <td>${analysis}</td>
      </tr>`;
    }).join("");
  }
}

loadData();
setInterval(loadData, 60000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/api/data")
def api_data():
    history     = load_json(TRADE_HISTORY_FILE)
    state       = load_json(RISK_STATE_FILE)
    open_trades = load_json(OPEN_TRADES_FILE)
    return jsonify({
        "history":     history,
        "state":       state,
        "open_trades": open_trades,
    })

if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)