"""
SQLite database for Copilot Money investment data.
Uses stdlib sqlite3 — no extra dependencies.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "investments.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    name TEXT NOT NULL,
    sub_type TEXT,
    institution_id TEXT,
    balance REAL,
    is_manual INTEGER DEFAULT 0,
    has_historical INTEGER DEFAULT 0,
    has_live_balance INTEGER DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS balance_history (
    account_id TEXT NOT NULL,
    date TEXT NOT NULL,
    balance REAL NOT NULL,
    PRIMARY KEY (account_id, date)
);
CREATE INDEX IF NOT EXISTS idx_balance_history_account ON balance_history(account_id);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    item_id TEXT,
    date TEXT,
    name TEXT,
    amount REAL,
    type TEXT
);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, date);

CREATE TABLE IF NOT EXISTS holdings (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    item_id TEXT,
    symbol TEXT,
    name TEXT,
    quantity REAL,
    current_price REAL,
    cost_basis REAL,
    total_return REAL,
    average_cost REAL,
    synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_holdings_account ON holdings(account_id);

CREATE TABLE IF NOT EXISTS networth_history (
    date TEXT PRIMARY KEY,
    assets REAL,
    debt REAL
);

CREATE TABLE IF NOT EXISTS detected_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_account TEXT,
    to_account TEXT,
    date TEXT,
    amount REAL,
    confidence REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    completed_at TEXT,
    status TEXT,
    accounts_synced INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS cost_basis_history (
    date TEXT PRIMARY KEY,
    cost_basis REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT,
    type TEXT,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS security_quantities (
    security_id TEXT NOT NULL,
    date TEXT NOT NULL,
    quantity REAL NOT NULL,
    PRIMARY KEY (security_id, date)
);

CREATE TABLE IF NOT EXISTS security_prices (
    security_id TEXT NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    PRIMARY KEY (security_id, date)
);

CREATE TABLE IF NOT EXISTS investment_balance_history (
    date TEXT PRIMARY KEY,
    balance REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_performance_history (
    date TEXT PRIMARY KEY,
    performance REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS allocation_history (
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    percentage REAL NOT NULL,
    PRIMARY KEY (date, type)
);

CREATE TABLE IF NOT EXISTS benchmark_prices (
    date TEXT PRIMARY KEY,
    price REAL NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """Get a connection to the investments database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection):
    """Run migrations that ALTER TABLE can't express in CREATE IF NOT EXISTS."""
    cursor = conn.execute("PRAGMA table_info(holdings)")
    cols = {row[1] for row in cursor.fetchall()}
    if "security_id" not in cols:
        conn.execute("ALTER TABLE holdings ADD COLUMN security_id TEXT")


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def get_db():
    """Get a connection (for use in FastAPI dependency injection)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
