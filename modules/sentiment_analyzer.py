"""
MÓDULO 3: Sentiment Analyzer
Analiza Fear & Greed Index con caché para no llamar la API cada minuto.
Score: -1 (muy negativo) a +1 (muy positivo)
"""
import requests
import logging
from datetime import datetime, timedelta
from config.settings import NEWSAPI_KEY, SENTIMENT_MIN_SOURCES, SENTIMENT_CACHE_MINUTES

logger = logging.getLogger("bot.sentiment")

# ── Caché del Fear & Greed Index ──────────────────────────────────────────────
_fg_cache = {
    "score":      0.0,
    "label":      "Unknown",
    "value":      50,
    "expires_at": datetime.min,
}

CRYPTO_KEYWORDS = {
    "BTCUSDT": ["bitcoin", "BTC", "bitcoin price", "bitcoin market"],
    "ETHUSDT": ["ethereum", "ETH", "ethereum price", "ether"],
}

POSITIVE_WORDS = [
    "surge", "rally", "bullish", "adoption", "breakout", "record", "gain",
    "rise", "soar", "boost", "approval", "institutional", "buy", "support",
    "sube", "alza", "alcista", "récord", "adopción", "aprobación"
]

NEGATIVE_WORDS = [
    "crash", "dump", "bearish", "ban", "hack", "fraud", "sell", "fear",
    "regulation", "lawsuit", "investigation", "collapse", "liquidation",
    "cae", "baja", "bajista", "prohibición", "fraude", "regulación", "colapso"
]


def get_fear_greed_index() -> dict:
    """Obtiene el Fear & Greed Index con caché de 60 minutos."""
    global _fg_cache

    # Devolver caché si todavía es válido
    if datetime.now() < _fg_cache["expires_at"]:
        logger.debug(f"F&G desde caché: {_fg_cache['value']} ({_fg_cache['label']})")
        return _fg_cache

    try:
        resp  = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data  = resp.json()["data"][0]
        value = int(data["value"])
        score = round((value - 50) / 50, 2)

        _fg_cache = {
            "score":      score,
            "label":      data["value_classification"],
            "value":      value,
            "expires_at": datetime.now() + timedelta(minutes=SENTIMENT_CACHE_MINUTES),
        }
        logger.info(f"F&G actualizado: {value} ({data['value_classification']}) → score={score}")
        return _fg_cache

    except Exception as e:
        logger.error(f"Error obteniendo F&G: {e}")
        # Si falla, devolver caché viejo o neutro
        return _fg_cache


def analyze_text_sentiment(text: str) -> float:
    """Análisis simple de sentimiento por palabras clave."""
    text_lower = text.lower()
    pos   = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg   = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


def get_news_sentiment(symbol: str) -> dict:
    """Obtiene noticias recientes y calcula el sentimiento promedio."""
    if not NEWSAPI_KEY or NEWSAPI_KEY == "TU_NEWSAPI_KEY":
        return {"score": 0.0, "articles": 0, "source": "disabled"}

    keywords = CRYPTO_KEYWORDS.get(symbol, [symbol[:3]])
    query    = " OR ".join(keywords)
    since    = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        url    = "https://newsapi.org/v2/everything"
        params = {
            "q":        query,
            "from":     since,
            "sortBy":   "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey":   NEWSAPI_KEY,
        }
        resp     = requests.get(url, params=params, timeout=10)
        articles = resp.json().get("articles", [])

        scores = []
        for a in articles:
            text  = f"{a.get('title', '')} {a.get('description', '')}"
            score = analyze_text_sentiment(text)
            if score != 0:
                scores.append(score)

        if len(scores) < SENTIMENT_MIN_SOURCES:
            return {"score": 0.0, "articles": len(articles), "source": "insufficient"}

        avg_score = round(sum(scores) / len(scores), 2)
        return {"score": avg_score, "articles": len(articles), "source": "newsapi"}

    except Exception as e:
        return {"score": 0.0, "articles": 0, "source": "error", "error": str(e)}


def get_combined_sentiment(symbol: str) -> dict:
    """Combina Fear & Greed + noticias en un score final."""
    fg   = get_fear_greed_index()
    news = get_news_sentiment(symbol)

    if news["source"] == "newsapi":
        combined = round(fg["score"] * 0.5 + news["score"] * 0.5, 2)
    else:
        combined = fg["score"]

    return {
        "sentiment_score": combined,
        "fear_greed":      fg,
        "news":            news,
    }