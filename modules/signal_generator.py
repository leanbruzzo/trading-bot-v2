"""
MÓDULO 2: Signal Generator
Genera señales técnicas combinando MA crossover, RSI y Momentum.
Retorna un score entre -1 (bajista fuerte) y +1 (alcista fuerte).
v2.0: RSI coherente con dirección de señal
"""
import pandas as pd
import numpy as np
from config.settings import MA_SHORT, MA_LONG, RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_signals(df: pd.DataFrame) -> dict:
    close = df["close"]

    # --- Moving Averages ---
    ma_short = close.rolling(MA_SHORT).mean()
    ma_long  = close.rolling(MA_LONG).mean()

    ma_prev_short = ma_short.iloc[-2]
    ma_prev_long  = ma_long.iloc[-2]
    ma_curr_short = ma_short.iloc[-1]
    ma_curr_long  = ma_long.iloc[-1]

    if ma_prev_short <= ma_prev_long and ma_curr_short > ma_curr_long:
        ma_signal = 1.0
    elif ma_prev_short >= ma_prev_long and ma_curr_short < ma_curr_long:
        ma_signal = -1.0
    elif ma_curr_short > ma_curr_long:
        ma_signal = 0.5
    else:
        ma_signal = -0.5

    # --- RSI ---
    rsi = calculate_rsi(close, RSI_PERIOD).iloc[-1]

    if rsi < RSI_OVERSOLD:
        rsi_signal = 1.0
    elif rsi > RSI_OVERBOUGHT:
        rsi_signal = -1.0
    elif rsi < 45:
        rsi_signal = 0.3
    elif rsi > 55:
        rsi_signal = -0.3
    else:
        rsi_signal = 0.0

    # --- Momentum (rate of change 10 períodos) ---
    roc = ((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]) * 100

    if roc > 3:
        mom_signal = 1.0
    elif roc > 1:
        mom_signal = 0.5
    elif roc < -3:
        mom_signal = -1.0
    elif roc < -1:
        mom_signal = -0.5
    else:
        mom_signal = 0.0

    # --- Volumen como confirmador ---
    vol_avg = df["volume"].rolling(20).mean().iloc[-1]
    vol_now = df["volume"].iloc[-1]
    volume_confirm = bool(vol_now > vol_avg * 1.2)

    # --- Score técnico combinado ---
    raw_score = (ma_signal * 0.4) + (rsi_signal * 0.35) + (mom_signal * 0.25)
    final_score = raw_score if volume_confirm else raw_score * 0.5

    # --- Coherencia RSI con dirección de señal (v2.0) ---
    # Si la señal apunta SHORT pero el RSI no está sobrecomprado → penalizar
    # Si la señal apunta LONG pero el RSI no está sobrevendido → penalizar
    rsi_coherence_penalty = 1.0

    if final_score < 0:  # señal SHORT
        if rsi < 65:
            # RSI bajo en señal SHORT = incoherencia fuerte → anular señal
            rsi_coherence_penalty = 0.0
        elif rsi > 80:
            # RSI extremadamente sobrecomprado = momentum alcista fuerte
            # puede seguir subiendo antes de revertir → penalizar
            rsi_coherence_penalty = 0.5

    elif final_score > 0:  # señal LONG
        if rsi > 35:
            # RSI alto en señal LONG = incoherencia → anular señal
            rsi_coherence_penalty = 0.0
        elif rsi < 20:
            # RSI extremadamente sobrevendido = momentum bajista fuerte
            # puede seguir bajando antes de rebotar → penalizar
            rsi_coherence_penalty = 0.5

    final_score = final_score * rsi_coherence_penalty

    return {
        "technical_score":      round(final_score, 3),
        "ma_signal":            round(ma_signal, 2),
        "rsi":                  round(rsi, 2),
        "rsi_signal":           round(rsi_signal, 2),
        "momentum":             round(roc, 2),
        "mom_signal":           round(mom_signal, 2),
        "volume_confirm":       volume_confirm,
        "ma_short":             round(ma_curr_short, 4),
        "ma_long":              round(ma_curr_long, 4),
        "rsi_coherence_penalty": rsi_coherence_penalty,
    }
