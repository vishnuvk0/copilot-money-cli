"""
S&P 500 benchmark data and risk-free rate.
Uses yfinance for S&P 500 daily prices, caches in benchmark_prices table.
"""

from datetime import date, timedelta

from db import get_connection

RISK_FREE_RATE = 0.043  # 4.3% annualized (approximate current T-bill rate)


def get_risk_free_daily() -> float:
    """Daily risk-free rate from annualized rate."""
    return (1 + RISK_FREE_RATE) ** (1 / 252) - 1


def sync_benchmark_prices():
    """Fetch S&P 500 daily prices via yfinance and cache in DB."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT MAX(date) as last_date FROM benchmark_prices").fetchone()
        last_date = row["last_date"] if row else None

        if last_date:
            start = date.fromisoformat(last_date) + timedelta(days=1)
        else:
            start = date.today() - timedelta(days=5 * 365)

        if start >= date.today():
            return  # already up to date

        try:
            import yfinance as yf
            spy = yf.download("^GSPC", start=start.isoformat(), end=date.today().isoformat(), progress=False)
            if spy.empty:
                return
            for idx, row_data in spy.iterrows():
                d = idx.strftime("%Y-%m-%d")
                # Handle both MultiIndex and regular Index columns from yfinance
                try:
                    price = float(row_data[("Close", "^GSPC")])
                except (KeyError, TypeError):
                    price = float(row_data["Close"])
                conn.execute(
                    "INSERT OR REPLACE INTO benchmark_prices (date, price) VALUES (?, ?)",
                    (d, price),
                )
            conn.commit()
            print(f"  synced {len(spy)} benchmark price records")
        except ImportError:
            print("  yfinance not installed — skipping benchmark price sync")
    finally:
        conn.close()


def get_benchmark_returns(start_date: str | None = None) -> list[dict]:
    """Get daily benchmark returns from DB."""
    conn = get_connection()
    try:
        sql = "SELECT date, price FROM benchmark_prices"
        params: list = []
        if start_date:
            sql += " WHERE date >= ?"
            params.append(start_date)
        sql += " ORDER BY date"
        rows = conn.execute(sql, params).fetchall()

        returns = []
        for i in range(1, len(rows)):
            prev_price = rows[i - 1]["price"]
            if prev_price > 0:
                daily_ret = (rows[i]["price"] - prev_price) / prev_price
                returns.append({"date": rows[i]["date"], "return": daily_ret})
        return returns
    finally:
        conn.close()
