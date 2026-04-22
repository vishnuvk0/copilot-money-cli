---
name: copilot-money
description: Query the local investment portfolio API for account data, holdings, balance history, allocations, performance metrics, and trades. Use when the user asks about their investments, portfolio performance, holdings, allocation, returns, or wants to sync Copilot Money data.
---

# Investment Portfolio API

Local FastAPI server backed by SQLite, synced from Copilot Money.

## Starting the Server

```bash
cd /Users/viviku/Documents/copilot/api && source venv/bin/activate && uvicorn main:app --reload
```

Server runs at `http://localhost:8000`. On startup it syncs all data from Copilot Money and precomputes derived metrics. Token is read from `~/Documents/copilot/.env`.

## CLI

```bash
python api/cli.py <command> [options]
python api/cli.py <command> --json   # raw JSON output
```

## Endpoints

### Accounts & Holdings

**GET /api/investments/accounts** — All investment accounts with balances.

**GET /api/investments/holdings** — Current security positions.
- `?account_id=` — filter by account

**GET /api/investments/sync-status** — Last sync info and data ranges per table.

**POST /api/investments/sync** — Trigger a background data sync from Copilot Money.

### Portfolio Snapshots

**GET /api/investments/allocation/{YYYY-MM-DD}** — Holdings breakdown for a date (defaults to nearest available date). Returns each security's symbol, quantity, price, value, weight %, cost basis per share, and unrealized gain %.

**GET /api/investments/filing/{YYYY-MM-DD}** — 13F-style filing with positions, cost basis totals, and sector breakdown by asset type.

**GET /api/investments/allocation-history** — Allocation weights over time.
- `?period=1Y` — 1D|1W|1M|3M|6M|YTD|1Y|ALL
- `?granularity=weekly` — weekly|monthly

### Balance & Trades

**GET /api/investments/balance-history** — Daily portfolio or account balance.
- `?period=1Y` — 1D|1W|1M|3M|6M|YTD|1Y|ALL
- `?account_id=` — filter by account (omit for aggregate)

**GET /api/investments/trades** — Detected buys/sells from quantity changes.
- `?period=ALL` — 1D|1W|1M|3M|6M|YTD|1Y|ALL
- `?security_id=` — filter by security

### Performance & Returns

**GET /api/returns/performance** — TWR, MWR/XIRR, Sharpe, volatility, beta, max drawdown, best/worst day.
- `?period=1Y` — 1D|1W|1M|3M|6M|YTD|1Y|ALL
- `?account_id=` — filter by account

**GET /api/returns/daily-returns** — Daily or cumulative return series.
- `?period=1Y`
- `?account_id=`
- `?cumulative=true` — cumulative instead of daily

**GET /api/returns/comparison** — Portfolio TWR vs S&P 500, with alpha and beta.
- `?period=1Y`
- `?account_id=`

**GET /api/returns/periods** — Performance metrics for every standard period (1D through ALL) in one call.
- `?account_id=`

## Common Queries

| Question | Approach |
|----------|----------|
| "What's my portfolio worth?" | `GET /api/investments/accounts` → sum balances |
| "What do I hold?" | `GET /api/investments/allocation/{today}` |
| "How am I doing?" | `GET /api/returns/periods` for quick overview |
| "Performance this year" | `GET /api/returns/performance?period=YTD` |
| "Am I beating the market?" | `GET /api/returns/comparison?period=1Y` |
| "Show my trades" | `GET /api/investments/trades?period=1Y` |
| "Portfolio breakdown" | `GET /api/investments/filing/{today}` for positions + sector breakdown |
| "Balance over time" | `GET /api/investments/balance-history?period=ALL` |
| "Refresh data" | `POST /api/investments/sync` |

## Example CLI Commands

```bash
# Quick portfolio overview
python api/cli.py accounts
python api/cli.py periods

# What do I hold today?
python api/cli.py allocation

# YTD performance
python api/cli.py performance --period YTD

# Am I beating S&P 500?
python api/cli.py comparison --period 1Y

# Recent trades
python api/cli.py trades --period 3M

# Raw JSON for scripting
python api/cli.py --json performance --period ALL
```
