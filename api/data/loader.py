"""
Sync orchestrator — runs all sync steps in dependency order.
"""

from datetime import datetime

from db import get_connection, init_db
from services.sync import (
    sync_accounts,
    sync_allocation_snapshot,
    sync_balance_history,
    sync_holdings,
    sync_investment_balance,
    sync_investment_performance,
    sync_networth,
    sync_security_prices,
    sync_security_quantities,
    sync_transactions,
)


def load_all():
    """Run full incremental sync of all Copilot investment data."""
    init_db()

    conn = get_connection()
    conn.execute(
        "INSERT INTO sync_log (started_at, status) VALUES (?, ?)",
        (datetime.utcnow().isoformat(), "running"),
    )
    conn.commit()
    log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    try:
        print("Starting full sync...")

        # 1. Accounts first (everything depends on account list)
        print("[1/10] Syncing accounts...")
        accounts = sync_accounts()

        # 2. Holdings (also populates securities table)
        print("[2/10] Syncing holdings...")
        sync_holdings()

        # 3-4. Security quantities and prices (need securities from step 2)
        print("[3/10] Syncing security quantities...")
        sync_security_quantities()

        print("[4/10] Syncing security prices...")
        sync_security_prices()

        # 5. Per-account balance history
        print("[5/10] Syncing balance history...")
        sync_balance_history(accounts)

        # 6. Transactions
        print("[6/10] Syncing transactions...")
        sync_transactions(accounts)

        # 7-9. Aggregate data
        print("[7/10] Syncing investment balance...")
        sync_investment_balance()

        print("[8/10] Syncing investment performance...")
        sync_investment_performance()

        print("[9/10] Syncing net worth...")
        sync_networth()

        # 10. Allocation snapshot
        print("[10/10] Capturing allocation snapshot...")
        sync_allocation_snapshot()

        # Mark success
        conn = get_connection()
        conn.execute(
            "UPDATE sync_log SET completed_at = ?, status = ?, accounts_synced = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), "success", len(accounts), log_id),
        )
        conn.commit()
        conn.close()
        print("Sync complete.")

    except Exception as e:
        conn = get_connection()
        conn.execute(
            "UPDATE sync_log SET completed_at = ?, status = ?, error = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), "error", str(e), log_id),
        )
        conn.commit()
        conn.close()
        print(f"Sync failed: {e}")
        raise
