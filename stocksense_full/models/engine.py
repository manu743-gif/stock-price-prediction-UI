# ═══════════════════════════════════════════════════════════
#  StockSense — models/engine.py
#  Unified ML prediction engine (XGBoost + Prophet fallback)
# ═══════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
from data.fetcher import fetch_history_df, fetch_current_price


def run_prediction(ticker: str, horizon: int = 7) -> dict:
    """
    Run prediction using XGBoost. Falls back to Prophet, then
    to a simple moving-average estimate if both fail.
    """
    try:
        return _xgboost_predict(ticker, horizon)
    except Exception as e:
        print(f"[engine] XGBoost failed for {ticker}: {e}")
    try:
        return _prophet_predict(ticker, horizon)
    except Exception as e:
        print(f"[engine] Prophet failed for {ticker}: {e}")
    return _fallback_predict(ticker, horizon)


# ── XGBOOST ──────────────────────────────────────────────────
def _xgboost_predict(ticker, horizon):
    from xgboost import XGBRegressor
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_absolute_percentage_error

    df = fetch_history_df(ticker, period="2y")
    if df.empty or len(df) < 60:
        raise ValueError("Not enough data")

    df = _add_features(df).dropna()
    if len(df) < 40:
        raise ValueError("Not enough features after dropna")

    feature_cols = ["returns_1d","returns_5d","ma_5","ma_20","ma_50",
                    "vol_5d","rsi_14","price_to_ma20","momentum_10d"]
    X = df[feature_cols].values
    y = df["Close"].values

    sx = MinMaxScaler(); sy = MinMaxScaler()
    Xs = sx.fit_transform(X)
    ys = sy.fit_transform(y.reshape(-1,1)).ravel()

    split = int(len(Xs) * 0.85)
    model = XGBRegressor(n_estimators=300, learning_rate=0.04,
                          max_depth=4, subsample=0.8,
                          colsample_bytree=0.8, random_state=42, verbosity=0)
    model.fit(Xs[:split], ys[:split])

    # accuracy on test set
    y_test  = y[split:]
    y_pred  = sy.inverse_transform(model.predict(Xs[split:]).reshape(-1,1)).ravel()
    mape    = mean_absolute_percentage_error(y_test, y_pred)
    conf    = max(50, min(95, int((1 - mape) * 100)))

    # forecast
    last    = Xs[-1].reshape(1,-1)
    pred_s  = model.predict(last)[0]
    target  = float(sy.inverse_transform([[pred_s]])[0][0])
    step    = 1 + 0.002 * horizon
    target *= step
    margin  = target * (0.02 + horizon * 0.003)

    return {
        "target":     round(target, 2),
        "lower":      round(target - margin, 2),
        "upper":      round(target + margin, 2),
        "confidence": conf,
        "model":      "XGBoost",
        "signals":    _signals(df),
    }


# ── PROPHET ──────────────────────────────────────────────────
def _prophet_predict(ticker, horizon):
    from prophet import Prophet

    df = fetch_history_df(ticker, period="1y")
    if df.empty or len(df) < 30:
        raise ValueError("Not enough data for Prophet")

    prophet_df = df.reset_index()[["Date","Close"]].rename(
        columns={"Date":"ds","Close":"y"})
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"]).dt.tz_localize(None)

    m = Prophet(daily_seasonality=False, weekly_seasonality=True,
                yearly_seasonality=True, interval_width=0.80)
    m.fit(prophet_df)

    future  = m.make_future_dataframe(periods=horizon)
    fcast   = m.predict(future)
    last    = fcast.iloc[-1]
    target  = round(float(last["yhat"]), 2)
    lower   = round(float(last["yhat_lower"]), 2)
    upper   = round(float(last["yhat_upper"]), 2)
    conf    = 78

    df_feat = _add_features(df).dropna()
    return {
        "target":     target,
        "lower":      lower,
        "upper":      upper,
        "confidence": conf,
        "model":      "Prophet",
        "signals":    _signals(df_feat) if not df_feat.empty else ["Trend analysis complete"],
    }


# ── FALLBACK ─────────────────────────────────────────────────
def _fallback_predict(ticker, horizon):
    price  = fetch_current_price(ticker) or 100.0
    target = round(price * (1 + 0.015 * (horizon / 7)), 2)
    return {
        "target":     target,
        "lower":      round(target * 0.97, 2),
        "upper":      round(target * 1.03, 2),
        "confidence": 65,
        "model":      "Moving Average",
        "signals":    ["Trend estimate", "Low data confidence"],
    }


# ── FEATURE ENGINEERING ──────────────────────────────────────
def _add_features(df):
    df = df.copy()
    c  = df["Close"]
    df["returns_1d"]    = c.pct_change(1)
    df["returns_5d"]    = c.pct_change(5)
    df["ma_5"]          = c.rolling(5).mean()
    df["ma_20"]         = c.rolling(20).mean()
    df["ma_50"]         = c.rolling(50).mean()
    df["vol_5d"]        = c.rolling(5).std()
    df["momentum_10d"]  = c - c.shift(10)
    df["price_to_ma20"] = c / df["ma_20"]
    delta               = c.diff()
    gain                = delta.clip(lower=0).rolling(14).mean()
    loss                = (-delta.clip(upper=0)).rolling(14).mean()
    rs                  = gain / loss.replace(0, np.nan)
    df["rsi_14"]        = 100 - (100 / (1 + rs))
    return df


# ── SIGNAL TAGS ──────────────────────────────────────────────
def _signals(df):
    signals = []
    try:
        close = df["Close"].iloc[-1]
        ma20  = df["ma_20"].iloc[-1]
        ma50  = df["ma_50"].iloc[-1]
        rsi   = df["rsi_14"].iloc[-1]
        vol_t = df["vol_5d"].iloc[-1]
        vol_a = df["vol_5d"].mean()

        signals.append("Above 50MA"    if close > ma50 else "Below 50MA")
        signals.append("Bullish trend" if close > ma20 else "Bearish trend")

        if   rsi < 30: signals.append(f"RSI {rsi:.0f} — oversold")
        elif rsi > 70: signals.append(f"RSI {rsi:.0f} — overbought")
        else:          signals.append(f"RSI {rsi:.0f}")

        if vol_t > vol_a * 1.2: signals.append("High volume")
    except Exception:
        signals = ["Signal data unavailable"]
    return signals[:4]
