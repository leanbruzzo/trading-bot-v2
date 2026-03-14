"""
MÓDULO 3: Sentiment Analyzer
Analiza noticias y Fear & Greed Index para obtener un score de sentimiento.
Score: -1 (muy negativo) a +1 (muy positivo)
"""
import requests
import time
from datetime import datetime, timedelta
from config.settings import NEWSAPI_KEY, SENTIMENT_MIN_SOURCES


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
    """Obtiene el Fear & Greed Index de cripto (API pública, sin key)."""
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data = resp.json()["data"][0]
        value = int(data["value"])
        # Normalizar a -1 / +1
        score = (value - 50) / 50   # 0=neutral, 100=+1, 0=-1
        return {"score": round(score, 2), "label": data["value_classification"], "value": value}
    except Exception as e:
        return {"score": 0.0, "label": "Unknown", "value": 50, "error": str(e)}


def analyze_text_sentiment(text: str) -> float:
    """Análisis simple de sentimiento por palabras clave."""
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
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
        url = "https://newsapi.org/v2/everything"
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

    # Si las noticias están disponibles, peso 50/50. Si no, solo Fear & Greed.
    if news["source"] in ("newsapi",):
        combined = round(fg["score"] * 0.5 + news["score"] * 0.5, 2)
    else:
        combined = fg["score"]

    return {
        "sentiment_score": combined,
        "fear_greed":      fg,
        "news":            news,
    }
