"""
Portfolio precomputation: cost basis history and allocation snapshots.
"""

from datetime import date

from db import get_connection
from services.market_data import sync_benchmark_prices


def precompute():
    """Run all precomputation steps after sync."""
    print("Running portfolio precomputation...")

    # Sync benchmark (S&P 500) prices for Beta/Sharpe calculations
    try:
        sync_benchmark_prices()
    except Exception as e:
        print(f"  benchmark sync failed (non-fatal): {e}")

    # Precompute cost basis history from current holdings
    conn = get_connection()
    try:
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
            print(f"  cost basis snapshot: {row['total']:.2f}")
    finally:
        conn.close()

    print("Precomputation complete.")
