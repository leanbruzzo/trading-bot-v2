"""
MÓDULO PRINCIPAL: Trading Bot Orchestrator
Coordina todos los módulos y ejecuta el loop principal.
"""
import time
import logging
import pandas as pd
import json
import os
from datetime import datetime

from config.settings import (
    SYMBOLS, BOT_INTERVAL_SECONDS, SENTIMENT_WEIGHT, TECHNICAL_WEIGHT,
    REGIME_WEIGHT, PARTIAL_TP_PCT, PARTIAL_TP_SIZE,
    SIGNAL_THRESHOLD, SIGNAL_REVERSAL_COOLDOWN
)
from modules.regime_detector    import detect_regime
from modules.signal_generator   import calculate_signals
from modules.sentiment_analyzer import get_combined_sentiment
from modules.risk_manager       import (
    load_risk_state, save_risk_state, can_trade, calculate_position_size,
    calculate_stop_loss, calculate_take_profit, calculate_partial_tp,
    update_trailing_stop, register_pnl, is_flash_crash,
    load_open_trades, save_open_trades
)
from modules.order_executor import (
    setup_symbol, get_balance, get_klines, get_current_price,
    open_long, open_short, close_position, get_open_positions
)
from modules.sheets_logger import log_trade_to_sheets
from modules.notifier import (
    notify_trade_open, notify_trade_close, notify_risk_alert,
    notify_bot_stopped, notify_flash_crash, notify_daily_summary,
    send_message, start_command_listener
)

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("bot.main")

# ── Estado ────────────────────────────────────────────────────────────────────
open_trades: dict = load_open_trades()

TRADE_HISTORY_FILE = "logs/trade_history.json"

# ── Cooldown de señales invertidas ────────────────────────────────────────────
# { "BTCUSDT": datetime_del_ultimo_cierre_por_inversion }
reversal_cooldown: dict = {}


# ── Historial ─────────────────────────────────────────────────────────────────

def load_trade_history() -> list:
    if os.path.exists(TRADE_HISTORY_FILE):
        with open(TRADE_HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_trade_to_history(record: dict):
    history = load_trade_history()
    history.append(record)
    with open(TRADE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    logger.info(f"📝 Trade guardado: {record['symbol']} {record['side']} P&L=${record['pnl']:+.2f}")
    log_trade_to_sheets(record)


def klines_to_df(candles: list) -> pd.DataFrame:
    return pd.DataFrame(candles, columns=["open", "high", "low", "close", "volume"])


def decide_action(symbol: str, df: pd.DataFrame, current_price: float) -> tuple[str, float, dict]:
    regime_data    = detect_regime(df)
    technical_data = calculate_signals(df)
    sentiment_data = get_combined_sentiment(symbol)

    regime  = regime_data["regime"]
    t_score = technical_data["technical_score"]
    s_score = sentiment_data["sentiment_score"]

    if regime == "TRENDING_UP":
        regime_score = 0.7
    elif regime == "TRENDING_DOWN":
        regime_score = -0.7
    elif regime == "RANGING":
        regime_score = 0.0
    else:
        regime_score = 0.0

    combined = (
        t_score      * TECHNICAL_WEIGHT +
        regime_score * REGIME_WEIGHT +
        s_score      * SENTIMENT_WEIGHT
    )

    if regime == "VOLATILE":
        combined *= 0.5

    analysis = {
        "regime":          regime,
        "regime_score":    round(regime_score, 2),
        "technical_score": t_score,
        "sentiment_score": round(s_score, 3),
        "combined_score":  round(combined, 3),
        "rsi":             technical_data["rsi"],
        "ma_signal":       technical_data["ma_signal"],
        "ma_short":        technical_data["ma_short"],
        "ma_long":         technical_data["ma_long"],
        "momentum":        technical_data["momentum"],
        "mom_signal":      technical_data["mom_signal"],
        "rsi_signal":      technical_data["rsi_signal"],
        "volume_confirm":  technical_data["volume_confirm"],
        "adx":             regime_data.get("adx", None),
        "atr":             regime_data.get("atr", None),
    }

    logger.info(
        f"{symbol} | régimen={regime} | técnico={t_score:.2f} | "
        f"sentiment={s_score:.2f} | combined={combined:.2f} | "
        f"RSI={technical_data['rsi']:.1f} | vol_confirm={technical_data['volume_confirm']}"
    )

    if combined >= SIGNAL_THRESHOLD:
        return "LONG", combined, analysis
    elif combined <= -SIGNAL_THRESHOLD:
        return "SHORT", combined, analysis
    else:
        return "FLAT", combined, analysis


def is_in_cooldown(symbol: str) -> bool:
    """Verifica si el símbolo está en cooldown tras una señal invertida."""
    if symbol not in reversal_cooldown:
        return False
    elapsed = (datetime.now() - reversal_cooldown[symbol]).total_seconds() / 60
    if elapsed < SIGNAL_REVERSAL_COOLDOWN:
        remaining = int(SIGNAL_REVERSAL_COOLDOWN - elapsed)
        logger.info(f"⏳ {symbol} en cooldown — {remaining} min restantes")
        return True
    del reversal_cooldown[symbol]
    return False


def manage_open_trade(symbol: str, current_price: float, df: pd.DataFrame):
    trade = open_trades[symbol]
    side  = trade["side"]

    # ── Partial Take Profit ───────────────────────────────────────────────────
    if not trade["partial_done"]:
        hit_partial = (
            (side == "LONG"  and current_price >= trade["partial_tp"]) or
            (side == "SHORT" and current_price <= trade["partial_tp"])
        )
        if hit_partial:
            partial_qty = round(trade["qty"] * PARTIAL_TP_SIZE, 4)
            order = close_position(symbol, side, partial_qty)
            if order:
                pnl = abs(current_price - trade["entry"]) * partial_qty
                register_pnl(pnl)
                notify_trade_close(
                    symbol, side, trade["entry"], current_price,
                    pnl, f"Take Profit parcial 50% (+{PARTIAL_TP_PCT*100:.0f}%)"
                )
                logger.info(f"✅ Partial TP {symbol} — P&L parcial: ${pnl:+.2f}")
                open_trades[symbol]["partial_done"] = True
                open_trades[symbol]["stop"]         = trade["entry"]
                open_trades[symbol]["qty"]          = round(trade["qty"] - partial_qty, 4)
                save_open_trades(open_trades)
                logger.info(f"🔒 Stop movido a breakeven: ${trade['entry']}")
            return

    # ── Trailing stop ─────────────────────────────────────────────────────────
    new_stop = update_trailing_stop(current_price, trade["stop"], side)
    open_trades[symbol]["stop"] = new_stop

    # ── Verificaciones de cierre ──────────────────────────────────────────────
    hit_stop = (
        (side == "LONG"  and current_price <= new_stop) or
        (side == "SHORT" and current_price >= new_stop)
    )
    hit_tp = (
        (side == "LONG"  and current_price >= trade["tp"]) or
        (side == "SHORT" and current_price <= trade["tp"])
    )
    new_signal, new_score, new_analysis = decide_action(symbol, df, current_price)
    signal_reversed = (
        (side == "LONG"  and new_signal == "SHORT") or
        (side == "SHORT" and new_signal == "LONG")
    )

    reason = None
    if hit_stop:
        reason = "Stop-Loss" + (" (breakeven)" if trade["partial_done"] else "")
    elif hit_tp:
        reason = "Take-Profit final"
    elif signal_reversed:
        reason = f"Señal invertida → {new_signal}"

    if reason:
        order = close_position(symbol, side, trade["qty"])
        if order:
            pnl = (current_price - trade["entry"]) * trade["qty"]
            if side == "SHORT":
                pnl = -pnl
            register_pnl(pnl)
            notify_trade_close(symbol, side, trade["entry"], current_price, pnl, reason)
            logger.info(f"Posición cerrada {symbol} | P&L: ${pnl:+.2f} | {reason}")

            opened_at = trade.get("opened_at", datetime.now().isoformat())
            closed_at = datetime.now().isoformat()
            duration  = (datetime.fromisoformat(closed_at) - datetime.fromisoformat(opened_at)).total_seconds() / 3600

            save_trade_to_history({
                "symbol":           symbol,
                "side":             side,
                "entry_price":      trade["entry"],
                "exit_price":       current_price,
                "qty":              trade["qty"],
                "pnl":              round(pnl, 4),
                "reason_close":     reason,
                "partial_tp_taken": trade.get("partial_done", False),
                "opened_at":        opened_at,
                "closed_at":        closed_at,
                "duration_hours":   round(duration, 2),
                "analysis_open":    trade.get("analysis_open", {}),
                "analysis_close":   new_analysis,
            })

            # Si fue señal invertida → activar cooldown
            if signal_reversed:
                reversal_cooldown[symbol] = datetime.now()
                logger.info(f"⏳ Cooldown activado para {symbol} — {SIGNAL_REVERSAL_COOLDOWN} min")

            del open_trades[symbol]
            save_open_trades(open_trades)

            state = load_risk_state()
            state["open_positions"] = len(open_trades)
            save_risk_state(state)

            # Abrir en nueva dirección solo si NO está en cooldown
            if signal_reversed and not is_in_cooldown(symbol):
                open_new_trade(symbol, new_signal, current_price, new_score, df, new_analysis)


def open_new_trade(symbol: str, direction: str, current_price: float, score: float,
                   df: pd.DataFrame, analysis: dict = None):
    # Verificar cooldown
    if is_in_cooldown(symbol):
        return

    state = load_risk_state()
    ok, reason = can_trade(state)
    if not ok:
        logger.warning(f"Trade bloqueado: {reason}")
        notify_risk_alert(reason)
        return

    if analysis is None:
        _, _, analysis = decide_action(symbol, df, current_price)

    balance    = get_balance()
    size       = calculate_position_size(balance, score)
    stop       = calculate_stop_loss(current_price, direction)
    tp         = calculate_take_profit(current_price, direction)
    partial_tp = calculate_partial_tp(current_price, direction)

    if direction == "LONG":
        result = open_long(symbol, size)
    else:
        result = open_short(symbol, size)

    if result:
        open_trades[symbol] = {
            "side":          direction,
            "qty":           result["qty"],
            "entry":         result["entry_price"],
            "stop":          stop,
            "tp":            tp,
            "partial_tp":    partial_tp,
            "partial_done":  False,
            "signal_score":  score,
            "opened_at":     datetime.now().isoformat(),
            "analysis_open": analysis,
        }
        save_open_trades(open_trades)

        state["open_positions"] = len(open_trades)
        save_risk_state(state)

        size_label = "🔥 ALTA" if abs(score) > 0.70 else "⚡ MEDIA" if abs(score) > 0.50 else "🔹 BAJA"
        notify_trade_open(symbol, direction, result["entry_price"], stop, tp, size)
        send_message(
            f"📐 <b>Tamaño de posición:</b> {size_label} (score={score:.2f})\n"
            f"🎯 <b>Partial TP al 4.5%:</b> ${partial_tp:,.2f}\n"
            f"🔒 <b>Stop post-partial:</b> Breakeven (${result['entry_price']:,.2f})"
        )


def emergency_close_all(reason: str):
    logger.critical(f"🚨 CIERRE DE EMERGENCIA: {reason}")
    for symbol, trade in list(open_trades.items()):
        price = get_current_price(symbol)
        order = close_position(symbol, trade["side"], trade["qty"])
        if order and price:
            pnl = (price - trade["entry"]) * trade["qty"]
            if trade["side"] == "SHORT":
                pnl = -pnl
            register_pnl(pnl)
            notify_trade_close(symbol, trade["side"], trade["entry"], price, pnl, reason)

            opened_at = trade.get("opened_at", datetime.now().isoformat())
            closed_at = datetime.now().isoformat()
            duration  = (datetime.fromisoformat(closed_at) - datetime.fromisoformat(opened_at)).total_seconds() / 3600

            save_trade_to_history({
                "symbol":           symbol,
                "side":             trade["side"],
                "entry_price":      trade["entry"],
                "exit_price":       price,
                "qty":              trade["qty"],
                "pnl":              round(pnl, 4),
                "reason_close":     reason,
                "partial_tp_taken": trade.get("partial_done", False),
                "opened_at":        opened_at,
                "closed_at":        closed_at,
                "duration_hours":   round(duration, 2),
                "analysis_open":    trade.get("analysis_open", {}),
                "analysis_close":   {},
            })
            del open_trades[symbol]
    save_open_trades(open_trades)
    notify_bot_stopped(reason)


def run():
    logger.info("🚀 Trading Bot iniciado — v2.0 (cooldown + señales mejoradas)")
    loaded = len(open_trades)
    send_message(
        f"🚀 <b>Trading Bot iniciado v2.0</b>\n"
        f"Monitoreando: {', '.join(SYMBOLS)}\n"
        f"📐 Umbral señal: {SIGNAL_THRESHOLD} | Stop: 3.5% | TP: 7%\n"
        f"⏳ Cooldown inversión: {SIGNAL_REVERSAL_COOLDOWN} min\n"
        f"📂 Posiciones recuperadas: <b>{loaded}</b>"
    )

    for symbol in SYMBOLS:
        setup_symbol(symbol)

    start_command_listener(open_trades)

    daily_trade_count = 0
    last_summary_date = datetime.now().date()

    while True:
        try:
            today = datetime.now().date()
            if today != last_summary_date:
                state = load_risk_state()
                notify_daily_summary(daily_trade_count, state["daily_pnl"], len(open_trades))
                daily_trade_count = 0
                last_summary_date = today

            for symbol in SYMBOLS:
                candles = get_klines(symbol, limit=100)
                if not candles:
                    continue

                df            = klines_to_df(candles)
                current_price = get_current_price(symbol)

                if is_flash_crash(candles, current_price):
                    notify_flash_crash(symbol, current_price, 10.0)
                    emergency_close_all(f"Flash crash detectado en {symbol}")
                    break

                if symbol in open_trades:
                    manage_open_trade(symbol, current_price, df)
                else:
                    # Verificar cooldown antes de buscar entrada
                    if is_in_cooldown(symbol):
                        continue

                    state = load_risk_state()
                    ok, block_reason = can_trade(state)
                    if not ok:
                        logger.info(f"Sin operar {symbol}: {block_reason}")
                        continue

                    direction, score, analysis = decide_action(symbol, df, current_price)
                    if direction != "FLAT":
                        open_new_trade(symbol, direction, current_price, score, df, analysis)
                        daily_trade_count += 1

            time.sleep(BOT_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Bot detenido manualmente")
            send_message("⏹️ <b>Bot detenido manualmente</b>")
            break
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            notify_risk_alert(f"Error inesperado: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run()
