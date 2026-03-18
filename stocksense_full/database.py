# ═══════════════════════════════════════════════════════════
#  StockSense — database.py
#  SQLAlchemy models — User, Holding, PredictionRecord,
#                      Watchlist, Alert
# ═══════════════════════════════════════════════════════════

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import bcrypt
import os

db = SQLAlchemy()

def init_app(app):
    app.config["SQLALCHEMY_DATABASE_URI"]        = os.getenv("DATABASE_URL","sqlite:///stocksense.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

# ── USER ─────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    full_name  = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password_h = db.Column(db.String(200), nullable=False)
    plan       = db.Column(db.String(50),  default="Free Plan")
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    holdings    = db.relationship("Holding",          backref="user", lazy=True, cascade="all,delete")
    predictions = db.relationship("PredictionRecord", backref="user", lazy=True, cascade="all,delete")
    watchlist   = db.relationship("Watchlist",        backref="user", lazy=True, cascade="all,delete")
    alerts      = db.relationship("Alert",            backref="user", lazy=True, cascade="all,delete")

    @staticmethod
    def create(full_name, email, password):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        u      = User(full_name=full_name, email=email, password_h=hashed)
        db.session.add(u)
        db.session.commit()
        return u

    @staticmethod
    def authenticate(email, password):
        u = User.query.filter_by(email=email).first()
        if u and bcrypt.checkpw(password.encode(), u.password_h.encode()):
            return u
        return None


# ── HOLDING ───────────────────────────────────────────────────
class Holding(db.Model):
    __tablename__ = "holdings"
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    symbol    = db.Column(db.String(20),  nullable=False)
    shares    = db.Column(db.Float,       nullable=False, default=0)
    avg_price = db.Column(db.Float,       nullable=False, default=0)
    added_at  = db.Column(db.DateTime,    default=datetime.utcnow)


# ── PREDICTION RECORD ─────────────────────────────────────────
class PredictionRecord(db.Model):
    __tablename__   = "predictions"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ticker          = db.Column(db.String(20))
    predicted_price = db.Column(db.Float)
    actual_price    = db.Column(db.Float,   nullable=True)
    horizon         = db.Column(db.Integer, default=7)
    model           = db.Column(db.String(50))
    confidence      = db.Column(db.Integer, default=70)
    direction       = db.Column(db.String(20), default="bullish")
    hit             = db.Column(db.Boolean,    nullable=True)
    created_at      = db.Column(db.DateTime,   default=datetime.utcnow)

    def time_ago(self):
        delta = datetime.utcnow() - self.created_at
        hours = int(delta.total_seconds() / 3600)
        if hours < 1:  return "just now"
        if hours < 24: return f"{hours}h ago"
        d = hours // 24
        if d == 1:     return "1d ago"
        if d < 7:      return f"{d}d ago"
        return f"{d//7}w ago"

    @staticmethod
    def create(user_id, ticker, predicted_price, horizon, model, confidence, direction="bullish"):
        r = PredictionRecord(
            user_id=user_id, ticker=ticker,
            predicted_price=predicted_price, horizon=horizon,
            model=model, confidence=confidence, direction=direction,
        )
        db.session.add(r)
        db.session.commit()
        return r

    @staticmethod
    def get_active(user_id):
        cutoff = datetime.utcnow() - timedelta(days=30)
        return PredictionRecord.query.filter(
            PredictionRecord.user_id == user_id,
            PredictionRecord.created_at >= cutoff
        ).all()


# ── WATCHLIST ─────────────────────────────────────────────────
class Watchlist(db.Model):
    __tablename__ = "watchlist"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ticker       = db.Column(db.String(20), nullable=False)
    company_name = db.Column(db.String(100), default="")
    added_at     = db.Column(db.DateTime, default=datetime.utcnow)


# ── ALERT ─────────────────────────────────────────────────────
class Alert(db.Model):
    __tablename__  = "alerts"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ticker         = db.Column(db.String(20))
    target_price   = db.Column(db.Float)
    direction      = db.Column(db.String(10), default="above")  # "above" or "below"
    triggered      = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
