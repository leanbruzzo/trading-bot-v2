# 🤖 Trading Bot — BTC/ETH Futuros Binance

Bot de trading algorítmico adaptativo con análisis técnico + sentiment de noticias.

---

## 📁 Estructura del proyecto

```
trading-bot/
├── main.py                      ← Punto de entrada principal
├── requirements.txt
├── config/
│   └── settings.py              ← ⚙️ CONFIGURACIÓN (editá esto primero)
├── modules/
│   ├── regime_detector.py       ← Detecta régimen de mercado
│   ├── signal_generator.py      ← Señales técnicas (MA, RSI, Momentum)
│   ├── sentiment_analyzer.py    ← Noticias + Fear & Greed Index
│   ├── risk_manager.py          ← Stop-loss, tamaño de posición
│   ├── order_executor.py        ← Conexión con Binance API
│   └── notifier.py              ← Alertas por Telegram
└── logs/
    ├── bot.log                  ← Log de actividad
    └── risk_state.json          ← Estado de riesgo persistente
```

---

## 🚀 Instalación paso a paso

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Binance Testnet (paper trading)
1. Ir a https://testnet.binancefuture.com
2. Crear cuenta de testnet
3. Generar API Key y Secret
4. Pegar en `config/settings.py`:
   ```python
   BINANCE_API_KEY    = "tu_api_key"
   BINANCE_API_SECRET = "tu_api_secret"
   BINANCE_TESTNET    = True   # ← Dejar en True para empezar
   ```

### 3. Configurar Telegram
1. Abrir Telegram y buscar `@BotFather`
2. Escribir `/newbot` y seguir instrucciones
3. Copiar el token que te da BotFather
4. Buscar `@userinfobot` en Telegram para obtener tu Chat ID
5. Pegar en `config/settings.py`:
   ```python
   TELEGRAM_BOT_TOKEN = "123456:ABC-DEF..."
   TELEGRAM_CHAT_ID   = "987654321"
   ```

### 4. (Opcional) Configurar NewsAPI
1. Registrarse gratis en https://newsapi.org
2. Copiar la API key
3. Pegar en `config/settings.py`:
   ```python
   NEWSAPI_KEY = "tu_newsapi_key"
   ```
   Si no configurás esto, el bot usa solo el Fear & Greed Index.

### 5. Correr el bot
```bash
python main.py
```

---

## 🧠 Lógica de decisión

```
Cada 60 segundos, por cada activo:

1. Detecta régimen de mercado (ADX, ATR)
      → TRENDING_UP / TRENDING_DOWN / RANGING / VOLATILE

2. Calcula señales técnicas (MA crossover, RSI, Momentum, Volumen)
      → Score entre -1 y +1

3. Analiza sentiment (noticias + Fear & Greed)
      → Score entre -1 y +1

4. Combina todo con pesos:
      40% técnico + 30% régimen + 30% sentiment

5. Si score >= 0.35 → LONG
   Si score <= -0.35 → SHORT
   Si entre ambos  → FLAT (no opera)

6. Risk Manager valida antes de ejecutar:
      ✅ Stop-loss por trade: 2%
      ✅ Stop-loss diario: 4%
      ✅ Stop-loss mensual: 8%
      ✅ Flash crash: cierre de emergencia
```

---

## 🛡️ Gestión de riesgo

| Límite | Valor | Consecuencia |
|--------|-------|--------------|
| Stop-loss por trade | 2% | Cierre automático |
| Pérdida diaria | 4% | Pausa 24hs |
| Pérdida semanal | 6% | Pausa hasta revisión |
| Pérdida mensual | 8% | Bot apagado + alerta |
| Flash crash | >10% en 15min | Cierre de emergencia |

---

## ⚠️ Advertencias importantes

- **Empezá siempre en TESTNET** (`BINANCE_TESTNET = True`)
- Nunca des permisos de **retiro** a las API keys, solo trading
- El bot no garantiza ganancias — el trading conlleva riesgo de pérdida
- Monitoreá los logs regularmente aunque el bot sea automático
- Antes de pasar a real, corré el testnet al menos 2-4 semanas

---

## 🔄 Pasar a dinero real

Cuando estés listo:
1. Crear API keys en Binance real (sin permiso de retiro)
2. Actualizar `config/settings.py`:
   ```python
   BINANCE_TESTNET = False
   CAPITAL_TOTAL_USDT = 100   # Tu capital real
   ```
3. Para correr 24/7, deployar en Railway.app o DigitalOcean (~$5-6/mes)
