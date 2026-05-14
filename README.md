# StockSense — AI Stock Price Prediction

Full-stack web app built with Flask + SQLAlchemy + XGBoost + Prophet.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum

# 3. Run the app
python app.py
```

Open http://localhost:5000 — register an account and start predicting!

## Project Structure

```
stocksense/
├── app.py              ← All routes (Flask entry point)
├── database.py         ← SQLAlchemy models
├── requirements.txt
├── .env.example
├── data/
│   ├── fetcher.py      ← yfinance stock data
│   └── news.py         ← NewsAPI headlines
├── models/
│   └── engine.py       ← XGBoost + Prophet prediction
├── static/
│   ├── css/
│   │   ├── styles.css  ← Main styles
│   │   ├── extra.css   ← Page-specific styles
│   │   └── auth.css    ← Login/register styles
│   └── js/
│       └── charts.js   ← Candlestick + Chart.js
└── templates/
    ├── base.html        ← Sidebar layout (all pages extend this)
    ├── dashboard.html
    ├── predict.html
    ├── history.html
    ├── watchlist.html
    ├── portfolio.html
    ├── alerts.html
    ├── account.html
    └── auth/
        ├── login.html
        └── register.html
```

## Pages

| URL            | Description                        |
|----------------|------------------------------------|
| /login         | Login page                         |
| /register      | Create account                     |
| /dashboard     | Main dashboard with charts         |
| /predict       | Run a new AI prediction            |
| /history       | View all past predictions          |
| /watchlist     | Add/remove tracked stocks          |
| /portfolio     | Holdings + P&L tracker             |
| /alerts        | Set price alert rules              |
| /account       | Edit profile                       |

## API Endpoints (JSON)

| Endpoint                  | Returns                  |
|---------------------------|--------------------------|
| /api/price/<ticker>       | Current price            |
| /api/ohlc/<ticker>        | 7-day OHLC data          |
| /api/predict/<ticker>     | ML prediction result     |

## Production Deployment

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Set DATABASE_URL to a PostgreSQL URL in .env for production.

## Notes
- Predictions are for educational purposes only — not financial advice.
- Get a free NewsAPI key at https://newsapi.org
