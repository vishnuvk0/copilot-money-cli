#!/usr/bin/env python3
"""CLI for the investment portfolio API."""

import argparse
import json
import re
import sys
from datetime import date

import requests
import copilot_client as cc

BASE_URL = "http://localhost:8000"

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

USE_COLOR = sys.stdout.isatty()

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def c(text, code):
    return f"{code}{text}{RESET}" if USE_COLOR else str(text)


def fmt_dollar(val):
    if val is None:
        return "—"
    neg = val < 0
    s = f"${abs(val):,.2f}"
    if neg:
        s = f"-{s}"
    return c(s, RED) if neg else s


def fmt_pct(val, sign=True):
    if val is None:
        return "—"
    prefix = "+" if val > 0 and sign else ""
    s = f"{prefix}{val:.2f}%"
    color = GREEN if val > 0 else RED if val < 0 else ""
    return c(s, color) if color else s


def fmt_num(val, decimals=2):
    if val is None:
        return "—"
    if decimals == 0:
        return f"{val:,.0f}"
    return f"{val:,.{decimals}f}"


def visible_len(s):
    return len(ANSI_RE.sub("", str(s)))


def print_table(headers, rows, alignments=None):
    """Print a fixed-width table. alignments: 'l' or 'r' per column."""
    if not rows:
        print("  (no data)")
        return

    all_rows = [headers] + rows
    widths = [0] * len(headers)
    for row in all_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], visible_len(cell))

    if not alignments:
        alignments = ["l"] * len(headers)

    header_parts = []
    for i, h in enumerate(headers):
        pad = widths[i] - visible_len(h)
        if alignments[i] == "r":
            header_parts.append(" " * pad + c(h, BOLD))
        else:
            header_parts.append(c(h, BOLD) + " " * pad)
    print("  " + "  ".join(header_parts))
    print("  " + "  ".join("─" * w for w in widths))

    for row in rows:
        parts = []
        for i, cell in enumerate(row):
            pad = widths[i] - visible_len(str(cell))
            if alignments[i] == "r":
                parts.append(" " * pad + str(cell))
            else:
                parts.append(str(cell) + " " * pad)
        print("  " + "  ".join(parts))


def api(method, path, base_url, **params):
    """Make an API request and return JSON."""
    url = f"{base_url}{path}"
    try:
        if method == "GET":
            r = requests.get(url, params={k: v for k, v in params.items() if v is not None})
        else:
            r = requests.post(url)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        print(f"Error: cannot connect to {base_url}", file=sys.stderr)
        print("Start the server: cd api && source venv/bin/activate && uvicorn main:app", file=sys.stderr)
        sys.exit(1)
    except requests.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# ── Subcommands ──────────────────────────────────────────────


def cmd_accounts(args):
    data = api("GET", "/api/investments/accounts", args.base_url)
    if args.json:
        return data
    accts = data["accounts"]
    print(f"\n  {c('Investment Accounts', BOLD)} ({len(accts)})\n")
    headers = ["Name", "Type", "Balance", "Updated"]
    rows = []
    for a in accts:
        rows.append([
            a.get("name") or a["id"][:12],
            a.get("sub_type") or "—",
            fmt_dollar(a.get("balance")),
            (a.get("updated_at") or "—")[:10],
        ])
    print_table(headers, rows, ["l", "l", "r", "l"])
    total = sum(a.get("balance") or 0 for a in accts)
    print(f"\n  Total: {fmt_dollar(total)}\n")


def cmd_holdings(args):
    data = api("GET", "/api/investments/holdings", args.base_url, account_id=args.account_id)
    if args.json:
        return data
    holdings = data["holdings"]
    print(f"\n  {c('Holdings', BOLD)} ({len(holdings)})\n")
    headers = ["Symbol", "Name", "Qty", "Price", "Value", "Return"]
    rows = []
    for h in holdings:
        qty = h.get("quantity") or 0
        price = h.get("current_price") or 0
        value = qty * price
        ret = h.get("total_return")
        rows.append([
            h.get("symbol") or "—",
            (h.get("name") or "—")[:30],
            fmt_num(qty, 4),
            fmt_dollar(price),
            fmt_dollar(value),
            fmt_pct(ret * 100 if ret is not None else None),
        ])
    print_table(headers, rows, ["l", "l", "r", "r", "r", "r"])
    print()


def cmd_balance(args):
    data = api("GET", "/api/investments/balance-history", args.base_url,
               period=args.period, account_id=args.account_id)
    if args.json:
        return data
    points = data["data"]
    if not points:
        print("  No balance data for this period.")
        return
    label = f"Balance History ({data['period']})"
    print(f"\n  {c(label, BOLD)}\n")
    balances = [p["balance"] for p in points]
    first, last = points[0], points[-1]
    change = last["balance"] - first["balance"]
    print(f"  Start: {first['date']}  {fmt_dollar(first['balance'])}")
    print(f"  End:   {last['date']}  {fmt_dollar(last['balance'])}")
    print(f"  Change: {fmt_dollar(change)}  ({fmt_pct(change / first['balance'] * 100 if first['balance'] else 0)})")
    print(f"  Low:  {fmt_dollar(min(balances))}   High: {fmt_dollar(max(balances))}")
    print(f"  Data points: {len(points)}\n")


def cmd_allocation(args):
    date_str = args.date or date.today().isoformat()
    data = api("GET", f"/api/investments/allocation/{date_str}", args.base_url)
    if args.json:
        return data
    print(f"\n  {c('Allocation', BOLD)} — {data['date']}  (Total: {fmt_dollar(data['total_value'])})\n")
    headers = ["Symbol", "Name", "Qty", "Price", "Value", "Weight", "Gain"]
    rows = []
    for h in data["holdings"]:
        rows.append([
            h["symbol"],
            (h.get("name") or "—")[:25],
            fmt_num(h["quantity"], 4),
            fmt_dollar(h["price"]),
            fmt_dollar(h["value"]),
            f"{h['weight_pct']:.1f}%",
            fmt_pct(h.get("unrealized_gain_pct")),
        ])
    print_table(headers, rows, ["l", "l", "r", "r", "r", "r", "r"])
    print()


def cmd_allocation_history(args):
    data = api("GET", "/api/investments/allocation-history", args.base_url,
               period=args.period, granularity=args.granularity)
    if args.json:
        return data
    dates = data["dates"]
    secs = data["securities"]
    if not dates:
        print("  No allocation history data.")
        return
    print(f"\n  {c('Allocation History', BOLD)} ({args.period}, {args.granularity})\n")
    print(f"  Date range: {dates[0]} → {dates[-1]}  ({len(dates)} snapshots)")
    print(f"  Securities tracked: {len(secs)}\n")
    if secs and dates:
        headers = ["Symbol", "Latest Weight", "Latest Value"]
        rows = []
        for s in sorted(secs, key=lambda x: x["weights"][-1] if x["weights"] else 0, reverse=True):
            w = s["weights"][-1] if s["weights"] else 0
            v = s["values"][-1] if s["values"] else 0
            if w > 0.1:
                rows.append([s["symbol"], f"{w:.1f}%", fmt_dollar(v)])
        print_table(headers, rows, ["l", "r", "r"])
    print()


def cmd_filing(args):
    date_str = args.date or date.today().isoformat()
    data = api("GET", f"/api/investments/filing/{date_str}", args.base_url)
    if args.json:
        return data
    print(f"\n  {c('13F-Style Filing', BOLD)} — {data['filing_date']}\n")
    print(f"  Market Value:  {fmt_dollar(data['total_market_value'])}")
    print(f"  Cost Basis:    {fmt_dollar(data['total_cost_basis'])}")
    gain = data["total_market_value"] - data["total_cost_basis"]
    print(f"  Unrealized:    {fmt_dollar(gain)}")
    print()
    headers = ["Symbol", "Name", "Qty", "Price", "MV", "Cost", "Wt%", "Gain%"]
    rows = []
    for p in data["positions"]:
        rows.append([
            p["symbol"],
            (p.get("name") or "—")[:20],
            fmt_num(p["quantity"], 2),
            fmt_dollar(p["price"]),
            fmt_dollar(p["market_value"]),
            fmt_dollar(p["cost_basis"]),
            f"{p['weight_pct']:.1f}%",
            fmt_pct(p.get("unrealized_gain_pct")),
        ])
    print_table(headers, rows, ["l", "l", "r", "r", "r", "r", "r", "r"])

    if data.get("sector_breakdown"):
        print(f"\n  {c('Sector Breakdown', BOLD)}\n")
        headers = ["Type", "Market Value", "Weight"]
        rows = []
        for s in data["sector_breakdown"]:
            rows.append([s["type"], fmt_dollar(s["market_value"]), f"{s['weight_pct']:.1f}%"])
        print_table(headers, rows, ["l", "r", "r"])
    print()


def cmd_trades(args):
    data = api("GET", "/api/investments/trades", args.base_url,
               period=args.period, security_id=args.security_id)
    if args.json:
        return data
    trades = data["trades"]
    print(f"\n  {c('Trades', BOLD)} ({len(trades)})\n")
    headers = ["Date", "Symbol", "Action", "Qty", "Price", "Value"]
    rows = []
    for t in trades:
        action = t["action"]
        action_str = c(action, GREEN if action == "BUY" else RED)
        rows.append([
            t["date"],
            t["symbol"],
            action_str,
            fmt_num(t["quantity_change"], 4),
            fmt_dollar(t["price_on_date"]),
            fmt_dollar(t["estimated_value"]),
        ])
    print_table(headers, rows, ["l", "l", "l", "r", "r", "r"])
    print()


def cmd_performance(args):
    data = api("GET", "/api/returns/performance", args.base_url,
               period=args.period, account_id=args.account_id)
    if args.json:
        return data
    m = data["metrics"]
    print(f"\n  {c('Performance', BOLD)} ({data['period']})\n")
    items = [
        ("TWR", fmt_pct(m.get("twr") and m["twr"] * 100)),
        ("MWR (XIRR)", fmt_pct(m.get("mwr_xirr") and m["mwr_xirr"] * 100)),
        ("Sharpe Ratio", fmt_num(m.get("sharpe_ratio"))),
        ("Volatility", fmt_pct(m.get("volatility") and m["volatility"] * 100)),
        ("Beta", fmt_num(m.get("beta"))),
        ("Max Drawdown", fmt_pct(m.get("max_drawdown") and m["max_drawdown"] * 100)),
    ]
    for label, val in items:
        print(f"  {label:<15} {val}")

    best = m.get("best_day")
    worst = m.get("worst_day")
    if best:
        print(f"  {'Best Day':<15} {best['date']}  {fmt_pct(best['return'] * 100)}")
    if worst:
        print(f"  {'Worst Day':<15} {worst['date']}  {fmt_pct(worst['return'] * 100)}")
    print()


def cmd_returns(args):
    data = api("GET", "/api/returns/daily-returns", args.base_url,
               period=args.period, account_id=args.account_id,
               cumulative=str(args.cumulative).lower())
    if args.json:
        return data
    points = data["data"]
    if not points:
        print("  No return data for this period.")
        return
    mode = "Cumulative" if data["cumulative"] else "Daily"
    print(f"\n  {c(f'{mode} Returns', BOLD)} ({data['period']})\n")
    if data["cumulative"] and points:
        print(f"  Total: {fmt_pct(points[-1]['return'] * 100)}")
        print(f"  Data points: {len(points)}")
    else:
        rets = [p["return"] for p in points]
        pos = sum(1 for r in rets if r > 0)
        neg = sum(1 for r in rets if r < 0)
        avg = sum(rets) / len(rets) if rets else 0
        print(f"  Days: {len(rets)}  (Up: {pos}, Down: {neg})")
        print(f"  Avg daily: {fmt_pct(avg * 100)}")
    recent = points[-10:]
    print()
    headers = ["Date", "Return"]
    rows = [[p["date"], fmt_pct(p["return"] * 100)] for p in recent]
    print_table(headers, rows, ["l", "r"])
    if len(points) > 10:
        print(f"  ... ({len(points) - 10} more rows, use --json for full data)")
    print()


def cmd_comparison(args):
    data = api("GET", "/api/returns/comparison", args.base_url,
               period=args.period, account_id=args.account_id)
    if args.json:
        return data
    port = data["portfolio"]
    bench = data["benchmark"]
    print(f"\n  {c('Portfolio vs Benchmark', BOLD)} ({args.period})\n")
    headers = ["", "TWR", ""]
    rows = [
        ["Portfolio", fmt_pct(port["twr"] and port["twr"] * 100), ""],
        [bench["name"], fmt_pct(bench["twr"] and bench["twr"] * 100), ""],
    ]
    print_table(headers, rows, ["l", "r", "l"])
    print()
    print(f"  Alpha: {fmt_pct(data['alpha'] and data['alpha'] * 100)}")
    print(f"  Beta:  {fmt_num(data.get('beta'))}")
    print()


def cmd_periods(args):
    data = api("GET", "/api/returns/periods", args.base_url, account_id=args.account_id)
    if args.json:
        return data
    print(f"\n  {c('Performance by Period', BOLD)}\n")
    headers = ["Period", "TWR", "Sharpe", "Volatility", "Max DD"]
    rows = []
    for period in ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL"]:
        m = data["periods"].get(period, {})
        rows.append([
            period,
            fmt_pct(m.get("twr") and m["twr"] * 100),
            fmt_num(m.get("sharpe_ratio")),
            fmt_pct(m.get("volatility") and m["volatility"] * 100),
            fmt_pct(m.get("max_drawdown") and m["max_drawdown"] * 100),
        ])
    print_table(headers, rows, ["l", "r", "r", "r", "r"])
    print()


def cmd_sync_status(args):
    data = api("GET", "/api/investments/sync-status", args.base_url)
    if args.json:
        return data
    ls = data.get("last_sync")
    print(f"\n  {c('Sync Status', BOLD)}\n")
    if ls:
        print(f"  Last sync: {ls.get('started_at', '—')}")
        print(f"  Status:    {ls.get('status', '—')}")
        print(f"  Accounts:  {ls.get('accounts_synced', '—')}")
        if ls.get("error"):
            print(f"  Error:     {c(ls['error'], RED)}")
    else:
        print("  No syncs recorded.")
    ranges = data.get("data_ranges", {})
    if ranges:
        print(f"\n  {c('Data Ranges', BOLD)}\n")
        headers = ["Table", "From", "To", "Rows"]
        rows = []
        for table, info in sorted(ranges.items()):
            rows.append([table, info["min_date"], info["max_date"], fmt_num(info["count"], 0)])
        print_table(headers, rows, ["l", "l", "l", "r"])
    print()


def cmd_sync(args):
    data = api("POST", "/api/investments/sync", args.base_url)
    if args.json:
        return data
    print(f"\n  {c('Sync triggered', GREEN)}: {data.get('status', 'started')}\n")


def cmd_auth_start(args):
    if args.app_check_token or args.gmpid:
        cc.configure_onboarding_values(args.app_check_token, args.gmpid)
    data = cc.start_magic_link(args.email)
    if args.json:
        return {"status": "sent", "email": data.get("email")}
    print(f"\n  {c('Magic link sent', GREEN)} to {data.get('email', args.email)}")
    print("  Next: run `python api/cli.py auth complete --email <email> --magic-link <url>`\n")


def cmd_auth_complete(args):
    if args.app_check_token or args.gmpid:
        cc.configure_onboarding_values(args.app_check_token, args.gmpid)
    data = cc.complete_magic_link(args.email, args.magic_link)
    accounts = cc.fetch_accounts()
    sync = api("POST", "/api/investments/sync", args.base_url)
    if args.json:
        return {
            "email": data.get("email"),
            "accounts": len(accounts),
            "sync_status": sync.get("status"),
        }
    print(f"\n  {c('Authenticated', GREEN)} as {data.get('email', args.email)}")
    print(f"  Accounts available: {len(accounts)}")
    print(f"  Sync status: {sync.get('status', 'started')}\n")


def cmd_auth_status(args):
    status = cc.get_auth_status()
    if args.json:
        return status
    print(f"\n  {c('Auth Status', BOLD)}\n")
    print(f"  Token present:         {'yes' if status['has_token'] else 'no'}")
    print(f"  Refresh token present: {'yes' if status['has_refresh_token'] else 'no'}")
    print(f"  App Check token set:   {'yes' if status['has_app_check_token'] else 'no'}")
    if status.get("email"):
        print(f"  Email:                 {status['email']}")
    if status.get("expires_at"):
        print(f"  Token expires at:      {status['expires_at']}")
        print(f"  Token expired:         {'yes' if status['expired'] else 'no'}")
    print()


# ── Main ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="invest",
        description="Investment portfolio CLI — query the local API",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--base-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")

    sub = parser.add_subparsers(dest="command", required=True)

    # accounts
    sub.add_parser("accounts", help="List investment accounts")

    # holdings
    p = sub.add_parser("holdings", help="List current holdings")
    p.add_argument("--account-id", help="Filter by account ID")

    # balance
    p = sub.add_parser("balance", help="Balance history")
    p.add_argument("--period", default="1Y", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--account-id", help="Filter by account ID")

    # allocation
    p = sub.add_parser("allocation", help="Portfolio allocation for a date")
    p.add_argument("date", nargs="?", help="YYYY-MM-DD (default: today)")

    # allocation-history
    p = sub.add_parser("allocation-history", help="Allocation over time")
    p.add_argument("--period", default="1Y", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--granularity", default="weekly", help="weekly|monthly")

    # filing
    p = sub.add_parser("filing", help="13F-style filing for a date")
    p.add_argument("date", nargs="?", help="YYYY-MM-DD (default: today)")

    # trades
    p = sub.add_parser("trades", help="Detected trades")
    p.add_argument("--period", default="ALL", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--security-id", help="Filter by security ID")

    # performance
    p = sub.add_parser("performance", help="Performance metrics")
    p.add_argument("--period", default="1Y", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--account-id", help="Filter by account ID")

    # returns
    p = sub.add_parser("returns", help="Daily or cumulative returns")
    p.add_argument("--period", default="1Y", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--account-id", help="Filter by account ID")
    p.add_argument("--cumulative", action="store_true", help="Cumulative returns")

    # comparison
    p = sub.add_parser("comparison", help="Portfolio vs S&P 500")
    p.add_argument("--period", default="1Y", help="1D|1W|1M|3M|6M|YTD|1Y|ALL")
    p.add_argument("--account-id", help="Filter by account ID")

    # periods
    p = sub.add_parser("periods", help="Performance across all periods")
    p.add_argument("--account-id", help="Filter by account ID")

    # sync-status
    sub.add_parser("sync-status", help="Show last sync info and data ranges")

    # sync
    sub.add_parser("sync", help="Trigger a data sync")

    # auth onboarding
    p = sub.add_parser("auth", help="Email-link onboarding and auth status")
    auth_sub = p.add_subparsers(dest="auth_command", required=True)

    p_start = auth_sub.add_parser("start", help="Send magic link to email")
    p_start.add_argument("--email", required=True, help="Email for Copilot login")
    p_start.add_argument("--app-check-token", help="Firebase App Check token from web request headers")
    p_start.add_argument("--gmpid", help="Firebase GMPID override")

    p_complete = auth_sub.add_parser("complete", help="Exchange magic link for tokens and sync")
    p_complete.add_argument("--email", required=True, help="Email used for magic-link sign in")
    p_complete.add_argument("--magic-link", required=True, help="Magic link copied from email")
    p_complete.add_argument("--app-check-token", help="Firebase App Check token from web request headers")
    p_complete.add_argument("--gmpid", help="Firebase GMPID override")

    auth_sub.add_parser("status", help="Show local auth/token status")

    args = parser.parse_args()

    if args.command == "auth":
        auth_dispatch = {
            "start": cmd_auth_start,
            "complete": cmd_auth_complete,
            "status": cmd_auth_status,
        }
        result = auth_dispatch[args.auth_command](args)
        if args.json and result:
            print(json.dumps(result, indent=2))
        return

    dispatch = {
        "accounts": cmd_accounts,
        "holdings": cmd_holdings,
        "balance": cmd_balance,
        "allocation": cmd_allocation,
        "allocation-history": cmd_allocation_history,
        "filing": cmd_filing,
        "trades": cmd_trades,
        "performance": cmd_performance,
        "returns": cmd_returns,
        "comparison": cmd_comparison,
        "periods": cmd_periods,
        "sync-status": cmd_sync_status,
        "sync": cmd_sync,
    }

    result = dispatch[args.command](args)
    if args.json and result:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
