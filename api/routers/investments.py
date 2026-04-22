"""
Investment data endpoints: accounts, holdings, balances, allocations, trades.
"""

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from db import get_db

router = APIRouter(prefix="/api/investments", tags=["investments"])

PERIOD_DAYS = {
    "1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365,
}


def _period_start(period: str) -> str | None:
    """Convert period string to start date ISO string. None = no filter."""
    if period == "ALL":
        return None
    if period == "YTD":
        return date(date.today().year, 1, 1).isoformat()
    days = PERIOD_DAYS.get(period)
    if days:
        return (date.today() - timedelta(days=days)).isoformat()
    return None


# ---------- Accounts ----------

@router.get("/accounts")
def get_accounts(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM accounts ORDER BY balance DESC").fetchall()
    return {"accounts": [dict(r) for r in rows]}


# ---------- Holdings ----------

@router.get("/holdings")
def get_holdings(
    account_id: str | None = Query(None),
    db: sqlite3.Connection = Depends(get_db),
):
    if account_id:
        rows = db.execute(
            "SELECT * FROM holdings WHERE account_id = ? ORDER BY current_price * quantity DESC",
            (account_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM holdings ORDER BY current_price * quantity DESC"
        ).fetchall()
    return {"holdings": [dict(r) for r in rows]}


# ---------- Balance History ----------

@router.get("/balance-history")
def get_balance_history(
    period: str = Query("1Y"),
    account_id: str | None = Query(None),
    db: sqlite3.Connection = Depends(get_db),
):
    start = _period_start(period)

    if account_id:
        sql = "SELECT date, balance FROM balance_history WHERE account_id = ?"
        params: list = [account_id]
        if start:
            sql += " AND date >= ?"
            params.append(start)
        sql += " ORDER BY date"
        rows = db.execute(sql, params).fetchall()
    else:
        # Aggregate from investment_balance_history
        sql = "SELECT date, balance FROM investment_balance_history"
        params = []
        if start:
            sql += " WHERE date >= ?"
            params.append(start)
        sql += " ORDER BY date"
        rows = db.execute(sql, params).fetchall()

    return {
        "period": period,
        "account_id": account_id,
        "data": [{"date": r["date"], "balance": r["balance"]} for r in rows],
    }


# ---------- Allocation for a specific date ----------

@router.get("/allocation/{date_str}")
def get_allocation(
    date_str: str,
    db: sqlite3.Connection = Depends(get_db),
):
    # Find nearest date <= requested date with security_quantities data
    target = date_str

    # Get all securities with quantities on or before this date
    # Use a subquery to aggregate holdings by security_id to avoid
    # duplicate rows when a security is held across multiple accounts
    rows = db.execute(
        """
        SELECT sq.security_id, sq.quantity, sp.price,
               s.symbol, s.name, s.type,
               ha.total_cost_basis, ha.total_holding_qty, ha.avg_cost
        FROM security_quantities sq
        JOIN security_prices sp ON sq.security_id = sp.security_id AND sq.date = sp.date
        JOIN securities s ON sq.security_id = s.security_id
        LEFT JOIN (
            SELECT security_id,
                   SUM(cost_basis) as total_cost_basis,
                   SUM(quantity) as total_holding_qty,
                   CASE WHEN SUM(quantity) > 0
                        THEN SUM(cost_basis) / SUM(quantity)
                        ELSE NULL END as avg_cost
            FROM holdings
            GROUP BY security_id
        ) ha ON sq.security_id = ha.security_id
        WHERE sq.date = (
            SELECT MAX(sq2.date) FROM security_quantities sq2
            WHERE sq2.date <= ? AND sq2.security_id = sq.security_id
        )
        AND sq.quantity > 0
        ORDER BY (sq.quantity * sp.price) DESC
        """,
        (target,),
    ).fetchall()

    # If no exact date, try the nearest prior date across all securities
    if not rows:
        nearest = db.execute(
            "SELECT MAX(date) as d FROM security_quantities WHERE date <= ?",
            (target,),
        ).fetchone()
        if nearest and nearest["d"]:
            target = nearest["d"]
            rows = db.execute(
                """
                SELECT sq.security_id, sq.quantity, sp.price,
                       s.symbol, s.name, s.type,
                       ha.total_cost_basis, ha.total_holding_qty, ha.avg_cost
                FROM security_quantities sq
                JOIN security_prices sp ON sq.security_id = sp.security_id AND sq.date = sp.date
                JOIN securities s ON sq.security_id = s.security_id
                LEFT JOIN (
                    SELECT security_id,
                           SUM(cost_basis) as total_cost_basis,
                           SUM(quantity) as total_holding_qty,
                           CASE WHEN SUM(quantity) > 0
                                THEN SUM(cost_basis) / SUM(quantity)
                                ELSE NULL END as avg_cost
                    FROM holdings
                    GROUP BY security_id
                ) ha ON sq.security_id = ha.security_id
                WHERE sq.date = ? AND sq.quantity > 0
                ORDER BY (sq.quantity * sp.price) DESC
                """,
                (target,),
            ).fetchall()

    total_value = sum(r["quantity"] * r["price"] for r in rows)

    holdings_out = []
    for r in rows:
        value = r["quantity"] * r["price"]
        avg_cost = r["avg_cost"]
        gain_pct = ((r["price"] / avg_cost) - 1) * 100 if avg_cost and avg_cost > 0 else None
        holdings_out.append({
            "symbol": r["symbol"],
            "name": r["name"],
            "type": r["type"],
            "quantity": r["quantity"],
            "price": r["price"],
            "value": round(value, 2),
            "weight_pct": round(value / total_value * 100, 2) if total_value else 0,
            "cost_basis_per_share": avg_cost,
            "unrealized_gain_pct": round(gain_pct, 2) if gain_pct is not None else None,
        })

    return {
        "date": target,
        "total_value": round(total_value, 2),
        "holdings": holdings_out,
    }


# ---------- Allocation History ----------

@router.get("/allocation-history")
def get_allocation_history(
    period: str = Query("1Y"),
    granularity: str = Query("weekly"),
    db: sqlite3.Connection = Depends(get_db),
):
    start = _period_start(period)

    # Get all dates with security_quantities data
    date_sql = "SELECT DISTINCT date FROM security_quantities"
    params: list = []
    if start:
        date_sql += " WHERE date >= ?"
        params.append(start)
    date_sql += " ORDER BY date"
    all_dates = [r["date"] for r in db.execute(date_sql, params).fetchall()]

    # Apply granularity filter
    if granularity == "weekly":
        filtered = []
        last_week = None
        for d in all_dates:
            dt = date.fromisoformat(d)
            week = dt.isocalendar()[1]
            year = dt.year
            key = (year, week)
            if key != last_week:
                filtered.append(d)
                last_week = key
        all_dates = filtered
    elif granularity == "monthly":
        filtered = []
        last_month = None
        for d in all_dates:
            key = d[:7]  # YYYY-MM
            if key != last_month:
                filtered.append(d)
                last_month = key
        all_dates = filtered

    # For each date, compute per-security values
    securities_data: dict[str, dict] = {}  # symbol -> {values: [], weights: []}

    for d in all_dates:
        rows = db.execute(
            """
            SELECT sq.security_id, sq.quantity, sp.price, s.symbol
            FROM security_quantities sq
            JOIN security_prices sp ON sq.security_id = sp.security_id AND sq.date = sp.date
            JOIN securities s ON sq.security_id = s.security_id
            WHERE sq.date = ? AND sq.quantity > 0
            """,
            (d,),
        ).fetchall()

        total = sum(r["quantity"] * r["price"] for r in rows)
        date_values = {}
        for r in rows:
            val = r["quantity"] * r["price"]
            date_values[r["symbol"]] = {
                "value": round(val, 2),
                "weight": round(val / total * 100, 2) if total else 0,
            }

        # Initialize any new securities
        for sym in date_values:
            if sym not in securities_data:
                securities_data[sym] = {"values": [], "weights": []}

        # Fill values for all tracked securities
        for sym in securities_data:
            if sym in date_values:
                securities_data[sym]["values"].append(date_values[sym]["value"])
                securities_data[sym]["weights"].append(date_values[sym]["weight"])
            else:
                securities_data[sym]["values"].append(0)
                securities_data[sym]["weights"].append(0)

    securities_out = [
        {"symbol": sym, "values": data["values"], "weights": data["weights"]}
        for sym, data in sorted(securities_data.items())
    ]

    return {
        "dates": all_dates,
        "securities": securities_out,
    }


# ---------- Filing (13F-style) ----------

@router.get("/filing/{date_str}")
def get_filing(
    date_str: str,
    db: sqlite3.Connection = Depends(get_db),
):
    alloc = get_allocation(date_str, db)
    holdings_list = alloc["holdings"]
    total_mv = alloc["total_value"]

    # Compute cost basis totals
    total_cost = 0
    positions = []
    for h in holdings_list:
        cb = (h["cost_basis_per_share"] or 0) * h["quantity"]
        total_cost += cb
        positions.append({
            "symbol": h["symbol"],
            "name": h["name"],
            "type": h["type"],
            "quantity": h["quantity"],
            "price": h["price"],
            "market_value": h["value"],
            "cost_basis": round(cb, 2),
            "weight_pct": h["weight_pct"],
            "unrealized_gain_pct": h["unrealized_gain_pct"],
        })

    # Sector breakdown by type
    type_agg: dict[str, float] = {}
    for p in positions:
        t = p["type"] or "Unknown"
        type_agg[t] = type_agg.get(t, 0) + p["market_value"]
    sector_breakdown = [
        {
            "type": t,
            "market_value": round(v, 2),
            "weight_pct": round(v / total_mv * 100, 2) if total_mv else 0,
        }
        for t, v in sorted(type_agg.items(), key=lambda x: -x[1])
    ]

    return {
        "filing_date": alloc["date"],
        "total_market_value": total_mv,
        "total_cost_basis": round(total_cost, 2),
        "positions": positions,
        "sector_breakdown": sector_breakdown,
    }


# ---------- Trades ----------

@router.get("/trades")
def get_trades(
    period: str = Query("ALL"),
    security_id: str | None = Query(None),
    db: sqlite3.Connection = Depends(get_db),
):
    start = _period_start(period)

    sql = """
        SELECT sq.security_id, sq.date, sq.quantity, s.symbol, s.name,
               sp.price
        FROM security_quantities sq
        JOIN securities s ON sq.security_id = s.security_id
        LEFT JOIN security_prices sp ON sq.security_id = sp.security_id AND sq.date = sp.date
    """
    conditions = []
    params: list = []
    if security_id:
        conditions.append("sq.security_id = ?")
        params.append(security_id)
    if start:
        conditions.append("sq.date >= ?")
        params.append(start)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY sq.security_id, sq.date"

    rows = db.execute(sql, params).fetchall()

    # Detect quantity changes as trades
    trades = []
    prev: dict[str, float] = {}
    for r in rows:
        sid = r["security_id"]
        qty = r["quantity"]
        if sid in prev:
            diff = qty - prev[sid]
            if abs(diff) > 0.0001:
                price = r["price"] or 0
                trades.append({
                    "date": r["date"],
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "action": "BUY" if diff > 0 else "SELL",
                    "quantity_change": round(abs(diff), 6),
                    "price_on_date": price,
                    "estimated_value": round(abs(diff) * price, 2),
                })
        prev[sid] = qty

    # Sort by date descending
    trades.sort(key=lambda t: t["date"], reverse=True)

    return {"trades": trades}


# ---------- Sync Status ----------

@router.get("/sync-status")
def get_sync_status(db: sqlite3.Connection = Depends(get_db)):
    last_sync = db.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Data range info
    ranges = {}
    for table in ["balance_history", "investment_balance_history", "security_quantities",
                   "security_prices", "transactions", "networth_history"]:
        row = db.execute(
            f"SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count FROM {table}"
        ).fetchone()
        if row and row["count"] > 0:
            ranges[table] = {
                "min_date": row["min_date"],
                "max_date": row["max_date"],
                "count": row["count"],
            }

    return {
        "last_sync": dict(last_sync) if last_sync else None,
        "data_ranges": ranges,
    }


# ---------- Manual Sync ----------

@router.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    from data.loader import load_all
    background_tasks.add_task(load_all)
    return {"status": "sync started"}
