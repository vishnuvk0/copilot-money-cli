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

### 1. Authenticate with onboarding CLI

Use the built-in onboarding flow instead of manually copying bearer tokens.

1. Set your App Check token once (from Copilot web auth requests):

```
COPILOT_APP_CHECK_TOKEN=eyJ...app_check_token...
```

2. Start email-link login:

```bash
cd api
venv/bin/python cli.py auth start --email you@example.com
```

3. Paste the magic link from your email:

```bash
venv/bin/python cli.py auth complete --email you@example.com --magic-link "https://auth.copilot.money/__/auth/action?..."
```

This stores `COPILOT_TOKEN` and `COPILOT_REFRESH_TOKEN` in local `.env` and triggers an initial sync.

> Tokens rotate automatically via refresh token during API calls.  
> If refresh fails (revoked/expired), re-run the `auth start` / `auth complete` flow.

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

# Onboard / auth flow
make cli ARGS="auth status"
make cli ARGS="auth start --email you@example.com"
make cli ARGS="auth complete --email you@example.com --magic-link \"https://auth.copilot.money/__/auth/action?...\""

# Raw JSON output
make cli ARGS="--json holdings"
```

## Multi-user + Cloud Notes

- This flow works for any Copilot account, but each user must authenticate their own email and keep their own local `.env`.
- Do not commit `.env` or share refresh tokens.
- Current implementation is local-first by design (no hosted secret store).
- For a future hosted onboarding service, plan for secure secret storage, per-user isolation, App Check token capture, and abuse/rate controls before public rollout.

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
