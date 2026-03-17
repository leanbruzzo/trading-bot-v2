"""
DASHBOARD: Servidor web para visualizar P&L e historial de trades.
"""
import json
import os
from flask import Flask, jsonify

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
  .container { padding: 25px 30px; max-width: 1300px; margin: 0 auto; }
  .period-selector { display: flex; gap: 10px; margin-bottom: 25px; }
  .period-btn { padding: 8px 20px; border-radius: 8px; border: 1px solid #2a2a4a; background: #1a1a2e; color: #888; cursor: pointer; font-size: 13px; transition: all 0.2s; }
  .period-btn.active { background: #6c63ff; color: #fff; border-color: #6c63ff; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-bottom: 25px; }
  .card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }
  .card .label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .card .value { font-size: 24px; font-weight: 700; }
  .card .sub { font-size: 11px; color: #555; margin-top: 4px; }
  .green { color: #00ff88; } .red { color: #ff4466; } .white { color: #fff; } .yellow { color: #ffd700; }
  .charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
  .chart-card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; }
  .chart-card.full { grid-column: 1 / -1; }
  .chart-card h2 { font-size: 14px; color: #aaa; margin-bottom: 15px; }
  .table-card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4a; margin-bottom: 25px; }
  .table-card h2 { font-size: 14px; color: #aaa; margin-bottom: 15px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; padding: 10px; color: #666; font-weight: 500; border-bottom: 1px solid #2a2a4a; }
  td { padding: 9px 10px; border-bottom: 1px solid #16162a; }
  tr:hover { background: #22223a; }
  .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-long { background: #00ff8822; color: #00ff88; }
  .badge-short { background: #ff446622; color: #ff4466; }
  .details { font-size: 11px; color: #555; margin-top: 3px; }
  .open-section { margin-bottom: 25px; }
  .refresh { font-size: 11px; color: #444; margin-top: 20px; text-align: center; padding-bottom: 30px; }
  .stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #16162a; font-size: 13px; }
  .stat-row:last-child { border: none; }
  .stat-label { color: #666; }
</style>
</head>
<body>
<div class="header">
  <div class="dot"></div>
  <h1>🤖 Trading Bot Dashboard</h1>
</div>
<div class="container">

  <!-- Selector de período -->
  <div class="period-selector">
    <button class="period-btn active" onclick="setPeriod('all')">Todo</button>
    <button class="period-btn" onclick="setPeriod('month')">Este mes</button>
    <button class="period-btn" onclick="setPeriod('week')">Esta semana</button>
    <button class="period-btn" onclick="setPeriod('today')">Hoy</button>
  </div>

  <!-- Métricas principales -->
  <div class="metrics" id="metrics">Cargando...</div>

  <!-- Posiciones abiertas -->
  <div class="open-section">
    <div class="table-card">
      <h2>📂 Posiciones Abiertas</h2>
      <table>
        <thead><tr><th>Par</th><th>Dir.</th><th>Entrada</th><th>Stop</th><th>TP</th><th>Partial TP</th><th>P&L Estimado</th><th>Desde</th></tr></thead>
        <tbody id="open-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- Gráficos fila 1 -->
  <div class="charts-grid">
    <div class="chart-card full">
      <h2>📈 P&L Acumulado</h2>
      <canvas id="pnlChart" height="60"></canvas>
    </div>
  </div>

  <!-- Gráficos fila 2 -->
  <div class="charts-grid">
    <div class="chart-card">
      <h2>📊 P&L por Día</h2>
      <canvas id="dailyChart" height="160"></canvas>
    </div>
    <div class="chart-card">
      <h2>🪙 P&L por Activo</h2>
      <canvas id="assetChart" height="160"></canvas>
    </div>
  </div>

  <!-- Gráficos fila 3 -->
  <div class="charts-grid">
    <div class="chart-card">
      <h2>🎯 Motivos de Cierre</h2>
      <canvas id="reasonChart" height="160"></canvas>
    </div>
    <div class="chart-card">
      <h2>📉 P&L LONG vs SHORT</h2>
      <canvas id="sideChart" height="160"></canvas>
    </div>
  </div>

  <!-- Gráficos fila 4 -->
  <div class="charts-grid">
    <div class="chart-card">
      <h2>🌊 Win Rate por Régimen</h2>
      <canvas id="regimeChart" height="160"></canvas>
    </div>
    <div class="chart-card">
      <h2>⚡ Win Rate por Score de Entrada</h2>
      <canvas id="scoreChart" height="160"></canvas>
    </div>
  </div>

  <!-- Stats adicionales -->
  <div class="charts-grid">
    <div class="chart-card">
      <h2>⏱️ Duración Promedio por Resultado</h2>
      <canvas id="durationChart" height="160"></canvas>
    </div>
    <div class="chart-card">
      <h2>📋 Estadísticas Avanzadas</h2>
      <div id="advanced-stats"></div>
    </div>
  </div>

  <!-- Historial -->
  <div class="table-card">
    <h2>📋 Historial de Trades</h2>
    <table>
      <thead>
        <tr>
          <th>Fecha</th><th>Par</th><th>Dir.</th><th>Entrada</th>
          <th>Salida</th><th>P&L</th><th>Duración</th><th>Motivo</th><th>Análisis Apertura</th>
        </tr>
      </thead>
      <tbody id="history-tbody"></tbody>
    </table>
  </div>

  <div class="refresh" id="refresh-label">Actualización automática cada 60 segundos</div>
</div>

<script>
let charts = {};
let currentPeriod = 'all';
let allData = null;

function setPeriod(period) {
  currentPeriod = period;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  if (allData) renderAll(allData);
}

function filterByPeriod(history, period) {
  const now = new Date();
  return history.filter(t => {
    if (!t.closed_at) return false;
    const d = new Date(t.closed_at);
    if (period === 'today') {
      return d.toDateString() === now.toDateString();
    } else if (period === 'week') {
      const weekAgo = new Date(now); weekAgo.setDate(now.getDate() - 7);
      return d >= weekAgo;
    } else if (period === 'month') {
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }
    return true;
  });
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function renderAll(data) {
  const { state, open_trades } = data;
  const history = filterByPeriod(data.history, currentPeriod);

  // ── Métricas ──────────────────────────────────────────────────────────────
  const wins      = history.filter(t => t.pnl > 0).length;
  const losses    = history.filter(t => t.pnl <= 0).length;
  const winrate   = history.length > 0 ? ((wins / history.length) * 100).toFixed(1) : 0;
  const totalPnl  = history.reduce((a, t) => a + t.pnl, 0);
  const avgPnl    = history.length > 0 ? (totalPnl / history.length).toFixed(2) : 0;
  const bestTrade = history.length > 0 ? Math.max(...history.map(t => t.pnl)) : 0;
  const worstTrade= history.length > 0 ? Math.min(...history.map(t => t.pnl)) : 0;

  // Drawdown máximo
  const sorted = [...history].sort((a,b) => new Date(a.closed_at)-new Date(b.closed_at));
  let peak = 0, cum = 0, maxDD = 0;
  sorted.forEach(t => {
    cum += t.pnl;
    if (cum > peak) peak = cum;
    const dd = peak - cum;
    if (dd > maxDD) maxDD = dd;
  });

  // Racha
  let maxWinStreak = 0, maxLossStreak = 0, curWin = 0, curLoss = 0;
  sorted.forEach(t => {
    if (t.pnl > 0) { curWin++; curLoss = 0; maxWinStreak = Math.max(maxWinStreak, curWin); }
    else { curLoss++; curWin = 0; maxLossStreak = Math.max(maxLossStreak, curLoss); }
  });

  document.getElementById("metrics").innerHTML = `
    <div class="card"><div class="label">P&L Total</div><div class="value ${totalPnl>=0?'green':'red'}">${totalPnl>=0?'+':''}$${totalPnl.toFixed(2)}</div></div>
    <div class="card"><div class="label">P&L Hoy</div><div class="value ${(state.daily_pnl||0)>=0?'green':'red'}">${(state.daily_pnl||0)>=0?'+':''}$${(state.daily_pnl||0).toFixed(2)}</div></div>
    <div class="card"><div class="label">Win Rate</div><div class="value white">${winrate}%</div><div class="sub">${wins}W / ${losses}L</div></div>
    <div class="card"><div class="label">Total Trades</div><div class="value white">${history.length}</div></div>
    <div class="card"><div class="label">P&L Promedio</div><div class="value ${avgPnl>=0?'green':'red'}">${avgPnl>=0?'+':''}$${avgPnl}</div></div>
    <div class="card"><div class="label">Mejor Trade</div><div class="value green">+$${bestTrade.toFixed(2)}</div></div>
    <div class="card"><div class="label">Peor Trade</div><div class="value red">$${worstTrade.toFixed(2)}</div></div>
    <div class="card"><div class="label">Max Drawdown</div><div class="value red">-$${maxDD.toFixed(2)}</div></div>
    <div class="card"><div class="label">Posiciones</div><div class="value white">${Object.keys(open_trades).length}</div><div class="sub">abiertas</div></div>
  `;

  // ── Posiciones abiertas ───────────────────────────────────────────────────
  const openKeys = Object.keys(open_trades);
  document.getElementById("open-tbody").innerHTML = openKeys.length === 0
    ? `<tr><td colspan="8" style="color:#555;text-align:center;padding:20px">Sin posiciones abiertas</td></tr>`
    : openKeys.map(symbol => {
        const t = open_trades[symbol];
        const partial = t.partial_done ? "✅ Tomado" : "⏳ Pendiente";
        const since   = t.opened_at ? t.opened_at.replace("T"," ").slice(0,16) : "-";
        return `<tr>
          <td><b>${symbol}</b></td>
          <td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
          <td>$${(t.entry||0).toLocaleString()}</td>
          <td>$${(t.stop||0).toLocaleString()}</td>
          <td>$${(t.tp||0).toLocaleString()}</td>
          <td>${partial}</td>
          <td>-</td>
          <td>${since}</td>
        </tr>`;
      }).join("");

  // ── P&L Acumulado ─────────────────────────────────────────────────────────
  destroyChart('pnl');
  let cumPnl = 0;
  const pnlLabels = sorted.map(t => t.closed_at.replace("T"," ").slice(0,16));
  const pnlValues = sorted.map(t => { cumPnl += t.pnl; return +cumPnl.toFixed(2); });
  charts['pnl'] = new Chart(document.getElementById("pnlChart"), {
    type: "line",
    data: { labels: pnlLabels, datasets: [{ label: "P&L Acumulado (USDT)", data: pnlValues, borderColor: "#6c63ff", backgroundColor: "rgba(108,99,255,0.08)", pointBackgroundColor: pnlValues.map(v => v>=0?"#00ff88":"#ff4466"), tension: 0.3, fill: true }] },
    options: { plugins: { legend: { labels: { color: "#666" } } }, scales: { x: { ticks: { color: "#555", maxTicksLimit: 10 }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666" }, grid: { color: "#2a2a4a" } } } }
  });

  // ── P&L por Día ──────────────────────────────────────────────────────────
  destroyChart('daily');
  const byDay = {};
  history.forEach(t => {
    const day = t.closed_at ? t.closed_at.slice(0,10) : 'unknown';
    byDay[day] = (byDay[day] || 0) + t.pnl;
  });
  const dayKeys = Object.keys(byDay).sort();
  charts['daily'] = new Chart(document.getElementById("dailyChart"), {
    type: "bar",
    data: { labels: dayKeys, datasets: [{ label: "P&L Diario", data: dayKeys.map(d => +byDay[d].toFixed(2)), backgroundColor: dayKeys.map(d => byDay[d]>=0?"rgba(0,255,136,0.5)":"rgba(255,68,102,0.5)"), borderColor: dayKeys.map(d => byDay[d]>=0?"#00ff88":"#ff4466"), borderWidth: 1 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666" }, grid: { color: "#2a2a4a" } } } }
  });

  // ── P&L por Activo ────────────────────────────────────────────────────────
  destroyChart('asset');
  const byAsset = {};
  history.forEach(t => { byAsset[t.symbol] = (byAsset[t.symbol]||0) + t.pnl; });
  const assetKeys = Object.keys(byAsset);
  charts['asset'] = new Chart(document.getElementById("assetChart"), {
    type: "bar",
    data: { labels: assetKeys, datasets: [{ label: "P&L por Activo", data: assetKeys.map(k => +byAsset[k].toFixed(2)), backgroundColor: assetKeys.map(k => byAsset[k]>=0?"rgba(0,255,136,0.5)":"rgba(255,68,102,0.5)"), borderColor: assetKeys.map(k => byAsset[k]>=0?"#00ff88":"#ff4466"), borderWidth: 1 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666" }, grid: { color: "#2a2a4a" } } } }
  });

  // ── Motivos de Cierre ─────────────────────────────────────────────────────
  destroyChart('reason');
  const byReason = {};
  history.forEach(t => {
    const r = t.reason_close || 'Desconocido';
    const key = r.includes('Stop') ? 'Stop-Loss' : r.includes('Take-Profit') ? 'Take-Profit' : r.includes('Señal') ? 'Señal Invertida' : r;
    byReason[key] = (byReason[key]||0) + 1;
  });
  charts['reason'] = new Chart(document.getElementById("reasonChart"), {
    type: "doughnut",
    data: { labels: Object.keys(byReason), datasets: [{ data: Object.values(byReason), backgroundColor: ["#ff4466","#00ff88","#6c63ff","#ffd700","#00bfff"], borderWidth: 0 }] },
    options: { plugins: { legend: { labels: { color: "#888" }, position: 'bottom' } } }
  });

  // ── LONG vs SHORT ─────────────────────────────────────────────────────────
  destroyChart('side');
  const longTrades  = history.filter(t => t.side === 'LONG');
  const shortTrades = history.filter(t => t.side === 'SHORT');
  const longPnl  = longTrades.reduce((a,t) => a+t.pnl, 0);
  const shortPnl = shortTrades.reduce((a,t) => a+t.pnl, 0);
  const longWR   = longTrades.length > 0 ? (longTrades.filter(t=>t.pnl>0).length/longTrades.length*100).toFixed(1) : 0;
  const shortWR  = shortTrades.length > 0 ? (shortTrades.filter(t=>t.pnl>0).length/shortTrades.length*100).toFixed(1) : 0;
  charts['side'] = new Chart(document.getElementById("sideChart"), {
    type: "bar",
    data: {
      labels: [`LONG (${longTrades.length} trades, WR ${longWR}%)`, `SHORT (${shortTrades.length} trades, WR ${shortWR}%)`],
      datasets: [{ label: "P&L Total", data: [+longPnl.toFixed(2), +shortPnl.toFixed(2)], backgroundColor: [longPnl>=0?"rgba(0,255,136,0.5)":"rgba(255,68,102,0.5)", shortPnl>=0?"rgba(0,255,136,0.5)":"rgba(255,68,102,0.5)"], borderColor: [longPnl>=0?"#00ff88":"#ff4466", shortPnl>=0?"#00ff88":"#ff4466"], borderWidth: 1 }]
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666" }, grid: { color: "#2a2a4a" } } } }
  });

  // ── Win Rate por Régimen ──────────────────────────────────────────────────
  destroyChart('regime');
  const byRegime = {};
  history.forEach(t => {
    const r = t.analysis_open?.regime || 'Desconocido';
    if (!byRegime[r]) byRegime[r] = { wins: 0, total: 0 };
    byRegime[r].total++;
    if (t.pnl > 0) byRegime[r].wins++;
  });
  const regimeKeys = Object.keys(byRegime);
  charts['regime'] = new Chart(document.getElementById("regimeChart"), {
    type: "bar",
    data: { labels: regimeKeys, datasets: [{ label: "Win Rate %", data: regimeKeys.map(k => +(byRegime[k].wins/byRegime[k].total*100).toFixed(1)), backgroundColor: "rgba(108,99,255,0.5)", borderColor: "#6c63ff", borderWidth: 1 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666", callback: v => v+'%' }, grid: { color: "#2a2a4a" }, max: 100 } } }
  });

  // ── Win Rate por Score ────────────────────────────────────────────────────
  destroyChart('score');
  const scoreGroups = { 'Baja (0.35-0.50)': {w:0,t:0}, 'Media (0.50-0.70)': {w:0,t:0}, 'Alta (>0.70)': {w:0,t:0} };
  history.forEach(t => {
    const s = Math.abs(t.analysis_open?.combined_score || 0);
    const g = s > 0.70 ? 'Alta (>0.70)' : s > 0.50 ? 'Media (0.50-0.70)' : 'Baja (0.35-0.50)';
    scoreGroups[g].t++;
    if (t.pnl > 0) scoreGroups[g].w++;
  });
  charts['score'] = new Chart(document.getElementById("scoreChart"), {
    type: "bar",
    data: { labels: Object.keys(scoreGroups), datasets: [{ label: "Win Rate %", data: Object.keys(scoreGroups).map(k => scoreGroups[k].t > 0 ? +(scoreGroups[k].w/scoreGroups[k].t*100).toFixed(1) : 0), backgroundColor: ["rgba(0,191,255,0.5)","rgba(108,99,255,0.5)","rgba(255,215,0,0.5)"], borderColor: ["#00bfff","#6c63ff","#ffd700"], borderWidth: 1 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666", callback: v => v+'%' }, grid: { color: "#2a2a4a" }, max: 100 } } }
  });

  // ── Duración promedio ─────────────────────────────────────────────────────
  destroyChart('duration');
  const winDur  = history.filter(t=>t.pnl>0).map(t=>t.duration_hours||0);
  const lossDur = history.filter(t=>t.pnl<=0).map(t=>t.duration_hours||0);
  const avgWinDur  = winDur.length  > 0 ? (winDur.reduce((a,b)=>a+b,0)/winDur.length).toFixed(1)  : 0;
  const avgLossDur = lossDur.length > 0 ? (lossDur.reduce((a,b)=>a+b,0)/lossDur.length).toFixed(1) : 0;
  charts['duration'] = new Chart(document.getElementById("durationChart"), {
    type: "bar",
    data: { labels: [`Ganadores (${winDur.length})`, `Perdedores (${lossDur.length})`], datasets: [{ label: "Duración promedio (horas)", data: [avgWinDur, avgLossDur], backgroundColor: ["rgba(0,255,136,0.5)","rgba(255,68,102,0.5)"], borderColor: ["#00ff88","#ff4466"], borderWidth: 1 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#555" }, grid: { color: "#16162a" } }, y: { ticks: { color: "#666" }, grid: { color: "#2a2a4a" } } } }
  });

  // ── Estadísticas Avanzadas ────────────────────────────────────────────────
  const avgWin  = winDur.length  > 0 ? (history.filter(t=>t.pnl>0).reduce((a,t)=>a+t.pnl,0)/wins).toFixed(2) : 0;
  const avgLoss = lossDur.length > 0 ? (history.filter(t=>t.pnl<=0).reduce((a,t)=>a+t.pnl,0)/losses).toFixed(2) : 0;
  const rrRatio = avgLoss != 0 ? Math.abs(avgWin/avgLoss).toFixed(2) : '-';
  const partialTaken = history.filter(t=>t.partial_tp_taken).length;
  document.getElementById("advanced-stats").innerHTML = `
    <div class="stat-row"><span class="stat-label">Ganancia promedio (wins)</span><span class="green">+$${avgWin}</span></div>
    <div class="stat-row"><span class="stat-label">Pérdida promedio (losses)</span><span class="red">$${avgLoss}</span></div>
    <div class="stat-row"><span class="stat-label">Ratio ganancia/pérdida</span><span class="white">${rrRatio}</span></div>
    <div class="stat-row"><span class="stat-label">Racha ganadora máx.</span><span class="green">${maxWinStreak} trades</span></div>
    <div class="stat-row"><span class="stat-label">Racha perdedora máx.</span><span class="red">${maxLossStreak} trades</span></div>
    <div class="stat-row"><span class="stat-label">Max Drawdown</span><span class="red">-$${maxDD.toFixed(2)}</span></div>
    <div class="stat-row"><span class="stat-label">Partial TP tomado</span><span class="yellow">${partialTaken} / ${history.length}</span></div>
    <div class="stat-row"><span class="stat-label">Duración prom. ganadores</span><span class="white">${avgWinDur}h</span></div>
    <div class="stat-row"><span class="stat-label">Duración prom. perdedores</span><span class="white">${avgLossDur}h</span></div>
  `;

  // ── Historial ─────────────────────────────────────────────────────────────
  const tbody = document.getElementById("history-tbody");
  if (history.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="color:#555;text-align:center;padding:20px">Sin trades en este período</td></tr>`;
  } else {
    tbody.innerHTML = [...history].reverse().map(t => {
      const ao = t.analysis_open || {};
      return `<tr>
        <td>${t.closed_at?t.closed_at.replace("T"," ").slice(0,16):'-'}</td>
        <td><b>${t.symbol}</b></td>
        <td><span class="badge badge-${(t.side||'').toLowerCase()}">${t.side}</span></td>
        <td>$${(t.entry_price||0).toLocaleString()}</td>
        <td>$${(t.exit_price||0).toLocaleString()}</td>
        <td class="${t.pnl>=0?'green':'red'}"><b>${t.pnl>=0?'+':''}$${t.pnl.toFixed(2)}</b></td>
        <td>${t.duration_hours?t.duration_hours.toFixed(1)+'h':'-'}</td>
        <td><i>${t.reason_close||'-'}</i></td>
        <td>
          <div class="details">régimen=${ao.regime||'-'} | RSI=${ao.rsi||'-'} | score=${ao.combined_score||'-'}</div>
          <div class="details">vol=${ao.volume_confirm?'✅':'❌'} | MA=${ao.ma_signal||'-'} | mom=${ao.momentum||'-'}</div>
        </td>
      </tr>`;
    }).join("");
  }

  document.getElementById("refresh-label").textContent = "Última actualización: " + new Date().toLocaleTimeString();
}

async function loadData() {
  const res = await fetch("/api/data");
  allData = await res.json();
  renderAll(allData);
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