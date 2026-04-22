"""
Performance calculation engine: TWR, XIRR, Sharpe, Volatility, Beta, Max Drawdown.
All calculations work from DB data.
"""

import math
from datetime import date, timedelta

from db import get_connection
from services.market_data import get_benchmark_returns, get_risk_free_daily

PERIOD_DAYS = {
    "1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365,
}


def _period_start(period: str) -> str | None:
    if period == "ALL":
        return None
    if period == "YTD":
        return date(date.today().year, 1, 1).isoformat()
    days = PERIOD_DAYS.get(period)
    if days:
        return (date.today() - timedelta(days=days)).isoformat()
    return None


def _get_daily_balances(period: str, account_id: str | None = None) -> list[dict]:
    """Fetch daily balance series from DB."""
    conn = get_connection()
    try:
        start = _period_start(period)
        if account_id:
            sql = "SELECT date, balance FROM balance_history WHERE account_id = ?"
            params: list = [account_id]
            if start:
                sql += " AND date >= ?"
                params.append(start)
        else:
            sql = "SELECT date, balance FROM investment_balance_history"
            params = []
            if start:
                sql += " WHERE date >= ?"
                params.append(start)
        sql += " ORDER BY date"
        rows = conn.execute(sql, params).fetchall()
        return [{"date": r["date"], "balance": r["balance"]} for r in rows]
    finally:
        conn.close()


def _daily_returns_from_balances(balances: list[dict]) -> list[dict]:
    """Compute daily returns from a balance series."""
    returns = []
    for i in range(1, len(balances)):
        prev = balances[i - 1]["balance"]
        if prev and prev > 0:
            ret = (balances[i]["balance"] - prev) / prev
            returns.append({"date": balances[i]["date"], "return": ret})
    return returns


# ---------- TWR (Time-Weighted Return) ----------

def calc_twr(period: str, account_id: str | None = None) -> float | None:
    """∏(1 + r_t) - 1 over the period."""
    balances = _get_daily_balances(period, account_id)
    if len(balances) < 2:
        return None
    product = 1.0
    for i in range(1, len(balances)):
        prev = balances[i - 1]["balance"]
        if prev and prev > 0:
            product *= balances[i]["balance"] / prev
    return product - 1


# ---------- XIRR (MWR via Newton-Raphson) ----------

def _xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float | None:
    """Pure-Python Newton-Raphson XIRR solver.
    cashflows: list of (date, amount) where negative = outflow, positive = inflow.
    """
    if not cashflows or len(cashflows) < 2:
        return None

    d0 = cashflows[0][0]

    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** ((d - d0).days / 365.0) for d, cf in cashflows)

    def dnpv(rate: float) -> float:
        return sum(
            -((d - d0).days / 365.0) * cf / (1 + rate) ** ((d - d0).days / 365.0 + 1)
            for d, cf in cashflows
        )

    rate = guess
    for _ in range(100):
        f = npv(rate)
        df = dnpv(rate)
        if abs(df) < 1e-12:
            break
        new_rate = rate - f / df
        if abs(new_rate - rate) < 1e-9:
            return new_rate
        rate = new_rate
        if abs(rate) > 10:  # diverging
            return None
    return rate


def calc_xirr(period: str, account_id: str | None = None) -> float | None:
    """Money-weighted return using transaction cash flows + terminal balance."""
    conn = get_connection()
    try:
        start = _period_start(period)
        balances = _get_daily_balances(period, account_id)
        if len(balances) < 2:
            return None

        # Get transactions as cash flows
        sql = "SELECT date, amount FROM transactions"
        conditions = []
        params: list = []
        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)
        if start:
            conditions.append("date >= ?")
            params.append(start)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY date"
        txns = conn.execute(sql, params).fetchall()

        # Build cashflows: initial balance (negative = investment), transactions, final balance (positive)
        cashflows: list[tuple[date, float]] = []
        first_balance = balances[0]
        cashflows.append((date.fromisoformat(first_balance["date"]), -first_balance["balance"]))

        for t in txns:
            d = date.fromisoformat(t["date"])
            # In Copilot, negative amounts are debits (money out of account = contributions)
            # Positive amounts are credits (money into account = withdrawals)
            # For XIRR: contributions are negative (cash outflow), withdrawals are positive
            cashflows.append((d, t["amount"]))

        last_balance = balances[-1]
        cashflows.append((date.fromisoformat(last_balance["date"]), last_balance["balance"]))

        return _xirr(cashflows)
    finally:
        conn.close()


# ---------- Volatility ----------

def calc_volatility(period: str, account_id: str | None = None) -> float | None:
    """Annualized volatility = std(daily_returns) × √252."""
    balances = _get_daily_balances(period, account_id)
    returns = _daily_returns_from_balances(balances)
    if len(returns) < 2:
        return None
    mean = sum(r["return"] for r in returns) / len(returns)
    variance = sum((r["return"] - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252)


# ---------- Sharpe Ratio ----------

def calc_sharpe(period: str, account_id: str | None = None) -> float | None:
    """(mean(excess_daily_returns) / std(excess_daily_returns)) × √252."""
    balances = _get_daily_balances(period, account_id)
    returns = _daily_returns_from_balances(balances)
    if len(returns) < 2:
        return None
    rf_daily = get_risk_free_daily()
    excess = [r["return"] - rf_daily for r in returns]
    mean_excess = sum(excess) / len(excess)
    variance = sum((e - mean_excess) ** 2 for e in excess) / (len(excess) - 1)
    std_excess = math.sqrt(variance)
    if std_excess < 1e-12:
        return None
    return (mean_excess / std_excess) * math.sqrt(252)


# ---------- Beta ----------

def calc_beta(period: str, account_id: str | None = None) -> float | None:
    """cov(portfolio, market) / var(market)."""
    balances = _get_daily_balances(period, account_id)
    port_returns = _daily_returns_from_balances(balances)
    if len(port_returns) < 5:
        return None

    start = port_returns[0]["date"]
    bench_returns = get_benchmark_returns(start)

    # Align by date
    bench_map = {r["date"]: r["return"] for r in bench_returns}
    aligned_port = []
    aligned_bench = []
    for pr in port_returns:
        if pr["date"] in bench_map:
            aligned_port.append(pr["return"])
            aligned_bench.append(bench_map[pr["date"]])

    n = len(aligned_port)
    if n < 5:
        return None

    mean_p = sum(aligned_port) / n
    mean_b = sum(aligned_bench) / n
    cov = sum((aligned_port[i] - mean_p) * (aligned_bench[i] - mean_b) for i in range(n)) / (n - 1)
    var_b = sum((aligned_bench[i] - mean_b) ** 2 for i in range(n)) / (n - 1)
    if var_b < 1e-12:
        return None
    return cov / var_b


# ---------- Max Drawdown ----------

def calc_max_drawdown(period: str, account_id: str | None = None) -> dict | None:
    """Largest peak-to-trough decline."""
    balances = _get_daily_balances(period, account_id)
    if len(balances) < 2:
        return None

    peak = balances[0]["balance"]
    max_dd = 0.0
    worst_date = balances[0]["date"]
    best_date = None
    worst_date_val = None

    for b in balances:
        if b["balance"] > peak:
            peak = b["balance"]
        dd = (b["balance"] - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
            worst_date = b["date"]

    return {"max_drawdown": max_dd, "worst_date": worst_date}


# ---------- Best/Worst Day ----------

def calc_best_worst_day(period: str, account_id: str | None = None) -> dict:
    balances = _get_daily_balances(period, account_id)
    returns = _daily_returns_from_balances(balances)
    if not returns:
        return {"best_day": None, "worst_day": None}

    best = max(returns, key=lambda r: r["return"])
    worst = min(returns, key=lambda r: r["return"])
    return {
        "best_day": {"date": best["date"], "return": best["return"]},
        "worst_day": {"date": worst["date"], "return": worst["return"]},
    }


# ---------- Daily Returns Series ----------

def get_daily_returns(period: str, account_id: str | None = None, cumulative: bool = False) -> list[dict]:
    balances = _get_daily_balances(period, account_id)
    returns = _daily_returns_from_balances(balances)

    if cumulative and returns:
        cum = 0.0
        for r in returns:
            cum = (1 + cum) * (1 + r["return"]) - 1
            r["return"] = cum

    return returns


# ---------- All Metrics ----------

def calc_all_metrics(period: str, account_id: str | None = None) -> dict:
    """Calculate all performance metrics for a given period."""
    twr = calc_twr(period, account_id)
    xirr = calc_xirr(period, account_id)
    sharpe = calc_sharpe(period, account_id)
    vol = calc_volatility(period, account_id)
    beta = calc_beta(period, account_id)
    dd = calc_max_drawdown(period, account_id)
    bw = calc_best_worst_day(period, account_id)

    return {
        "twr": round(twr, 6) if twr is not None else None,
        "mwr_xirr": round(xirr, 6) if xirr is not None else None,
        "sharpe_ratio": round(sharpe, 4) if sharpe is not None else None,
        "volatility": round(vol, 6) if vol is not None else None,
        "beta": round(beta, 4) if beta is not None else None,
        "max_drawdown": round(dd["max_drawdown"], 6) if dd else None,
        "best_day": bw["best_day"],
        "worst_day": bw["worst_day"],
    }


# ---------- Cost Basis History ----------

def populate_cost_basis_history():
    """Precompute aggregate cost basis from holdings snapshots."""
    conn = get_connection()
    try:
        # Use current holdings cost basis as today's snapshot
        row = conn.execute(
            "SELECT SUM(cost_basis) as total FROM holdings WHERE cost_basis IS NOT NULL"
        ).fetchone()
        if row and row["total"]:
            today = date.today().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO cost_basis_history (date, cost_basis) VALUES (?, ?)",
                (today, row["total"]),
            )
            conn.commit()
    finally:
        conn.close()
