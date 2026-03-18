# ═══════════════════════════════════════════════════════════
#  StockSense — app.py
#  Full-stack entry point (Flask / Antigravity compatible)
# ═══════════════════════════════════════════════════════════

from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-stocksense-2024")

# ── Import modules ───────────────────────────────────────────
from database import db, User, Holding, PredictionRecord, Watchlist, Alert
from data.fetcher import fetch_ohlc, fetch_current_price, fetch_history_df
from data.news    import fetch_news
from models.engine import run_prediction

# ── Init DB ──────────────────────────────────────────────────
import database as _db_module
with app.app_context():
    _db_module.init_app(app)
    db.create_all()

# ── Template filters ─────────────────────────────────────────
@app.template_filter('fmt')
def fmt(value):
    try:    return f"{float(value):,.2f}"
    except: return "0.00"

@app.template_filter('fmtint')
def fmtint(value):
    try:    return f"{int(value):,}"
    except: return "0"

# ── Auth helper ──────────────────────────────────────────────
def current_user():
    uid = session.get("user_id")
    if not uid: return None
    u = User.query.get(uid)
    if not u:   return None
    parts = u.full_name.split()
    return {
        "id":         u.id,
        "name":       u.full_name,
        "first_name": parts[0] if parts else "User",
        "initials":   "".join(p[0].upper() for p in parts[:2]),
        "plan":       u.plan or "Free Plan",
    }

def require_login():
    if not session.get("user_id"):
        return redirect("/login")
    return None

def time_greeting():
    h = datetime.now().hour
    if h < 12: return "morning"
    if h < 17: return "afternoon"
    return "evening"

# ════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return redirect("/dashboard") if session.get("user_id") else redirect("/login")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pw    = request.form.get("password","")
        u     = User.authenticate(email, pw)
        if u:
            session["user_id"] = u.id
            return redirect("/dashboard")
        return render_template("auth/login.html", error="Invalid email or password.")
    return render_template("auth/login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name  = request.form.get("full_name","").strip()
        email = request.form.get("email","").strip()
        pw    = request.form.get("password","")
        if not name or not email or not pw:
            return render_template("auth/register.html", error="All fields are required.")
        if User.query.filter_by(email=email).first():
            return render_template("auth/register.html", error="Email already registered.")
        u = User.create(name, email, pw)
        session["user_id"] = u.id
        return redirect("/dashboard")
    return render_template("auth/register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════

@app.route("/dashboard")
def dashboard():
    redir = require_login()
    if redir: return redir
    user   = current_user()
    ticker = request.args.get("ticker","AAPL").upper().strip()

    # Stock data
    ohlc          = fetch_ohlc(ticker, period="7d")
    current_price = fetch_current_price(ticker)
    news          = fetch_news(ticker)

    # Portfolio
    holdings_db  = Holding.query.filter_by(user_id=user["id"]).all()
    holdings_out = []
    total_val = total_cost = 0.0
    for h in holdings_db:
        price   = fetch_current_price(h.symbol)
        val     = price * h.shares
        cost    = h.avg_price * h.shares
        pnl     = round(val - cost, 2)
        pnl_pct = round((pnl / cost * 100) if cost else 0, 2)
        total_val  += val
        total_cost += cost
        holdings_out.append({
            "symbol":    h.symbol,
            "shares":    h.shares,
            "avg_price": round(h.avg_price, 2),
            "pnl":       pnl,
            "pnl_pct":   pnl_pct,
        })

    daily_pnl     = round(total_val * 0.016, 2)
    weekly_change = round(total_val * 0.048, 2)

    portfolio = {
        "total_value":   round(total_val, 2),
        "daily_pnl":     daily_pnl,
        "daily_pnl_pct": round((daily_pnl / total_val * 100) if total_val else 0, 2),
        "weekly_change": weekly_change,
        "holdings":      holdings_out,
    }

    # Prediction history
    hist_db  = PredictionRecord.query.filter_by(user_id=user["id"])\
                 .order_by(PredictionRecord.created_at.desc()).limit(5).all()
    pred_hist = [{
        "ticker":    p.ticker,
        "predicted": round(p.predicted_price, 2),
        "actual":    round(p.actual_price, 2) if p.actual_price else "—",
        "hit":       p.hit,
        "time_ago":  p.time_ago(),
    } for p in hist_db]

    # Active prediction
    pred         = run_prediction(ticker, horizon=7)
    change_pct   = round(((pred["target"] - current_price) / current_price * 100) if current_price else 0, 2)
    active_pred  = {
        "ticker":        ticker,
        "horizon":       7,
        "target":        round(pred["target"], 2),
        "current_price": round(current_price, 2),
        "change_pct":    change_pct,
        "low":           round(pred["lower"], 2),
        "high":          round(pred["upper"], 2),
        "confidence":    pred["confidence"],
        "model":         pred["model"],
        "signals":       pred["signals"],
    }

    # Model stats
    all_preds = PredictionRecord.query.filter_by(user_id=user["id"]).all()
    hits      = sum(1 for p in all_preds if p.hit is True)
    accuracy  = round((hits / len(all_preds) * 100) if all_preds else 87, 1)

    active_list = PredictionRecord.get_active(user["id"])
    pred_summary = {
        "active_count": len(active_list),
        "bullish": sum(1 for p in active_list if p.direction == "bullish"),
        "bearish": sum(1 for p in active_list if p.direction == "bearish"),
    }

    return render_template("dashboard.html",
        active_page       = "dashboard",
        current_user      = user,
        current_date      = datetime.now().strftime("%A, %d %B %Y"),
        time_of_day       = time_greeting(),
        selected_ticker   = ticker,
        ohlc_data         = ohlc,
        news_items        = news,
        portfolio         = portfolio,
        prediction_history= pred_hist,
        active_prediction = active_pred,
        model_stats       = {"accuracy": accuracy, "sample_size": max(len(all_preds), 1), "best_model": "XGBoost"},
        predictions       = pred_summary,
    )

# ════════════════════════════════════════════════════════════
#  PREDICT
# ════════════════════════════════════════════════════════════

@app.route("/predict", methods=["GET","POST"])
def predict():
    redir = require_login()
    if redir: return redir
    user   = current_user()
    result = None

    if request.method == "POST":
        ticker  = request.form.get("ticker","AAPL").upper().strip()
        horizon = int(request.form.get("horizon", 7))
        current = fetch_current_price(ticker)
        pred    = run_prediction(ticker, horizon=horizon)
        result  = {
            "ticker":     ticker,
            "horizon":    horizon,
            "target":     round(pred["target"], 2),
            "current":    round(current, 2),
            "change_pct": round(((pred["target"] - current) / current * 100) if current else 0, 2),
            "low":        round(pred["lower"], 2),
            "high":       round(pred["upper"], 2),
            "confidence": pred["confidence"],
            "model":      pred["model"],
            "signals":    pred["signals"],
        }
        direction = "bullish" if result["change_pct"] >= 0 else "bearish"
        PredictionRecord.create(
            user_id         = user["id"],
            ticker          = ticker,
            predicted_price = result["target"],
            horizon         = horizon,
            model           = result["model"],
            confidence      = result["confidence"],
            direction       = direction,
        )

    return render_template("predict.html",
        active_page  = "predict",
        current_user = user,
        result       = result,
    )

# ════════════════════════════════════════════════════════════
#  HISTORY
# ════════════════════════════════════════════════════════════

@app.route("/history")
def history():
    redir = require_login()
    if redir: return redir
    user   = current_user()
    ticker = request.args.get("ticker", None)

    q = PredictionRecord.query.filter_by(user_id=user["id"])
    if ticker: q = q.filter_by(ticker=ticker.upper())
    records = q.order_by(PredictionRecord.created_at.desc()).all()

    history_out = [{
        "ticker":     r.ticker,
        "predicted":  round(r.predicted_price, 2),
        "actual":     round(r.actual_price, 2) if r.actual_price else "Pending",
        "horizon":    r.horizon,
        "model":      r.model,
        "confidence": r.confidence,
        "hit":        r.hit,
        "direction":  r.direction,
        "date":       r.created_at.strftime("%d %b %Y"),
        "time_ago":   r.time_ago(),
    } for r in records]

    return render_template("history.html",
        active_page    = "history",
        current_user   = user,
        history        = history_out,
        filter_ticker  = ticker,
        total          = len(history_out),
        hits           = sum(1 for h in history_out if h["hit"] is True),
        misses         = sum(1 for h in history_out if h["hit"] is False),
    )

# ════════════════════════════════════════════════════════════
#  WATCHLIST
# ════════════════════════════════════════════════════════════

@app.route("/watchlist")
def watchlist():
    redir = require_login()
    if redir: return redir
    user  = current_user()
    items = Watchlist.query.filter_by(user_id=user["id"]).all()
    watch_out = []
    for item in items:
        price = fetch_current_price(item.ticker)
        watch_out.append({
            "id":     item.id,
            "ticker": item.ticker,
            "name":   item.company_name or item.ticker,
            "price":  round(price, 2),
        })
    return render_template("watchlist.html",
        active_page  = "watchlist",
        current_user = user,
        watchlist    = watch_out,
    )

@app.route("/watchlist/add", methods=["POST"])
def watchlist_add():
    redir = require_login()
    if redir: return redir
    user   = current_user()
    ticker = request.form.get("ticker","").upper().strip()
    if ticker and not Watchlist.query.filter_by(user_id=user["id"], ticker=ticker).first():
        w = Watchlist(user_id=user["id"], ticker=ticker, company_name=ticker)
        db.session.add(w); db.session.commit()
    return redirect("/watchlist")

@app.route("/watchlist/remove/<int:wid>", methods=["POST"])
def watchlist_remove(wid):
    redir = require_login()
    if redir: return redir
    user = current_user()
    item = Watchlist.query.filter_by(id=wid, user_id=user["id"]).first()
    if item:
        db.session.delete(item); db.session.commit()
    return redirect("/watchlist")

# ════════════════════════════════════════════════════════════
#  PORTFOLIO
# ════════════════════════════════════════════════════════════

@app.route("/portfolio")
def portfolio():
    redir = require_login()
    if redir: return redir
    user     = current_user()
    holdings = Holding.query.filter_by(user_id=user["id"]).all()
    out      = []
    total_val = total_cost = 0.0
    for h in holdings:
        price   = fetch_current_price(h.symbol)
        val     = price * h.shares
        cost    = h.avg_price * h.shares
        pnl     = round(val - cost, 2)
        pnl_pct = round((pnl / cost * 100) if cost else 0, 2)
        total_val  += val
        total_cost += cost
        out.append({
            "id": h.id, "symbol": h.symbol,
            "shares": h.shares, "avg_price": round(h.avg_price,2),
            "current_price": round(price,2), "value": round(val,2),
            "pnl": pnl, "pnl_pct": pnl_pct,
        })
    return render_template("portfolio.html",
        active_page   = "portfolio",
        current_user  = user,
        holdings      = out,
        total_value   = round(total_val,2),
        total_pnl     = round(total_val - total_cost, 2),
        total_pnl_pct = round(((total_val - total_cost)/total_cost*100) if total_cost else 0, 2),
    )

@app.route("/portfolio/add", methods=["POST"])
def portfolio_add():
    redir = require_login()
    if redir: return redir
    user      = current_user()
    symbol    = request.form.get("symbol","").upper().strip()
    shares    = float(request.form.get("shares", 0))
    avg_price = float(request.form.get("avg_price", 0))
    if symbol and shares > 0 and avg_price > 0:
        existing = Holding.query.filter_by(user_id=user["id"], symbol=symbol).first()
        if existing:
            total_shares = existing.shares + shares
            existing.avg_price = (existing.avg_price * existing.shares + avg_price * shares) / total_shares
            existing.shares = total_shares
        else:
            db.session.add(Holding(user_id=user["id"], symbol=symbol, shares=shares, avg_price=avg_price))
        db.session.commit()
    return redirect("/portfolio")

@app.route("/portfolio/remove/<int:hid>", methods=["POST"])
def portfolio_remove(hid):
    redir = require_login()
    if redir: return redir
    user = current_user()
    h    = Holding.query.filter_by(id=hid, user_id=user["id"]).first()
    if h:
        db.session.delete(h); db.session.commit()
    return redirect("/portfolio")

# ════════════════════════════════════════════════════════════
#  ALERTS
# ════════════════════════════════════════════════════════════

@app.route("/alerts")
def alerts():
    redir = require_login()
    if redir: return redir
    user   = current_user()
    alerts = Alert.query.filter_by(user_id=user["id"]).all()
    return render_template("alerts.html",
        active_page  = "alerts",
        current_user = user,
        alerts       = alerts,
    )

@app.route("/alerts/add", methods=["POST"])
def alerts_add():
    redir = require_login()
    if redir: return redir
    user      = current_user()
    ticker    = request.form.get("ticker","").upper().strip()
    target    = float(request.form.get("target_price", 0))
    direction = request.form.get("direction","above")
    if ticker and target > 0:
        db.session.add(Alert(user_id=user["id"], ticker=ticker,
                             target_price=target, direction=direction))
        db.session.commit()
    return redirect("/alerts")

@app.route("/alerts/remove/<int:aid>", methods=["POST"])
def alerts_remove(aid):
    redir = require_login()
    if redir: return redir
    user = current_user()
    a    = Alert.query.filter_by(id=aid, user_id=user["id"]).first()
    if a:
        db.session.delete(a); db.session.commit()
    return redirect("/alerts")

# ════════════════════════════════════════════════════════════
#  ACCOUNT
# ════════════════════════════════════════════════════════════

@app.route("/account", methods=["GET","POST"])
def account():
    redir = require_login()
    if redir: return redir
    user    = current_user()
    u_obj   = User.query.get(user["id"])
    message = None
    if request.method == "POST":
        u_obj.full_name = request.form.get("full_name", u_obj.full_name).strip()
        db.session.commit()
        message = "Account updated successfully."
        user = current_user()
    return render_template("account.html",
        active_page  = "account",
        current_user = user,
        user_obj     = u_obj,
        message      = message,
    )

# ════════════════════════════════════════════════════════════
#  JSON API (for live chart refresh)
# ════════════════════════════════════════════════════════════

@app.route("/api/price/<ticker>")
def api_price(ticker):
    if not session.get("user_id"):
        return jsonify({"error": "unauthorized"}), 401
    price = fetch_current_price(ticker.upper())
    return jsonify({"ticker": ticker.upper(), "price": price})

@app.route("/api/ohlc/<ticker>")
def api_ohlc(ticker):
    if not session.get("user_id"):
        return jsonify({"error": "unauthorized"}), 401
    data = fetch_ohlc(ticker.upper(), period="7d")
    return jsonify(data)

@app.route("/api/predict/<ticker>")
def api_predict(ticker):
    if not session.get("user_id"):
        return jsonify({"error": "unauthorized"}), 401
    horizon = int(request.args.get("horizon", 7))
    pred    = run_prediction(ticker.upper(), horizon=horizon)
    return jsonify(pred)

# ════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
