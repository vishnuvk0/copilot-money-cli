# Copilot Money Portfolio Tracker

A local portfolio analytics dashboard that syncs data from [Copilot Money](https://copilot.money) and provides performance metrics, allocation breakdowns, trade detection, and benchmark comparisons.

## Architecture

```
api/          FastAPI backend (Python) — syncs from Copilot, stores in SQLite, serves REST API
frontend/     React + Vite dashboard — charts, holdings, performance metrics
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- A Copilot Money account

### 1. Get your Copilot token

1. Log into [app.copilot.money](https://app.copilot.money) in your browser
2. Open DevTools > Application > Cookies or Network tab
3. Copy the Firebase auth token (starts with `eyJhbG...`)
4. Create a `.env` file in the project root:

```
COPILOT_TOKEN=Bearer eyJhbG...your_token_here
```

> Tokens expire after ~1 hour. Refresh from the Copilot web app when needed.

### 2. Install dependencies

```bash
make install
```

Or manually:

```bash
# API
python3 -m venv api/venv
api/venv/bin/pip install -r api/requirements.txt

# Frontend
cd frontend && npm install
```

### 3. Run

```bash
make dev
```

This starts both servers concurrently:
- API: http://localhost:8000
- Frontend: http://localhost:3000

On startup, the API syncs all data from Copilot Money and stores it in a local SQLite database (`api/data/investments.db`). Subsequent syncs are incremental.

## CLI

Query your portfolio from the terminal:

```bash
# Overview
make cli ARGS="accounts"
make cli ARGS="periods"

# What do I hold?
make cli ARGS="allocation"

# Performance
make cli ARGS="performance --period YTD"

# Am I beating S&P 500?
make cli ARGS="comparison --period 1Y"

# Recent trades
make cli ARGS="trades --period 3M"

# Trigger a data sync
make cli ARGS="sync"

# Raw JSON output
make cli ARGS="--json holdings"
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/investments/accounts` | All investment accounts |
| `GET /api/investments/holdings` | Current positions |
| `GET /api/investments/allocation/{date}` | Holdings breakdown for a date |
| `GET /api/investments/balance-history?period=1Y` | Daily portfolio balance |
| `GET /api/investments/trades?period=ALL` | Detected buys/sells |
| `GET /api/returns/performance?period=1Y` | TWR, Sharpe, volatility, beta, drawdown |
| `GET /api/returns/comparison?period=1Y` | Portfolio vs S&P 500 |
| `GET /api/returns/periods` | All period metrics at once |
| `POST /api/investments/sync` | Trigger data sync |

Periods: `1D`, `1W`, `1M`, `3M`, `6M`, `YTD`, `1Y`, `ALL`
