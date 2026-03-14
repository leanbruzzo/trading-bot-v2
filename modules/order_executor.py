"""
MÓDULO 5: Order Executor
Conecta con Binance Futures API y ejecuta órdenes.
En modo DRY_RUN=True no se ejecutan órdenes reales.
"""
from binance.um_futures import UMFutures
from binance.error import ClientError
from config.settings import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET,
    LEVERAGE, MARGIN_TYPE
)
import logging

logger = logging.getLogger("bot.executor")

# Modo DRY_RUN (observación sin ejecutar órdenes reales)
try:
    from config.settings import DRY_RUN
except ImportError:
    DRY_RUN = False

# Cliente Binance (testnet o real)
if BINANCE_TESTNET:
    client = UMFutures(
        key=BINANCE_API_KEY,
        secret=BINANCE_API_SECRET,
        base_url="https://testnet.binancefuture.com"
    )
else:
    client = UMFutures(key=BINANCE_API_KEY, secret=BINANCE_API_SECRET)


def setup_symbol(symbol: str):
    """Configura apalancamiento y tipo de margen para un símbolo."""
    if DRY_RUN:
        logger.info(f"🔵 [SIMULADO] {symbol} configurado — leverage {LEVERAGE}x, margen {MARGIN_TYPE}")
        return
    try:
        client.change_margin_type(symbol=symbol, marginType=MARGIN_TYPE)
    except ClientError as e:
        if "No need to change margin type" not in str(e):
            logger.warning(f"Margin type: {e}")
    try:
        client.change_leverage(symbol=symbol, leverage=LEVERAGE)
        logger.info(f"✅ {symbol} configurado — leverage {LEVERAGE}x, margen {MARGIN_TYPE}")
    except ClientError as e:
        logger.error(f"Error configurando {symbol}: {e}")


def get_balance() -> float:
    """Retorna el balance disponible en USDT."""
    if DRY_RUN:
        from config.settings import CAPITAL_TOTAL_USDT
        return CAPITAL_TOTAL_USDT
    try:
        account = client.account()
        for asset in account["assets"]:
            if asset["asset"] == "USDT":
                return float(asset["availableBalance"])
        return 0.0
    except Exception as e:
        logger.error(f"Error obteniendo balance: {e}")
        return 0.0


def get_current_price(symbol: str) -> float:
    try:
        ticker = client.ticker_price(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        logger.error(f"Error obteniendo precio {symbol}: {e}")
        return 0.0


def get_klines(symbol: str, interval: str = "15m", limit: int = 100) -> list:
    """Obtiene velas históricas y las devuelve como lista de dicts."""
    try:
        raw = client.klines(symbol=symbol, interval=interval, limit=limit)
        candles = []
        for k in raw:
            candles.append({
                "open":   float(k[1]),
                "high":   float(k[2]),
                "low":    float(k[3]),
                "close":  float(k[4]),
                "volume": float(k[5]),
            })
        return candles
    except Exception as e:
        logger.error(f"Error obteniendo klines {symbol}: {e}")
        return []


def open_long(symbol: str, usdt_amount: float) -> dict | None:
    """Abre posición LONG (BUY) con cantidad en USDT."""
    price = get_current_price(symbol)
    if not price:
        return None
    qty = round(usdt_amount / price, 3)
    if DRY_RUN:
        logger.info(f"🔵 [SIMULADO] 📈 LONG abierto {symbol} — qty {qty} @ ~{price}")
        return {"side": "LONG", "symbol": symbol, "qty": qty, "entry_price": price, "order": {"dry_run": True}}
    try:
        order = client.new_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=qty,
        )
        logger.info(f"📈 LONG abierto {symbol} — qty {qty} @ ~{price}")
        return {"side": "LONG", "symbol": symbol, "qty": qty, "entry_price": price, "order": order}
    except ClientError as e:
        logger.error(f"Error abriendo LONG {symbol}: {e}")
        return None


def open_short(symbol: str, usdt_amount: float) -> dict | None:
    """Abre posición SHORT (SELL) con cantidad en USDT."""
    price = get_current_price(symbol)
    if not price:
        return None
    qty = round(usdt_amount / price, 3)
    if DRY_RUN:
        logger.info(f"🔵 [SIMULADO] 📉 SHORT abierto {symbol} — qty {qty} @ ~{price}")
        return {"side": "SHORT", "symbol": symbol, "qty": qty, "entry_price": price, "order": {"dry_run": True}}
    try:
        order = client.new_order(
            symbol=symbol,
            side="SELL",
            type="MARKET",
            quantity=qty,
        )
        logger.info(f"📉 SHORT abierto {symbol} — qty {qty} @ ~{price}")
        return {"side": "SHORT", "symbol": symbol, "qty": qty, "entry_price": price, "order": order}
    except ClientError as e:
        logger.error(f"Error abriendo SHORT {symbol}: {e}")
        return None


def close_position(symbol: str, side: str, qty: float) -> dict | None:
    """Cierra una posición existente."""
    if DRY_RUN:
        logger.info(f"🔵 [SIMULADO] ✅ Posición cerrada {symbol} {side} — qty {qty}")
        return {"dry_run": True}
    close_side = "SELL" if side == "LONG" else "BUY"
    try:
        order = client.new_order(
            symbol=symbol,
            side=close_side,
            type="MARKET",
            quantity=qty,
            reduceOnly=True,
        )
        logger.info(f"✅ Posición cerrada {symbol} {side} — qty {qty}")
        return order
    except ClientError as e:
        logger.error(f"Error cerrando posición {symbol}: {e}")
        return None


def get_open_positions() -> list:
    """Retorna todas las posiciones abiertas."""
    if DRY_RUN:
        return []
    try:
        positions = client.get_position_risk()
        return [p for p in positions if float(p["positionAmt"]) != 0]
    except Exception as e:
        logger.error(f"Error obteniendo posiciones: {e}")
        return []
