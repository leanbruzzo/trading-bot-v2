"""
MÓDULO 1: Market Regime Detector
Detecta si el mercado está en tendencia, lateral o volátil.
"""
import pandas as pd
import numpy as np


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < (-low.diff()).clip(lower=0)]  = 0
    minus_dm[minus_dm < high.diff().clip(lower=0)] = 0

    atr       = tr.ewm(span=period, adjust=False).mean()
    plus_di   = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
    minus_di  = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr
    dx        = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).fillna(0)
    adx       = dx.ewm(span=period, adjust=False).mean()
    return adx


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def detect_regime(df: pd.DataFrame, adx_trend: float = 25, adx_flat: float = 20) -> dict:
    """
    Retorna el régimen de mercado actual:
      - TRENDING_UP   → tendencia alcista fuerte
      - TRENDING_DOWN → tendencia bajista fuerte
      - RANGING       → mercado lateral
      - VOLATILE      → alta volatilidad sin dirección clara
    """
    adx    = calculate_adx(df).iloc[-1]
    atr    = calculate_atr(df).iloc[-1]
    close  = df["close"].iloc[-1]
    atr_pct = atr / close  # volatilidad como % del precio

    ma20 = df["close"].rolling(20).mean().iloc[-1]
    ma50 = df["close"].rolling(50).mean().iloc[-1]

    if atr_pct > 0.04:                          # volatilidad > 4%
        regime = "VOLATILE"
    elif adx > adx_trend:
        regime = "TRENDING_UP" if ma20 > ma50 else "TRENDING_DOWN"
    elif adx < adx_flat:
        regime = "RANGING"
    else:
        regime = "RANGING"

    return {
        "regime":  regime,
        "adx":     round(adx, 2),
        "atr_pct": round(atr_pct * 100, 2),
        "ma20":    round(ma20, 4),
        "ma50":    round(ma50, 4),
    }
