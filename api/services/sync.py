"""
Incremental sync from Copilot Money API into local SQLite DB.
Each function: query DB for latest date → pick timeframe → fetch → filter → upsert.
"""

from datetime import date, datetime, timedelta

from copilot_client import (
    fetch_accounts,
    fetch_balance_history,
    fetch_holdings,
    fetch_holding_quantity_by_security,
    fetch_investment_allocation,
    fetch_investment_balance,
    fetch_investment_performance,
    fetch_networth,
    fetch_security_prices,
    fetch_transactions,
)
from db import get_connection


def _pick_timeframe(last_date_str: str | None, max_initial: str = "ALL") -> str:
    """Pick the smallest Copilot timeframe enum that covers the gap."""
    if not last_date_str:
        return max_initial
    last = date.fromisoformat(last_date_str)
    gap = (date.today() - last).days
    if gap <= 7:
        return "ONE_WEEK"
    if gap <= 30:
        return "ONE_MONTH"
    if gap <= 90:
        return "THREE_MONTHS"
    # YTD: covers from Jan 1 of current year
    jan1 = date(date.today().year, 1, 1)
    if last >= jan1:
        return "YTD"
    if gap <= 365:
        return "ONE_YEAR"
    return "ALL"


def sync_accounts():
    """Fetch all investment accounts, upsert into DB."""
    accounts = fetch_accounts()
    conn = get_connection()
    try:
        for a in accounts:
            conn.execute(
                """INSERT OR REPLACE INTO accounts
                   (id, item_id, name, sub_type, institution_id, balance,
                    is_manual, has_historical, has_live_balance, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a["id"], a["itemId"], a["name"], a.get("subType"),
                    a.get("institutionId"), a.get("balance"),
                    int(a.get("isManual", False)),
                    int(a.get("hasHistoricalUpdates", False)),
                    int(a.get("hasLiveBalance", False)),
                    a.get("latestBalanceUpdate"),
                ),
            )
        conn.commit()
        print(f"  synced {len(accounts)} accounts")
    finally:
        conn.close()
    return accounts


def sync_holdings():
    """Fetch current holdings, full replace. Also upserts securities table."""
    holdings = fetch_holdings()
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        conn.execute("DELETE FROM holdings")
        for h in holdings:
            sec = h.get("security") or {}
            metrics = h.get("metrics") or {}
            security_id = sec.get("id")
            # Upsert security
            conn.execute(
                """INSERT OR REPLACE INTO securities
                   (security_id, symbol, name, type, synced_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (security_id, sec.get("symbol"), sec.get("name"),
                 sec.get("type"), now),
            )
            # Insert holding
            conn.execute(
                """INSERT INTO holdings
                   (id, account_id, item_id, symbol, name, quantity,
                    current_price, cost_basis, total_return, average_cost,
                    security_id, synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    h["id"], h.get("accountId"), h.get("itemId"),
                    sec.get("symbol"), sec.get("name"), h.get("quantity"),
                    sec.get("currentPrice"), metrics.get("costBasis"),
                    metrics.get("totalReturn"), metrics.get("averageCost"),
                    security_id, now,
                ),
            )
        conn.commit()
        print(f"  synced {len(holdings)} holdings")
    finally:
        conn.close()
    return holdings


def sync_security_quantities():
    """Per security, incremental sync of daily quantities."""
    conn = get_connection()
    try:
        securities = conn.execute(
            "SELECT security_id, symbol FROM securities"
        ).fetchall()
        total = 0
        for sec in securities:
            sid = sec["security_id"]
            row = conn.execute(
                "SELECT MAX(date) as last_date FROM security_quantities WHERE security_id = ?",
                (sid,),
            ).fetchone()
            tf = _pick_timeframe(row["last_date"] if row else None, max_initial="ONE_YEAR")
            records = fetch_holding_quantity_by_security(sid, timeframe=tf)
            for r in records:
                if r.get("quantity") is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO security_quantities (security_id, date, quantity) VALUES (?, ?, ?)",
                        (sid, r["date"], r["quantity"]),
                    )
                    total += 1
        conn.commit()
        print(f"  synced {total} security quantity records across {len(securities)} securities")
    finally:
        conn.close()


def sync_security_prices():
    """Per security, incremental sync of daily prices."""
    conn = get_connection()
    try:
        securities = conn.execute(
            "SELECT security_id, symbol FROM securities"
        ).fetchall()
        total = 0
        for sec in securities:
            sid = sec["security_id"]
            row = conn.execute(
                "SELECT MAX(date) as last_date FROM security_prices WHERE security_id = ?",
                (sid,),
            ).fetchone()
            tf = _pick_timeframe(row["last_date"] if row else None, max_initial="ONE_YEAR")
            records = fetch_security_prices(sid, timeframe=tf)
            for r in records:
                if r.get("price") is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO security_prices (security_id, date, price) VALUES (?, ?, ?)",
                        (sid, r["date"], r["price"]),
                    )
                    total += 1
        conn.commit()
        print(f"  synced {total} security price records across {len(securities)} securities")
    finally:
        conn.close()


def sync_balance_history(accounts: list[dict] | None = None):
    """Per account, incremental sync of daily balances."""
    conn = get_connection()
    try:
        if accounts is None:
            accounts = [dict(row) for row in conn.execute("SELECT * FROM accounts").fetchall()]
        total = 0
        for a in accounts:
            aid = a.get("id") or a.get("account_id")
            iid = a.get("itemId") or a.get("item_id")
            row = conn.execute(
                "SELECT MAX(date) as last_date FROM balance_history WHERE account_id = ?",
                (aid,),
            ).fetchone()
            tf = _pick_timeframe(row["last_date"] if row else None)
            records = fetch_balance_history(aid, iid, timeframe=tf)
            for r in records:
                conn.execute(
                    "INSERT OR REPLACE INTO balance_history (account_id, date, balance) VALUES (?, ?, ?)",
                    (aid, r["date"], r["balance"]),
                )
            total += len(records)
        conn.commit()
        print(f"  synced {total} balance history records")
    finally:
        conn.close()


def sync_transactions(accounts: list[dict] | None = None):
    """Per account, fetch all transactions, INSERT OR IGNORE on PK."""
    conn = get_connection()
    try:
        if accounts is None:
            accounts = [dict(row) for row in conn.execute("SELECT * FROM accounts").fetchall()]
        total = 0
        for a in accounts:
            aid = a.get("id") or a.get("account_id")
            iid = a.get("itemId") or a.get("item_id")
            txns = fetch_transactions(aid, iid)
            for t in txns:
                conn.execute(
                    """INSERT OR IGNORE INTO transactions
                       (id, account_id, item_id, date, name, amount, type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (t["id"], t.get("accountId"), t.get("itemId"),
                     t.get("date"), t.get("name"), t.get("amount"), t.get("type")),
                )
            total += len(txns)
        conn.commit()
        print(f"  synced {total} transactions")
    finally:
        conn.close()


def sync_investment_balance():
    """Aggregate investment balance, incremental."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(date) as last_date FROM investment_balance_history"
        ).fetchone()
        tf = _pick_timeframe(row["last_date"] if row else None)
        records = fetch_investment_balance(timeframe=tf)
        for r in records:
            conn.execute(
                "INSERT OR REPLACE INTO investment_balance_history (date, balance) VALUES (?, ?)",
                (r["date"], r["balance"]),
            )
        conn.commit()
        print(f"  synced {len(records)} investment balance records")
    finally:
        conn.close()


def sync_investment_performance():
    """Aggregate investment performance, incremental."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(date) as last_date FROM investment_performance_history"
        ).fetchone()
        tf = _pick_timeframe(row["last_date"] if row else None)
        records = fetch_investment_performance(timeframe=tf)
        for r in records:
            conn.execute(
                "INSERT OR REPLACE INTO investment_performance_history (date, performance) VALUES (?, ?)",
                (r["date"], r["performance"]),
            )
        conn.commit()
        print(f"  synced {len(records)} investment performance records")
    finally:
        conn.close()


def sync_networth():
    """Aggregate net worth, incremental."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(date) as last_date FROM networth_history"
        ).fetchone()
        tf = _pick_timeframe(row["last_date"] if row else None)
        records = fetch_networth(timeframe=tf)
        for r in records:
            conn.execute(
                "INSERT OR REPLACE INTO networth_history (date, assets, debt) VALUES (?, ?, ?)",
                (r["date"], r.get("assets"), r.get("debt")),
            )
        conn.commit()
        print(f"  synced {len(records)} networth records")
    finally:
        conn.close()


def sync_allocation_snapshot():
    """Capture today's allocation from the API."""
    today = date.today().isoformat()
    alloc = fetch_investment_allocation()
    conn = get_connection()
    try:
        for a in alloc:
            conn.execute(
                "INSERT OR REPLACE INTO allocation_history (date, type, amount, percentage) VALUES (?, ?, ?, ?)",
                (today, a["type"], a["amount"], a["percentage"]),
            )
        conn.commit()
        print(f"  captured allocation snapshot: {len(alloc)} types")
    finally:
        conn.close()
