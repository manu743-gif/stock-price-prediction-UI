# ═══════════════════════════════════════════════════════════
#  StockSense — data/fetcher.py
# ═══════════════════════════════════════════════════════════

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def fetch_ohlc(ticker: str, period: str = "7d") -> list:
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        if df.empty: return _sample_ohlc()
        return [{
            "open":  round(float(r["Open"]),  2),
            "high":  round(float(r["High"]),  2),
            "low":   round(float(r["Low"]),   2),
            "close": round(float(r["Close"]), 2),
            "date":  d.strftime("%Y-%m-%d"),
        } for d, r in df.iterrows()]
    except Exception as e:
        print(f"[fetcher] OHLC error {ticker}: {e}")
        return _sample_ohlc()


def fetch_current_price(ticker: str) -> float:
    try:
        info = yf.Ticker(ticker).fast_info
        return round(float(info.last_price), 2)
    except Exception:
        return 0.0


def fetch_history_df(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d")
        df.index = pd.to_datetime(df.index)
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def _sample_ohlc() -> list:
    base  = 180.0
    today = datetime.today()
    out   = []
    for i in range(7):
        d  = today - timedelta(days=6 - i)
        o  = round(base + i * 1.2, 2)
        c  = round(o + (1.5 if i % 2 == 0 else -0.8), 2)
        out.append({"open": o, "high": round(max(o,c)+1.5,2),
                    "low": round(min(o,c)-1.2,2), "close": c,
                    "date": d.strftime("%Y-%m-%d")})
    return out
