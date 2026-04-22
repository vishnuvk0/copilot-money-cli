"""
Backfill historical security prices from yfinance for dates where
we have quantity data but no price data.
"""

import sqlite3
from datetime import date, timedelta

import yfinance as yf

from db import get_connection

# Map Copilot security symbols to yfinance tickers
# Crypto symbols need -USD suffix for yfinance
SYMBOL_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "ADA": "ADA-USD",
    "AVAX": "AVAX-USD",
    "MANA": "MANA-USD",
    "USDC": None,   # stablecoin, always $1
    "BUSD": None,   # stablecoin, always $1
    "USD": None,    # cash, always $1
    "FDRXX": None,  # money market, ~$1
    "SPAXX": None,  # money market, ~$1
}

# Options have no yfinance history — skip
def _is_option(symbol: str) -> bool:
    # Options look like AMZN261218C00125000
    return any(c.isdigit() for c in symbol[4:8]) if len(symbol) > 8 else False


def _stable_price() -> float:
    return 1.0


def backfill_all():
    conn = get_connection()
    try:
        securities = conn.execute(
            "SELECT security_id, symbol FROM securities"
        ).fetchall()

        total_inserted = 0

        for sec in securities:
            sid = sec["security_id"]
            symbol = sec["symbol"] or ""

            if not symbol:
                continue

            # Get the date range where we have quantities but no prices
            qty_range = conn.execute(
                "SELECT MIN(date) as mi, MAX(date) as ma FROM security_quantities WHERE security_id = ?",
                (sid,),
            ).fetchone()
            price_min = conn.execute(
                "SELECT MIN(date) as mi FROM security_prices WHERE security_id = ?",
                (sid,),
            ).fetchone()

            if not qty_range["mi"]:
                continue

            # If prices already cover the full quantity range, skip
            if price_min["mi"] and price_min["mi"] <= qty_range["mi"]:
                print(f"  {symbol}: prices already cover full range, skipping")
                continue

            need_from = qty_range["mi"]
            need_to = price_min["mi"] if price_min["mi"] else qty_range["ma"]

            # Handle stablecoins and money market funds
            if symbol in SYMBOL_MAP and SYMBOL_MAP[symbol] is None:
                count = _backfill_stable(conn, sid, symbol, need_from, need_to)
                total_inserted += count
                continue

            # Handle options — skip
            if _is_option(symbol):
                print(f"  {symbol}: option, skipping yfinance backfill")
                continue

            # Map to yfinance ticker
            yf_ticker = SYMBOL_MAP.get(symbol, symbol)
            if yf_ticker is None:
                continue

            count = _backfill_from_yfinance(conn, sid, symbol, yf_ticker, need_from, need_to)
            total_inserted += count

        conn.commit()
        print(f"\nBackfill complete: {total_inserted} price records inserted")
    finally:
        conn.close()


def _backfill_stable(conn, sid, symbol, date_from, date_to):
    """Insert $1.00 for every date in range for stablecoins/money market."""
    d = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    count = 0
    while d <= end:
        ds = d.isoformat()
        existing = conn.execute(
            "SELECT 1 FROM security_prices WHERE security_id = ? AND date = ?",
            (sid, ds),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO security_prices (security_id, date, price) VALUES (?, ?, ?)",
                (sid, ds, 1.0),
            )
            count += 1
        d += timedelta(days=1)
    print(f"  {symbol}: backfilled {count} days @ $1.00")
    return count


def _backfill_from_yfinance(conn, sid, symbol, yf_ticker, date_from, date_to):
    """Fetch historical prices from yfinance and insert missing dates."""
    try:
        # Add a day buffer on each side
        start = (date.fromisoformat(date_from) - timedelta(days=5)).isoformat()
        end = (date.fromisoformat(date_to) + timedelta(days=1)).isoformat()

        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(start=start, end=end, auto_adjust=True)

        if hist.empty:
            print(f"  {symbol} ({yf_ticker}): no yfinance data")
            return 0

        count = 0
        for idx, row in hist.iterrows():
            ds = idx.strftime("%Y-%m-%d")
            price = round(float(row["Close"]), 4)
            existing = conn.execute(
                "SELECT 1 FROM security_prices WHERE security_id = ? AND date = ?",
                (sid, ds),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO security_prices (security_id, date, price) VALUES (?, ?, ?)",
                    (sid, ds, price),
                )
                count += 1

        print(f"  {symbol} ({yf_ticker}): backfilled {count} prices from {date_from} to {date_to}")
        return count

    except Exception as e:
        print(f"  {symbol} ({yf_ticker}): error — {e}")
        return 0


if __name__ == "__main__":
    backfill_all()
