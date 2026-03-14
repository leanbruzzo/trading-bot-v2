"""
MÓDULO 4: Risk Manager
Controla todos los límites de pérdida y calcula tamaño de posiciones.
"""
import json
import os
from datetime import datetime, date
from config.settings import (
    CAPITAL_TOTAL_USDT, MAX_POSITION_PCT, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    TRAILING_STOP_PCT, MAX_LOSS_DAILY_PCT, MAX_LOSS_WEEKLY_PCT,
    MAX_LOSS_MONTHLY_PCT, FLASH_CRASH_PCT, MAX_OPEN_POSITIONS, CASH_RESERVE_PCT,
    PARTIAL_TP_PCT, PARTIAL_TP_SIZE,
    POSITION_SIZE_LOW, POSITION_SIZE_MID, POSITION_SIZE_HIGH
)

RISK_STATE_FILE = "logs/risk_state.json"


def load_risk_state() -> dict:
    if os.path.exists(RISK_STATE_FILE):
        with open(RISK_STATE_FILE) as f:
            return json.load(f)
    return {
        "daily_pnl":      0.0,
        "weekly_pnl":     0.0,
        "monthly_pnl":    0.0,
        "paused_until":   None,
        "bot_stopped":    False,
        "last_reset":     str(date.today()),
        "open_positions": 0,
    }


def save_risk_state(state: dict):
    os.makedirs("logs", exist_ok=True)
    with open(RISK_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def reset_if_needed(state: dict) -> dict:
    today = str(date.today())
    if state["last_reset"] != today:
        state["daily_pnl"] = 0.0
        state["last_reset"] = today
    return state


def can_trade(state: dict) -> tuple[bool, str]:
    state = reset_if_needed(state)

    if state.get("bot_stopped"):
        return False, "🛑 Bot detenido — pérdida mensual máxima alcanzada"

    if state.get("paused_until"):
        paused = datetime.fromisoformat(state["paused_until"])
        if datetime.now() < paused:
            return False, f"⏸️ Bot en pausa hasta {paused.strftime('%H:%M %d/%m')}"
        else:
            state["paused_until"] = None
            save_risk_state(state)

    if state["open_positions"] >= MAX_OPEN_POSITIONS:
        return False, f"⚠️ Máximo de posiciones abiertas ({MAX_OPEN_POSITIONS}) alcanzado"

    if abs(state["daily_pnl"]) >= MAX_LOSS_DAILY_PCT * CAPITAL_TOTAL_USDT:
        return False, "⏸️ Pérdida diaria máxima alcanzada — pausa 24hs"

    if abs(state["weekly_pnl"]) >= MAX_LOSS_WEEKLY_PCT * CAPITAL_TOTAL_USDT:
        return False, "⏸️ Pérdida semanal máxima alcanzada"

    if abs(state["monthly_pnl"]) >= MAX_LOSS_MONTHLY_PCT * CAPITAL_TOTAL_USDT:
        state["bot_stopped"] = True
        save_risk_state(state)
        return False, "🛑 Pérdida mensual máxima alcanzada — bot detenido"

    return True, "OK"


def calculate_position_size(available_capital: float, signal_score: float) -> float:
    """Calcula tamaño de posición dinámico según fuerza de la señal."""
    usable = available_capital * (1 - CASH_RESERVE_PCT)
    score  = abs(signal_score)

    if score > 0.70:
        pct = POSITION_SIZE_HIGH
    elif score > 0.50:
        pct = POSITION_SIZE_MID
    else:
        pct = POSITION_SIZE_LOW

    return round(usable * pct, 2)


def calculate_stop_loss(entry_price: float, side: str) -> float:
    if side == "LONG":
        return round(entry_price * (1 - STOP_LOSS_PCT), 4)
    else:
        return round(entry_price * (1 + STOP_LOSS_PCT), 4)


def calculate_take_profit(entry_price: float, side: str) -> float:
    if side == "LONG":
        return round(entry_price * (1 + TAKE_PROFIT_PCT), 4)
    else:
        return round(entry_price * (1 - TAKE_PROFIT_PCT), 4)


def calculate_partial_tp(entry_price: float, side: str) -> float:
    """Calcula el precio del take profit parcial (3%)."""
    if side == "LONG":
        return round(entry_price * (1 + PARTIAL_TP_PCT), 4)
    else:
        return round(entry_price * (1 - PARTIAL_TP_PCT), 4)


def update_trailing_stop(current_price: float, current_stop: float, side: str) -> float:
    if side == "LONG":
        new_stop = current_price * (1 - TRAILING_STOP_PCT)
        return round(max(new_stop, current_stop), 4)
    else:
        new_stop = current_price * (1 + TRAILING_STOP_PCT)
        return round(min(new_stop, current_stop), 4)


def register_pnl(pnl_usdt: float):
    state = load_risk_state()
    state["daily_pnl"]   += pnl_usdt
    state["weekly_pnl"]  += pnl_usdt
    state["monthly_pnl"] += pnl_usdt
    save_risk_state(state)


def is_flash_crash(candles_15m: list, current_price: float) -> bool:
    if not candles_15m or len(candles_15m) < 2:
        return False
    price_15m_ago = float(candles_15m[-2]["close"])
    drop = (price_15m_ago - current_price) / price_15m_ago
    return drop >= FLASH_CRASH_PCT