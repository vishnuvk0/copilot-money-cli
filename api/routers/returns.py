"""
Returns and performance endpoints: metrics, daily returns, benchmark comparison.
"""

from fastapi import APIRouter, Query

from services.market_data import get_benchmark_returns
from services.returns import (
    calc_all_metrics,
    calc_beta,
    calc_twr,
    get_daily_returns,
    _period_start,
)

router = APIRouter(prefix="/api/returns", tags=["returns"])

ALL_PERIODS = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL"]


@router.get("/performance")
def get_performance(
    period: str = Query("1Y"),
    account_id: str | None = Query(None),
):
    metrics = calc_all_metrics(period, account_id)
    return {
        "period": period,
        "account_id": account_id,
        "metrics": metrics,
    }


@router.get("/daily-returns")
def get_daily_returns_endpoint(
    period: str = Query("1Y"),
    account_id: str | None = Query(None),
    cumulative: bool = Query(False),
):
    data = get_daily_returns(period, account_id, cumulative)
    return {"period": period, "cumulative": cumulative, "data": data}


@router.get("/comparison")
def get_comparison(
    period: str = Query("1Y"),
    account_id: str | None = Query(None),
):
    # Portfolio
    port_twr = calc_twr(period, account_id)
    port_returns = get_daily_returns(period, account_id, cumulative=True)

    # Benchmark
    start = _period_start(period)
    bench_daily = get_benchmark_returns(start)
    bench_cum = []
    cum = 0.0
    for r in bench_daily:
        cum = (1 + cum) * (1 + r["return"]) - 1
        bench_cum.append({"date": r["date"], "return": cum})
    bench_twr = bench_cum[-1]["return"] if bench_cum else None

    beta = calc_beta(period, account_id)
    alpha = (port_twr - bench_twr) if port_twr is not None and bench_twr is not None else None

    return {
        "portfolio": {
            "twr": round(port_twr, 6) if port_twr is not None else None,
            "data": port_returns,
        },
        "benchmark": {
            "name": "S&P 500",
            "twr": round(bench_twr, 6) if bench_twr is not None else None,
            "data": bench_cum,
        },
        "alpha": round(alpha, 6) if alpha is not None else None,
        "beta": round(beta, 4) if beta is not None else None,
    }


@router.get("/periods")
def get_all_periods(
    account_id: str | None = Query(None),
):
    periods = {}
    for p in ALL_PERIODS:
        metrics = calc_all_metrics(p, account_id)
        periods[p] = metrics

    return {"account_id": account_id, "periods": periods}
