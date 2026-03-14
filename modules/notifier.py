"""
MÓDULO 6: Telegram Notifier
Envía alertas y notificaciones al usuario via Telegram Bot API.
"""
import requests
import logging
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("bot.telegram")

try:
    from config.settings import DRY_RUN
except ImportError:
    DRY_RUN = False

DRY_LABEL = "🔵 <b>[SIMULADO]</b> " if DRY_RUN else ""


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TU_TELEGRAM_BOT_TOKEN":
        logger.warning("Telegram no configurado — mensaje no enviado")
        return False
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": parse_mode}
        resp = requests.post(url, data=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Error enviando mensaje Telegram: {e}")
        return False


def notify_trade_open(symbol: str, side: str, entry: float, stop: float, tp: float, size: float):
    emoji = "📈" if side == "LONG" else "📉"
    msg = (
        f"{DRY_LABEL}{emoji} <b>TRADE ABIERTO</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Par:        <b>{symbol}</b>\n"
        f"Dirección:  <b>{side}</b>\n"
        f"Entrada:    <b>${entry:,.2f}</b>\n"
        f"Stop-Loss:  <b>${stop:,.2f}</b>\n"
        f"Take-Profit:<b>${tp:,.2f}</b>\n"
        f"Tamaño:     <b>${size:.2f} USDT</b>"
    )
    send_message(msg)


def notify_trade_close(symbol: str, side: str, entry: float, exit_price: float,
                       pnl: float, reason: str):
    emoji = "✅" if pnl >= 0 else "❌"
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    msg = (
        f"{DRY_LABEL}{emoji} <b>TRADE CERRADO</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Par:        <b>{symbol}</b>\n"
        f"Dirección:  <b>{side}</b>\n"
        f"Entrada:    <b>${entry:,.2f}</b>\n"
        f"Salida:     <b>${exit_price:,.2f}</b>\n"
        f"P&L:        {pnl_emoji} <b>${pnl:+.2f} USDT</b>\n"
        f"Motivo:     <i>{reason}</i>"
    )
    send_message(msg)


def notify_risk_alert(message: str):
    msg = f"⚠️ <b>ALERTA DE RIESGO</b>\n━━━━━━━━━━━━━━━\n{message}"
    send_message(msg)


def notify_bot_stopped(reason: str):
    msg = (
        f"🛑 <b>BOT DETENIDO</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{reason}\n\n"
        f"<i>Revisá el portfolio manualmente antes de reiniciar.</i>"
    )
    send_message(msg)


def notify_flash_crash(symbol: str, price: float, drop_pct: float):
    msg = (
        f"🚨 <b>FLASH CRASH DETECTADO</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Par:    <b>{symbol}</b>\n"
        f"Precio: <b>${price:,.2f}</b>\n"
        f"Caída:  <b>{drop_pct:.1f}% en 15 min</b>\n\n"
        f"<i>Cerrando posiciones de emergencia...</i>"
    )
    send_message(msg)


def notify_daily_summary(trades: int, pnl: float, open_pos: int):
    emoji = "🟢" if pnl >= 0 else "🔴"
    msg = (
        f"📊 <b>RESUMEN DIARIO</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Trades hoy:       <b>{trades}</b>\n"
        f"P&L del día:      {emoji} <b>${pnl:+.2f} USDT</b>\n"
        f"Posiciones abiertas: <b>{open_pos}</b>"
    )
    send_message(msg)
