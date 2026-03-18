# ═══════════════════════════════════════════════════════════
#  StockSense — data/news.py
# ═══════════════════════════════════════════════════════════

import requests, os
from datetime import datetime, timedelta

NEWS_API_KEY = os.getenv("NEWS_API_KEY","")
NEWS_URL     = "https://newsapi.org/v2/everything"


def fetch_news(ticker: str, max_items: int = 5) -> list:
    if not NEWS_API_KEY:
        return _sample_news(ticker)
    try:
        from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        r = requests.get(NEWS_URL, params={
            "q": ticker, "from": from_date, "sortBy": "publishedAt",
            "pageSize": max_items, "apiKey": NEWS_API_KEY, "language": "en",
        }, timeout=5)
        data = r.json()
        if data.get("status") != "ok": return _sample_news(ticker)
        return [{
            "headline": a.get("title",""),
            "source":   a.get("source",{}).get("name",""),
            "time_ago": _time_ago(a.get("publishedAt","")),
            "sentiment":_sentiment(a.get("title","")),
        } for a in data.get("articles",[])[:max_items]]
    except Exception:
        return _sample_news(ticker)


def _sentiment(headline):
    h = headline.lower()
    if any(w in h for w in ["fed","rate","inflation","gdp","yield","fomc"]): return "macro"
    if any(w in h for w in ["beat","record","surge","rally","profit","gain"]): return "positive"
    if any(w in h for w in ["miss","drop","fall","loss","concern","risk"]): return "negative"
    return "neutral"


def _time_ago(iso):
    try:
        pub   = datetime.fromisoformat(iso.replace("Z","+00:00")).replace(tzinfo=None)
        hours = int((datetime.utcnow() - pub).total_seconds() / 3600)
        if hours < 1:  return "just now"
        if hours < 24: return f"{hours}h ago"
        d = hours // 24
        return f"{d}d ago" if d < 7 else f"{d//7}w ago"
    except: return "recently"


def _sample_news(ticker):
    return [
        {"headline": f"{ticker} beats Q1 earnings, services revenue hits record",
         "source":"Reuters",  "time_ago":"2h ago",  "sentiment":"positive"},
        {"headline": f"Analysts raise {ticker} price target on AI opportunity",
         "source":"Bloomberg","time_ago":"5h ago",  "sentiment":"positive"},
        {"headline": "Fed holds rates steady — tech stocks rally on lower yield bets",
         "source":"CNBC",     "time_ago":"8h ago",  "sentiment":"macro"},
        {"headline": f"{ticker} supply chain pressures ease heading into Q2",
         "source":"WSJ",      "time_ago":"1d ago",  "sentiment":"neutral"},
        {"headline": "Global market volatility rises amid macro uncertainty",
         "source":"FT",       "time_ago":"1d ago",  "sentiment":"negative"},
    ]
