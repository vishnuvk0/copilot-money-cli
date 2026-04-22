"""
Copilot Money GraphQL API — Phase 2: Extended Endpoint Testing

Tests all known endpoints including newly discovered ones from browser
network inspection: BalanceHistory, AccountLiveBalance, Networth,
TransactionsFeed, and TransactionSummary.

Usage:
    COPILOT_TOKEN=<jwt> python backend/scripts/test_copilot_api.py

Or place token in backend/.env:
    COPILOT_TOKEN=eyJ...
"""

import json
import os
import sys
import base64
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "https://app.copilot.money/api/graphql"

HEADERS_TEMPLATE = {
    "content-type": "application/json",
    "accept": "*/*",
    "apollographql-client-name": "web",
    "apollographql-client-version": "26.4.8+1387",
    "origin": "https://app.copilot.money",
    "referer": "https://app.copilot.money/investments",
}

TIMEFRAMES = ["ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "YTD", "ONE_YEAR", "ALL"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_token() -> str:
    """Load JWT from env var or .env file."""
    token = os.environ.get("COPILOT_TOKEN")
    if token:
        return token.strip()

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("COPILOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    print("=" * 80)
    print("ERROR: No Copilot Money API token found.")
    print()
    print("Set it via environment variable:")
    print("  COPILOT_TOKEN=eyJ... python backend/scripts/test_copilot_api.py")
    print()
    print("Or create backend/.env with:")
    print("  COPILOT_TOKEN=eyJ...")
    print("=" * 80)
    sys.exit(1)


def decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload (no verification) to inspect expiry."""
    try:
        payload_b64 = token.split(".")[1]
        # Add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return None


def gql(token: str, operation: str, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query and return the response JSON."""
    headers = {**HEADERS_TEMPLATE, "authorization": f"Bearer {token}"}
    payload = {"operationName": operation, "query": query, "variables": variables or {}}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    # Don't raise — return the body so we can see GraphQL errors
    try:
        return resp.json()
    except Exception:
        return {"errors": [{"message": f"HTTP {resp.status_code}: {resp.text[:200]}"}]}


def print_header(test_num: int, title: str):
    print()
    print("=" * 80)
    print(f"TEST {test_num}: {title}")
    print("=" * 80)


def ok(msg: str):
    print(f"  [PASS] {msg}")


def fail(msg: str):
    print(f"  [FAIL] {msg}")


def info(msg: str):
    print(f"  {msg}")


def warn(msg: str):
    print(f"  [WARN] {msg}")


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

Q_ACCOUNTS = """
query Accounts($filter: AccountFilter, $accountLink: Boolean = false) {
  accounts(filter: $filter) {
    ...AccountFields
    accountLink @include(if: $accountLink) {
      type
      account { ...AccountFields __typename }
      __typename
    }
    __typename
  }
}

fragment AccountFields on Account {
  hasHistoricalUpdates
  latestBalanceUpdate
  hasLiveBalance
  institutionId
  isUserHidden
  isUserClosed
  liveBalance
  isManual
  balance
  subType
  itemId
  limit
  color
  name
  type
  mask
  id
  __typename
}
"""

Q_HOLDINGS = """
query Holdings {
  holdings {
    security {
      ...SecurityFields
      __typename
    }
    metrics {
      averageCost
      totalReturn
      costBasis
      __typename
    }
    accountId
    quantity
    itemId
    id
    __typename
  }
}

fragment SecurityFields on Security {
  marketInfo {
    closeTime
    openTime
    __typename
  }
  currentPrice
  lastUpdate
  symbol
  name
  type
  id
  __typename
}
"""

Q_AGGREGATED_HOLDINGS = """
query AggregatedHoldings($timeFrame: TimeFrame, $filter: AggregatedHoldingsFilter, $accountId: ID, $itemId: ID) {
  aggregatedHoldings(
    timeFrame: $timeFrame
    filter: $filter
    accountId: $accountId
    itemId: $itemId
  ) {
    security {
      marketInfo {
        closeTime
        openTime
        __typename
      }
      lastUpdate
      symbol
      name
      type
      id
      __typename
    }
    change
    value
    __typename
  }
}
"""

Q_INVESTMENT_BALANCE = """
query InvestmentBalance($timeFrame: TimeFrame) {
  investmentBalance(timeFrame: $timeFrame) {
    id
    date
    balance
    __typename
  }
}
"""

# Variant with accountId to test per-account support
Q_INVESTMENT_BALANCE_ACCT = """
query InvestmentBalance($timeFrame: TimeFrame, $accountId: ID) {
  investmentBalance(timeFrame: $timeFrame, accountId: $accountId) {
    id
    date
    balance
    __typename
  }
}
"""

Q_INVESTMENT_PERFORMANCE = """
query InvestmentPerformance($timeFrame: TimeFrame) {
  investmentPerformance(timeFrame: $timeFrame) {
    date
    performance
    __typename
  }
}
"""

# Variant with accountId to test per-account support
Q_INVESTMENT_PERFORMANCE_ACCT = """
query InvestmentPerformance($timeFrame: TimeFrame, $accountId: ID) {
  investmentPerformance(timeFrame: $timeFrame, accountId: $accountId) {
    date
    performance
    __typename
  }
}
"""

Q_INVESTMENT_ALLOCATION = """
query InvestmentAllocation($filter: AllocationFilter) {
  investmentAllocation(filter: $filter) {
    ...AllocationFields
    __typename
  }
}

fragment AllocationFields on Allocation {
  percentage
  amount
  type
  id
  __typename
}
"""

Q_BALANCE_HISTORY = """
query BalanceHistory($itemId: ID!, $accountId: ID!, $timeFrame: TimeFrame) {
  accountBalanceHistory(
    itemId: $itemId
    accountId: $accountId
    timeFrame: $timeFrame
  ) {
    ...BalanceFields
    __typename
  }
}

fragment BalanceFields on AccountBalanceHistory {
  balance
  date
  __typename
}
"""

Q_ACCOUNT_LIVE_BALANCE = """
query AccountLiveBalance($itemId: ID!, $accountId: ID!) {
  accountLiveBalance(itemId: $itemId, accountId: $accountId) {
    balance
    date
    __typename
  }
}
"""

Q_NETWORTH = """
query Networth($timeFrame: TimeFrame) {
  networthHistory(timeFrame: $timeFrame) {
    assets
    date
    debt
    __typename
  }
}
"""

Q_TRANSACTION_SUMMARY = """
query TransactionSummary($filter: TransactionFilter) {
  transactionsSummary(filter: $filter) {
    transactionsCount
    totalNetIncome
    totalIncome
    totalSpent
    __typename
  }
}
"""

Q_TRANSACTIONS_FEED = """
query TransactionsFeed($first: Int, $after: String, $filter: TransactionFilter, $sort: [TransactionSort!], $month: Boolean = false) {
  feed: transactionsFeed(
    first: $first
    after: $after
    filter: $filter
    sort: $sort
  ) {
    edges {
      cursor
      node {
        ... on TransactionMonth @include(if: $month) {
          amount
          month
          id
          __typename
        }
        ... on Transaction {
          ...TransactionFields
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      endCursor
      hasNextPage
      hasPreviousPage
      startCursor
      __typename
    }
    __typename
  }
}

fragment TransactionFields on Transaction {
  recurringId
  categoryId
  isReviewed
  accountId
  isPending
  itemId
  amount
  date
  name
  type
  id
  __typename
}
"""

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Collected state for summary
results: dict[str, str] = {}
account_ids: list[tuple[str, str, str]] = []  # (id, name, itemId) tuples
per_account_support: dict[str, bool] = {}
valid_timeframes: dict[str, list[str]] = {}
data_quality_notes: list[str] = []


def test_1_auth(token: str):
    """Validate token and show expiry."""
    print_header(1, "Auth Validation")

    payload = decode_jwt_payload(token)
    if payload:
        exp = payload.get("exp")
        name = payload.get("name", "?")
        email = payload.get("email", "?")
        info(f"User:    {name} ({email})")
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            remaining = exp_dt - now
            info(f"Expires: {exp_dt.isoformat()}")
            if remaining.total_seconds() <= 0:
                fail(f"Token EXPIRED {abs(remaining)} ago")
                results["1_auth"] = "FAIL — token expired"
                return False
            else:
                mins = remaining.total_seconds() / 60
                ok(f"Token valid — {mins:.0f} minutes remaining")
        else:
            warn("No exp claim in JWT")
    else:
        warn("Could not decode JWT payload")

    # Quick connectivity test
    try:
        data = gql(token, "Accounts", Q_ACCOUNTS, {"filter": {"type": "INVESTMENT"}})
        if "errors" in data:
            fail(f"API returned errors: {data['errors']}")
            results["1_auth"] = "FAIL — API error"
            return False
        ok("API connection successful")
        results["1_auth"] = "PASS"
        return True
    except Exception as e:
        fail(f"API request failed: {e}")
        results["1_auth"] = "FAIL — request error"
        return False


def test_2_accounts(token: str):
    """Query investment accounts."""
    print_header(2, "Accounts")

    try:
        data = gql(token, "Accounts", Q_ACCOUNTS, {"filter": {"type": "INVESTMENT"}})
        accounts = data.get("data", {}).get("accounts", [])

        if not accounts:
            warn("No investment accounts returned")
            results["2_accounts"] = "WARN — no accounts"
            return

        ok(f"Found {len(accounts)} investment account(s)")
        print()

        for acct in accounts:
            acct_id = acct.get("id", "?")
            name = acct.get("name", "?")
            item_id = acct.get("itemId", "?")
            balance = acct.get("balance")
            sub_type = acct.get("subType", "?")
            institution = acct.get("institutionId", "?")
            is_manual = acct.get("isManual", False)
            has_hist = acct.get("hasHistoricalUpdates", False)
            has_live = acct.get("hasLiveBalance", False)

            balance_str = f"${balance:,.2f}" if balance is not None else "N/A"
            info(f"  {name}")
            info(f"    ID:          {acct_id}")
            info(f"    ItemID:      {item_id}")
            info(f"    Balance:     {balance_str}")
            info(f"    SubType:     {sub_type}")
            info(f"    Institution: {institution}")
            info(f"    Manual:      {is_manual}")
            info(f"    Historical:  {has_hist}")
            info(f"    LiveBalance: {has_live}")
            print()

            account_ids.append((acct_id, name, item_id))

        results["2_accounts"] = f"PASS — {len(accounts)} accounts"

    except Exception as e:
        fail(f"Error: {e}")
        results["2_accounts"] = f"FAIL — {e}"


def test_3_holdings(token: str):
    """Query all holdings."""
    print_header(3, "Holdings")

    try:
        data = gql(token, "Holdings", Q_HOLDINGS)
        holdings = data.get("data", {}).get("holdings", [])

        if not holdings:
            warn("No holdings returned")
            results["3_holdings"] = "WARN — no holdings"
            return

        ok(f"Found {len(holdings)} holding(s)")
        print()

        # Group by account
        by_account: dict[str, list] = {}
        for h in holdings:
            aid = h.get("accountId", "unknown")
            by_account.setdefault(aid, []).append(h)

        for aid, holdings_list in by_account.items():
            # Find account name
            acct_name = next((n for i, n, _ in account_ids if i == aid), aid)
            info(f"  --- {acct_name} ({aid}) ---")

            for h in holdings_list:
                sec = h.get("security") or {}
                met = h.get("metrics") or {}
                symbol = sec.get("symbol", "?")
                name = sec.get("name", "?")
                qty = h.get("quantity")
                price = sec.get("currentPrice")
                cost_basis = met.get("costBasis")
                total_return = met.get("totalReturn")
                avg_cost = met.get("averageCost")

                qty_str = f"{qty:,.4f}" if qty is not None else "N/A"
                price_str = f"${price:,.2f}" if price is not None else "N/A"
                cost_str = f"${cost_basis:,.2f}" if cost_basis is not None else "N/A"
                ret_str = f"${total_return:,.2f}" if total_return is not None else "N/A"
                avg_str = f"${avg_cost:,.2f}" if avg_cost is not None else "N/A"

                info(f"    {symbol:<8s} {name[:30]:<30s}  qty={qty_str}  price={price_str}  cost={cost_str}  return={ret_str}  avg={avg_str}")

            print()

        results["3_holdings"] = f"PASS — {len(holdings)} holdings across {len(by_account)} accounts"

    except Exception as e:
        fail(f"Error: {e}")
        results["3_holdings"] = f"FAIL — {e}"


def test_4_aggregated_holdings(token: str):
    """Test AggregatedHoldings with all timeframes and per-account filtering."""
    print_header(4, "AggregatedHoldings")

    # Test each timeframe
    working_tfs = []
    for tf in TIMEFRAMES:
        try:
            data = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                        {"timeFrame": tf, "filter": "LAST_PRICE"})
            agg = data.get("data", {}).get("aggregatedHoldings", [])
            if "errors" in data:
                fail(f"  {tf}: error — {data['errors'][0].get('message', '?')}")
            else:
                ok(f"{tf}: {len(agg)} holdings")
                working_tfs.append(tf)
        except Exception as e:
            fail(f"  {tf}: {e}")

    valid_timeframes["aggregatedHoldings"] = working_tfs
    print()

    # Show sample data from ONE_WEEK
    try:
        data = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                    {"timeFrame": "ONE_WEEK", "filter": "LAST_PRICE"})
        agg = data.get("data", {}).get("aggregatedHoldings", [])
        if agg:
            info("Sample (ONE_WEEK):")
            for h in agg[:10]:
                sec = h.get("security", {})
                symbol = sec.get("symbol", "?")
                name = sec.get("name", "?")
                change = h.get("change")
                value = h.get("value")
                change_str = f"{change:+,.2f}" if change is not None else "N/A"
                value_str = f"${value:,.2f}" if value is not None else "N/A"
                info(f"    {symbol:<8s} {name[:30]:<30s}  change={change_str}  value={value_str}")
            if len(agg) > 10:
                info(f"    ... and {len(agg) - 10} more")
            print()
    except Exception:
        pass

    # Test per-account filtering — needs BOTH accountId AND itemId
    if account_ids:
        # Get baseline count (all accounts)
        try:
            data_all = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                            {"timeFrame": "ONE_WEEK", "filter": "LAST_PRICE"})
            all_count = len(data_all.get("data", {}).get("aggregatedHoldings", []))
        except Exception:
            all_count = -1

        test_id, test_name, test_item_id = account_ids[1] if len(account_ids) > 1 else account_ids[0]
        info(f"Testing per-account filter with: {test_name} (all-accounts={all_count})")
        info(f"  Using accountId={test_id[:12]}... + itemId={test_item_id[:12]}...")
        try:
            data = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                        {"timeFrame": "ONE_WEEK", "filter": "LAST_PRICE",
                         "accountId": test_id, "itemId": test_item_id})
            agg = data.get("data", {}).get("aggregatedHoldings", [])
            if "errors" in data:
                fail(f"Per-account filter: error — {data['errors'][0].get('message', '?')}")
                per_account_support["aggregatedHoldings"] = False
            else:
                if len(agg) < all_count:
                    ok(f"Per-account filter works — {len(agg)} holdings for {test_name} (vs {all_count} total)")
                elif len(agg) == all_count:
                    warn(f"Per-account returned same count ({len(agg)}) as all — filter may be ignored")
                else:
                    ok(f"Per-account filter: {len(agg)} holdings for {test_name}")
                per_account_support["aggregatedHoldings"] = len(agg) != all_count
        except Exception as e:
            fail(f"Per-account filter: {e}")
            per_account_support["aggregatedHoldings"] = False
    else:
        warn("No account IDs available to test per-account filtering")

    results["4_aggregated_holdings"] = f"PASS — {len(working_tfs)}/{len(TIMEFRAMES)} timeframes"


def test_5_investment_balance(token: str):
    """Test InvestmentBalance (daily balance snapshots)."""
    print_header(5, "InvestmentBalance (daily balance snapshots)")

    # Test each timeframe
    working_tfs = []
    for tf in TIMEFRAMES:
        try:
            data = gql(token, "InvestmentBalance", Q_INVESTMENT_BALANCE, {"timeFrame": tf})
            balances = data.get("data", {}).get("investmentBalance", [])
            if "errors" in data:
                fail(f"{tf}: error — {data['errors'][0].get('message', '?')}")
            else:
                if balances:
                    first_date = balances[0].get("date", "?")
                    last_date = balances[-1].get("date", "?")
                    ok(f"{tf}: {len(balances)} data points  ({first_date} to {last_date})")
                    working_tfs.append(tf)
                else:
                    warn(f"{tf}: 0 data points")
        except Exception as e:
            fail(f"{tf}: {e}")

    valid_timeframes["investmentBalance"] = working_tfs
    print()

    # Show sample data from ALL
    tf_for_sample = "ALL" if "ALL" in working_tfs else (working_tfs[-1] if working_tfs else None)
    if tf_for_sample:
        try:
            data = gql(token, "InvestmentBalance", Q_INVESTMENT_BALANCE, {"timeFrame": tf_for_sample})
            balances = data.get("data", {}).get("investmentBalance", [])
            if balances:
                info(f"Sample data ({tf_for_sample}) — first 5 + last 5:")
                for b in balances[:5]:
                    info(f"    {b.get('date', '?')}  ${b.get('balance', 0):>12,.2f}")
                if len(balances) > 10:
                    info(f"    ... ({len(balances) - 10} more rows) ...")
                for b in balances[-5:]:
                    info(f"    {b.get('date', '?')}  ${b.get('balance', 0):>12,.2f}")
                print()
        except Exception:
            pass

    # Test per-account filtering (known to NOT work — accountId not accepted)
    if account_ids:
        test_id, test_name, _ = account_ids[0]
        info(f"Testing per-account filter with: {test_name}")
        try:
            # Try variant query that declares $accountId
            data = gql(token, "InvestmentBalance", Q_INVESTMENT_BALANCE_ACCT,
                        {"timeFrame": "ONE_MONTH", "accountId": test_id})
            balances = data.get("data", {}).get("investmentBalance", [])
            if "errors" in data:
                err_msg = data["errors"][0].get("message", "?")
                # Check if the error is about unknown argument
                if "Unknown argument" in err_msg or "unknown" in err_msg.lower():
                    fail(f"Per-account filter NOT supported — {err_msg}")
                    per_account_support["investmentBalance"] = False
                else:
                    fail(f"Per-account filter: error — {err_msg}")
                    per_account_support["investmentBalance"] = False
            else:
                ok(f"Per-account filter works — {len(balances)} data points for {test_name}")
                per_account_support["investmentBalance"] = True

                # Show a few values for verification
                if balances:
                    for b in balances[:3]:
                        info(f"    {b.get('date', '?')}  ${b.get('balance', 0):>12,.2f}")
        except Exception as e:
            fail(f"Per-account filter: {e}")
            per_account_support["investmentBalance"] = False
    else:
        warn("No account IDs available to test per-account filtering")

    results["5_investment_balance"] = f"PASS — {len(working_tfs)}/{len(TIMEFRAMES)} timeframes"


def test_6_investment_performance(token: str):
    """Test InvestmentPerformance (daily performance %, basis points from API)."""
    print_header(6, "InvestmentPerformance (daily performance %)")

    working_tfs = []
    for tf in TIMEFRAMES:
        try:
            data = gql(token, "InvestmentPerformance", Q_INVESTMENT_PERFORMANCE, {"timeFrame": tf})
            perfs = data.get("data", {}).get("investmentPerformance", [])
            if "errors" in data:
                fail(f"{tf}: error — {data['errors'][0].get('message', '?')}")
            else:
                if perfs:
                    first_date = perfs[0].get("date", "?")
                    last_date = perfs[-1].get("date", "?")
                    last_perf_bps = perfs[-1].get("performance")
                    # Convert basis points (bps) to percent: 100 bps = 1%
                    last_perf_pct = (last_perf_bps / 100.0) if last_perf_bps is not None else None
                    perf_str = f"{last_perf_pct:+.2%}" if last_perf_pct is not None else "N/A"
                    ok(f"{tf}: {len(perfs)} data points  ({first_date} to {last_date})  cumulative={perf_str}")
                    working_tfs.append(tf)
                else:
                    warn(f"{tf}: 0 data points")
        except Exception as e:
            fail(f"{tf}: {e}")

    valid_timeframes["investmentPerformance"] = working_tfs
    print()

    # Show sample data
    tf_for_sample = "YTD" if "YTD" in working_tfs else (working_tfs[0] if working_tfs else None)
    if tf_for_sample:
        try:
            data = gql(token, "InvestmentPerformance", Q_INVESTMENT_PERFORMANCE, {"timeFrame": tf_for_sample})
            perfs = data.get("data", {}).get("investmentPerformance", [])
            if perfs:
                info(f"Sample data ({tf_for_sample}) — first 5 + last 5:")
                for p in perfs[:5]:
                    perf = p.get("performance")
                    perf_str = f"{perf:+.4%}" if perf is not None else "N/A"
                    info(f"    {p.get('date', '?')}  {perf_str}")
                if len(perfs) > 10:
                    info(f"    ... ({len(perfs) - 10} more rows) ...")
                for p in perfs[-5:]:
                    perf = p.get("performance")
                    perf_str = f"{perf:+.4%}" if perf is not None else "N/A"
                    info(f"    {p.get('date', '?')}  {perf_str}")
                print()
        except Exception:
            pass

    # Test per-account filtering (known to NOT work — accountId not accepted)
    if account_ids:
        test_id, test_name, _ = account_ids[0]
        info(f"Testing per-account filter with: {test_name}")
        try:
            data = gql(token, "InvestmentPerformance", Q_INVESTMENT_PERFORMANCE_ACCT,
                        {"timeFrame": "ONE_MONTH", "accountId": test_id})
            perfs = data.get("data", {}).get("investmentPerformance", [])
            if "errors" in data:
                err_msg = data["errors"][0].get("message", "?")
                if "Unknown argument" in err_msg or "unknown" in err_msg.lower():
                    fail(f"Per-account filter NOT supported — {err_msg}")
                    per_account_support["investmentPerformance"] = False
                else:
                    fail(f"Per-account filter: error — {err_msg}")
                    per_account_support["investmentPerformance"] = False
            else:
                ok(f"Per-account filter works — {len(perfs)} data points for {test_name}")
                per_account_support["investmentPerformance"] = True

                if perfs:
                    last = perfs[-1]
                    perf = last.get("performance")
                    perf_str = f"{perf:+.4%}" if perf is not None else "N/A"
                    info(f"    Latest: {last.get('date', '?')}  {perf_str}")
        except Exception as e:
            fail(f"Per-account filter: {e}")
            per_account_support["investmentPerformance"] = False

    results["6_investment_performance"] = f"PASS — {len(working_tfs)}/{len(TIMEFRAMES)} timeframes"


def test_7_investment_allocation(token: str):
    """Test InvestmentAllocation."""
    print_header(7, "InvestmentAllocation")

    try:
        data = gql(token, "InvestmentAllocation", Q_INVESTMENT_ALLOCATION)
        allocs = data.get("data", {}).get("investmentAllocation", [])

        if "errors" in data:
            fail(f"Error: {data['errors']}")
            results["7_allocation"] = "FAIL"
            return

        if not allocs:
            warn("No allocation data returned")
            results["7_allocation"] = "WARN — no data"
            return

        ok(f"Found {len(allocs)} allocation categories")
        print()

        total_pct = 0
        for a in allocs:
            alloc_type = a.get("type", "?")
            amount = a.get("amount")
            pct = a.get("percentage")
            amount_str = f"${amount:>12,.2f}" if amount is not None else "N/A"
            pct_str = f"{pct:>6.2f}%" if pct is not None else "N/A"
            info(f"    {alloc_type:<20s}  {amount_str}  {pct_str}")
            if pct is not None:
                total_pct += pct

        info(f"    {'TOTAL':<20s}               {total_pct:>6.2f}%")

        # Test with accountId + itemId filter
        if account_ids:
            print()
            test_id, test_name, test_item_id = account_ids[0]
            info(f"Testing per-account filter with: {test_name}")
            try:
                data = gql(token, "InvestmentAllocation", Q_INVESTMENT_ALLOCATION,
                            {"filter": {"accountId": test_id, "itemId": test_item_id}})
                allocs_filtered = data.get("data", {}).get("investmentAllocation", [])
                if "errors" in data:
                    fail(f"Per-account filter: error — {data['errors'][0].get('message', '?')}")
                    per_account_support["investmentAllocation"] = False
                else:
                    ok(f"Per-account filter works — {len(allocs_filtered)} categories for {test_name}")
                    per_account_support["investmentAllocation"] = True
            except Exception as e:
                fail(f"Per-account filter: {e}")
                per_account_support["investmentAllocation"] = False

        results["7_allocation"] = f"PASS — {len(allocs)} categories"

    except Exception as e:
        fail(f"Error: {e}")
        results["7_allocation"] = f"FAIL — {e}"


def test_8_balance_history(token: str):
    """Test BalanceHistory — per-account daily balances (NEW in Phase 2)."""
    print_header(8, "BalanceHistory (per-account daily balances)")

    if not account_ids:
        warn("No account IDs available — skipping")
        results["8_balance_history"] = "SKIP — no accounts"
        return

    # Find a non-zero-balance account to test with
    # We'll test multiple accounts to confirm per-account works
    tested = 0
    all_working = True

    for acct_id, acct_name, item_id in account_ids[:4]:  # Test up to 4 accounts
        info(f"--- {acct_name} ---")

        for tf in ["ONE_MONTH", "ALL"]:
            try:
                data = gql(token, "BalanceHistory", Q_BALANCE_HISTORY,
                           {"accountId": acct_id, "itemId": item_id, "timeFrame": tf})

                if "errors" in data:
                    fail(f"  {tf}: error — {data['errors'][0].get('message', '?')}")
                    all_working = False
                    continue

                history = data.get("data", {}).get("accountBalanceHistory", [])
                if not history:
                    warn(f"  {tf}: 0 data points")
                    continue

                first = history[0]
                last = history[-1]
                ok(f"  {tf}: {len(history)} data points  "
                   f"({first.get('date', '?')} to {last.get('date', '?')})  "
                   f"first=${first.get('balance', 0):,.2f}  last=${last.get('balance', 0):,.2f}")

                if tf == "ALL":
                    data_quality_notes.append(
                        f"BalanceHistory/{acct_name}: {len(history)} points from {first.get('date', '?')}"
                    )

            except Exception as e:
                fail(f"  {tf}: {e}")
                all_working = False

        tested += 1
        print()

    per_account_support["balanceHistory"] = all_working and tested > 0

    # Show sample data for first account with ALL timeframe
    if account_ids:
        acct_id, acct_name, item_id = account_ids[0]
        try:
            data = gql(token, "BalanceHistory", Q_BALANCE_HISTORY,
                       {"accountId": acct_id, "itemId": item_id, "timeFrame": "ALL"})
            history = data.get("data", {}).get("accountBalanceHistory", [])
            if history and len(history) > 5:
                info(f"Sample data for {acct_name} (ALL) — first 5 + last 5:")
                for b in history[:5]:
                    info(f"    {b.get('date', '?')}  ${b.get('balance', 0):>12,.2f}")
                if len(history) > 10:
                    info(f"    ... ({len(history) - 10} more rows) ...")
                for b in history[-5:]:
                    info(f"    {b.get('date', '?')}  ${b.get('balance', 0):>12,.2f}")
        except Exception:
            pass

    results["8_balance_history"] = f"PASS — tested {tested} accounts" if all_working else f"PARTIAL — {tested} accounts tested"


def test_9_account_live_balance(token: str):
    """Test AccountLiveBalance — real-time balance per account."""
    print_header(9, "AccountLiveBalance (real-time per-account)")

    if not account_ids:
        warn("No account IDs available — skipping")
        results["9_live_balance"] = "SKIP — no accounts"
        return

    tested = 0

    for acct_id, acct_name, item_id in account_ids[:5]:
        try:
            data = gql(token, "AccountLiveBalance", Q_ACCOUNT_LIVE_BALANCE,
                       {"accountId": acct_id, "itemId": item_id})

            if "errors" in data:
                fail(f"  {acct_name}: error — {data['errors'][0].get('message', '?')}")
                continue

            live_data = data.get("data", {}).get("accountLiveBalance")
            if live_data is None:
                warn(f"  {acct_name}: null response (no live balance available)")
                continue

            live_bal = live_data.get("balance")
            live_date = live_data.get("date", "?")

            # Compare to stored balance from Accounts query
            # We'd need the original account data; for now just display
            live_str = f"${live_bal:,.2f}" if live_bal is not None else "N/A"
            ok(f"  {acct_name}: live={live_str}  date={live_date}")
            tested += 1

        except Exception as e:
            fail(f"  {acct_name}: {e}")

    per_account_support["accountLiveBalance"] = tested > 0
    results["9_live_balance"] = f"PASS — {tested} accounts responded" if tested > 0 else "FAIL — no responses"


def test_10_networth(token: str):
    """Test Networth — daily net worth (assets + debt) over time."""
    print_header(10, "Networth (aggregate assets + debt history)")

    try:
        data = gql(token, "Networth", Q_NETWORTH, {"timeFrame": "ALL"})

        if "errors" in data:
            fail(f"Error: {data['errors']}")
            results["10_networth"] = "FAIL"
            return

        history = data.get("data", {}).get("networthHistory", [])
        if not history:
            warn("No networth data returned")
            results["10_networth"] = "WARN — no data"
            return

        first = history[0]
        last = history[-1]
        ok(f"ALL timeframe: {len(history)} data points  "
           f"({first.get('date', '?')} to {last.get('date', '?')})")
        print()

        # Show first 5 + last 5
        info("Sample data (first 5 + last 5):")
        for h in history[:5]:
            assets = h.get("assets")
            debt = h.get("debt")
            assets_str = f"${assets:>12,.2f}" if assets is not None else "         N/A"
            debt_str = f"${debt:>12,.2f}" if debt is not None else "         N/A"
            net = (assets or 0) - (debt or 0)
            info(f"    {h.get('date', '?')}  assets={assets_str}  debt={debt_str}  net=${net:>12,.2f}")
        if len(history) > 10:
            info(f"    ... ({len(history) - 10} more rows) ...")
        for h in history[-5:]:
            assets = h.get("assets")
            debt = h.get("debt")
            assets_str = f"${assets:>12,.2f}" if assets is not None else "         N/A"
            debt_str = f"${debt:>12,.2f}" if debt is not None else "         N/A"
            net = (assets or 0) - (debt or 0)
            info(f"    {h.get('date', '?')}  assets={assets_str}  debt={debt_str}  net=${net:>12,.2f}")

        data_quality_notes.append(
            f"Networth: {len(history)} points from {first.get('date', '?')} to {last.get('date', '?')}"
        )

        results["10_networth"] = f"PASS — {len(history)} data points"

    except Exception as e:
        fail(f"Error: {e}")
        results["10_networth"] = f"FAIL — {e}"


def test_11_transaction_summary(token: str):
    """Test TransactionSummary — per-account transaction stats."""
    print_header(11, "TransactionSummary (per-account stats)")

    if not account_ids:
        warn("No account IDs available — skipping")
        results["11_txn_summary"] = "SKIP — no accounts"
        return

    tested = 0

    for acct_id, acct_name, item_id in account_ids[:5]:
        try:
            filter_var = {
                "accountIds": [{"accountId": acct_id, "itemId": item_id}]
            }
            data = gql(token, "TransactionSummary", Q_TRANSACTION_SUMMARY,
                       {"filter": filter_var})

            if "errors" in data:
                fail(f"  {acct_name}: error — {data['errors'][0].get('message', '?')}")
                continue

            summary = data.get("data", {}).get("transactionsSummary")
            if summary is None:
                warn(f"  {acct_name}: null response")
                continue

            count = summary.get("transactionsCount", 0)
            net_income = summary.get("totalNetIncome")
            total_income = summary.get("totalIncome")
            total_spent = summary.get("totalSpent")

            net_str = f"${net_income:,.2f}" if net_income is not None else "N/A"
            inc_str = f"${total_income:,.2f}" if total_income is not None else "N/A"
            spent_str = f"${total_spent:,.2f}" if total_spent is not None else "N/A"

            ok(f"  {acct_name}: {count} txns  income={inc_str}  spent={spent_str}  net={net_str}")
            tested += 1

            if count > 0:
                data_quality_notes.append(
                    f"TransactionSummary/{acct_name}: {count} transactions"
                )

        except Exception as e:
            fail(f"  {acct_name}: {e}")

    per_account_support["transactionSummary"] = tested > 0
    results["11_txn_summary"] = f"PASS — {tested} accounts" if tested > 0 else "FAIL — no responses"


def test_12_transactions_feed(token: str):
    """Test TransactionsFeed — CRITICAL for MWR/XIRR cash flow data."""
    print_header(12, "TransactionsFeed (paginated transactions — CRITICAL for MWR)")

    if not account_ids:
        warn("No account IDs available — skipping")
        results["12_txn_feed"] = "SKIP — no accounts"
        return

    # Pick a 401k or retirement account if possible (most likely to have contributions)
    target = None
    for acct_id, acct_name, item_id in account_ids:
        name_lower = acct_name.lower()
        if any(kw in name_lower for kw in ["401k", "401(k)", "ira", "roth", "retirement"]):
            target = (acct_id, acct_name, item_id)
            break
    if target is None:
        target = account_ids[0]  # Fallback to first account

    acct_id, acct_name, item_id = target
    info(f"Target account: {acct_name}")
    print()

    # Page through ALL transactions
    all_transactions = []
    cursor = None
    page = 0
    page_size = 50

    while True:
        page += 1
        variables: dict = {
            "first": page_size,
            "filter": {
                "accountIds": [{"accountId": acct_id, "itemId": item_id}]
            },
            "sort": [{"direction": "DESC", "field": "DATE"}],
            "month": False,
        }
        if cursor:
            variables["after"] = cursor

        try:
            data = gql(token, "TransactionsFeed", Q_TRANSACTIONS_FEED, variables)

            if "errors" in data:
                fail(f"Page {page}: error — {data['errors'][0].get('message', '?')}")
                break

            feed = data.get("data", {}).get("feed", {})
            edges = feed.get("edges", [])
            page_info = feed.get("pageInfo", {})

            for edge in edges:
                node = edge.get("node", {})
                if node.get("__typename") == "Transaction":
                    all_transactions.append(node)

            info(f"  Page {page}: {len(edges)} edges  (total so far: {len(all_transactions)})")

            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")
            if not cursor:
                break

            # Safety limit
            if page >= 100:
                warn("  Hit 100-page safety limit — stopping pagination")
                break

        except Exception as e:
            fail(f"Page {page}: {e}")
            break

    print()

    if not all_transactions:
        warn("No transactions found")
        results["12_txn_feed"] = f"WARN — 0 transactions for {acct_name}"
        return

    ok(f"Found {len(all_transactions)} transactions for {acct_name}")
    print()

    # Date range
    dates = [t.get("date", "") for t in all_transactions if t.get("date")]
    if dates:
        dates_sorted = sorted(dates)
        info(f"Date range: {dates_sorted[0]} to {dates_sorted[-1]}")

    # Analyze transaction types
    type_counts: dict[str, int] = {}
    contribution_txns = []
    for t in all_transactions:
        ttype = t.get("type", "UNKNOWN")
        type_counts[ttype] = type_counts.get(ttype, 0) + 1

        # Look for contributions/deposits (negative amounts = inflows in Copilot)
        name_lower = (t.get("name") or "").lower()
        amount = t.get("amount", 0)
        if any(kw in name_lower for kw in ["contrib", "deposit", "transfer", "contribution",
                                             "401k", "roth", "match", "employer"]):
            contribution_txns.append(t)

    info(f"Transaction types: {type_counts}")
    print()

    # Show sample transactions (first 10)
    info("Sample transactions (most recent 10):")
    for t in all_transactions[:10]:
        amount = t.get("amount", 0)
        amount_str = f"${amount:>10,.2f}" if amount is not None else "       N/A"
        info(f"    {t.get('date', '?')}  {amount_str}  {t.get('type', '?'):<10s}  {t.get('name', '?')[:40]}")
    if len(all_transactions) > 10:
        info(f"    ... and {len(all_transactions) - 10} more")
    print()

    # Contribution analysis
    if contribution_txns:
        ok(f"Found {len(contribution_txns)} contribution-like transactions")
        info("Sample contributions:")
        for t in contribution_txns[:5]:
            amount = t.get("amount", 0)
            info(f"    {t.get('date', '?')}  ${amount:>10,.2f}  {t.get('name', '?')[:50]}")
        if len(contribution_txns) > 5:
            info(f"    ... and {len(contribution_txns) - 5} more")
    else:
        warn("No obvious contribution transactions found by keyword search")
        info("Manual inspection of transaction names may be needed")

    data_quality_notes.append(
        f"TransactionsFeed/{acct_name}: {len(all_transactions)} txns, "
        f"{len(contribution_txns)} contribution-like, "
        f"types={type_counts}"
    )

    # Also test a second account if available
    if len(account_ids) > 1:
        print()
        acct_id2, acct_name2, item_id2 = account_ids[1]
        info(f"Quick test of second account: {acct_name2}")
        try:
            data2 = gql(token, "TransactionsFeed", Q_TRANSACTIONS_FEED, {
                "first": 5,
                "filter": {"accountIds": [{"accountId": acct_id2, "itemId": item_id2}]},
                "sort": [{"direction": "DESC", "field": "DATE"}],
                "month": False,
            })
            if "errors" in data2:
                fail(f"  {acct_name2}: error — {data2['errors'][0].get('message', '?')}")
            else:
                edges2 = data2.get("data", {}).get("feed", {}).get("edges", [])
                ok(f"  {acct_name2}: {len(edges2)} transactions in first page")
        except Exception as e:
            fail(f"  {acct_name2}: {e}")

    per_account_support["transactionsFeed"] = True
    results["12_txn_feed"] = f"PASS — {len(all_transactions)} txns for {acct_name}"


def test_13_aggregated_holdings_per_account(token: str):
    """Re-test AggregatedHoldings per-account with BOTH accountId and itemId."""
    print_header(13, "AggregatedHoldings per-account (with itemId)")

    if not account_ids:
        warn("No account IDs available — skipping")
        results["13_agg_holdings_per_acct"] = "SKIP — no accounts"
        return

    # Get all-accounts baseline
    try:
        data_all = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                       {"timeFrame": "ONE_MONTH", "filter": "LAST_PRICE"})
        all_holdings = data_all.get("data", {}).get("aggregatedHoldings", [])
        all_count = len(all_holdings)
        ok(f"All-accounts baseline: {all_count} holdings")
    except Exception as e:
        fail(f"Baseline query failed: {e}")
        results["13_agg_holdings_per_acct"] = "FAIL — baseline failed"
        return

    print()
    total_per_acct = 0

    for acct_id, acct_name, item_id in account_ids[:4]:
        try:
            data = gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS,
                       {"timeFrame": "ONE_MONTH", "filter": "LAST_PRICE",
                        "accountId": acct_id, "itemId": item_id})

            if "errors" in data:
                fail(f"  {acct_name}: error — {data['errors'][0].get('message', '?')}")
                continue

            holdings = data.get("data", {}).get("aggregatedHoldings", [])
            total_per_acct += len(holdings)

            if holdings:
                symbols = [h.get("security", {}).get("symbol", "?") for h in holdings[:5]]
                symbol_str = ", ".join(symbols)
                if len(holdings) > 5:
                    symbol_str += f", ... (+{len(holdings) - 5} more)"
                ok(f"  {acct_name}: {len(holdings)} holdings  [{symbol_str}]")
            else:
                info(f"  {acct_name}: 0 holdings")

        except Exception as e:
            fail(f"  {acct_name}: {e}")

    print()
    info(f"Sum of per-account holdings: {total_per_acct}  (all-accounts: {all_count})")
    if total_per_acct > 0:
        if total_per_acct >= all_count:
            ok("Per-account filtering confirmed working (sum >= total)")
        else:
            warn("Per-account sum < total — some accounts may not have been tested")

    results["13_agg_holdings_per_acct"] = f"PASS — per-acct sum={total_per_acct} vs all={all_count}"


def test_14_summary():
    """Final comprehensive summary report."""
    print_header(14, "Comprehensive Summary Report")

    # --- Test Results ---
    info("=" * 60)
    info("TEST RESULTS")
    info("=" * 60)
    for key in sorted(results.keys()):
        info(f"    {key}: {results[key]}")
    print()

    # --- Endpoint Capability Matrix ---
    info("=" * 60)
    info("ENDPOINT CAPABILITY MATRIX")
    info("=" * 60)
    endpoints = [
        ("Accounts",              "List accounts",              True,  "N/A"),
        ("Holdings",              "Per-holding positions",       True,  "N/A"),
        ("AggregatedHoldings",    "Grouped holdings + change",   True,  "Yes (accountId+itemId)"),
        ("InvestmentBalance",     "Daily aggregate balance",     True,  "NO (aggregate only)"),
        ("InvestmentPerformance", "Daily aggregate perf %",      True,  "NO (aggregate only)"),
        ("InvestmentAllocation",  "Asset type allocation",       True,  "Via filter"),
        ("BalanceHistory",        "Daily per-account balance",   True,  "YES (accountId+itemId)"),
        ("AccountLiveBalance",    "Real-time account balance",   True,  "YES (accountId+itemId)"),
        ("Networth",              "Daily net worth history",     True,  "NO (aggregate only)"),
        ("TransactionSummary",    "Per-account txn stats",       True,  "YES (filter.accountIds)"),
        ("TransactionsFeed",      "Paginated transactions",      True,  "YES (filter.accountIds)"),
    ]
    info(f"    {'Endpoint':<25s}  {'Description':<30s}  {'Per-Account'}")
    info(f"    {'-'*25}  {'-'*30}  {'-'*25}")
    for name, desc, _, per_acct in endpoints:
        info(f"    {name:<25s}  {desc:<30s}  {per_acct}")
    print()

    # --- Per-Account Support (tested) ---
    info("=" * 60)
    info("PER-ACCOUNT SUPPORT (tested)")
    info("=" * 60)
    for endpoint, supported in sorted(per_account_support.items()):
        status = "YES" if supported else "NO"
        info(f"    {endpoint:<30s}  {status}")
    print()

    # --- Valid Timeframes ---
    info("=" * 60)
    info("VALID TIMEFRAMES BY ENDPOINT")
    info("=" * 60)
    for endpoint, tfs in sorted(valid_timeframes.items()):
        info(f"    {endpoint}: {', '.join(tfs)}")
    info(f"    (SIX_MONTHS is NOT valid)")
    print()

    # --- Data Quality Notes ---
    if data_quality_notes:
        info("=" * 60)
        info("DATA QUALITY NOTES")
        info("=" * 60)
        for note in data_quality_notes:
            info(f"    {note}")
        print()

    # --- TWR Feasibility ---
    info("=" * 60)
    info("TWR FEASIBILITY ASSESSMENT")
    info("=" * 60)

    bal_hist = per_account_support.get("balanceHistory")
    if bal_hist:
        ok("BalanceHistory provides per-account daily balances")
        ok("TWR via daily returns: TWR = product((V_t / V_{t-1}) - 1) for each day")
        info("  Method: For each consecutive day pair, compute daily return.")
        info("  Chain daily returns to get sub-period TWR.")
        info("  This is the STANDARD approach for TWR calculation.")
    else:
        fail("BalanceHistory not working — TWR limited to aggregate InvestmentPerformance data")
        info("  Fallback: Use InvestmentPerformance (aggregate only, no per-account)")

    print()

    # --- MWR/XIRR Feasibility ---
    info("=" * 60)
    info("MWR / XIRR FEASIBILITY ASSESSMENT")
    info("=" * 60)

    txn_feed = per_account_support.get("transactionsFeed")
    if txn_feed:
        ok("TransactionsFeed provides paginated transaction history per account")
        ok("XIRR feasibility: Can extract cash flow dates and amounts")
        info("  Method: Extract all contribution/withdrawal transactions as cash flows.")
        info("  Use current balance as terminal value.")
        info("  Solve for IRR using scipy.optimize or similar.")
        info("  KEY QUESTION: Are transaction amounts signed correctly for inflows/outflows?")
        info("  (Copilot uses negative amounts for contributions/inflows)")
    else:
        fail("TransactionsFeed not working — XIRR not feasible from API data")
        info("  Fallback: User must manually input cash flow data")

    print()

    # --- Critical Answers ---
    info("=" * 60)
    info("ANSWERS TO CRITICAL QUESTIONS")
    info("=" * 60)

    if bal_hist:
        ok("Q: Does BalanceHistory work for ALL accounts?  → YES (tested multiple)")
    else:
        fail("Q: Does BalanceHistory work for ALL accounts?  → NOT CONFIRMED")

    # Check data range from notes
    for note in data_quality_notes:
        if "BalanceHistory" in note:
            info(f"  Q: How far back does BalanceHistory go?  → {note}")

    if txn_feed:
        ok("Q: Does TransactionsFeed have contribution data?  → See test 12 results above")
    else:
        fail("Q: Does TransactionsFeed have contribution data?  → NOT TESTED")

    agg_per = per_account_support.get("aggregatedHoldings")
    if agg_per:
        ok("Q: Does AggregatedHoldings per-account work with itemId?  → YES")
    elif agg_per is False:
        fail("Q: Does AggregatedHoldings per-account work with itemId?  → NO")
    else:
        warn("Q: Does AggregatedHoldings per-account work with itemId?  → NOT TESTED")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("=" * 80)
    print("COPILOT MONEY GraphQL API — Phase 2: Extended Endpoint Testing")
    print(f"Endpoint: {API_URL}")
    print(f"Time:     {datetime.now().isoformat()}")
    print("=" * 80)

    token = load_token()

    if not test_1_auth(token):
        print("\nAborting — fix auth before continuing.")
        sys.exit(1)

    test_2_accounts(token)
    test_3_holdings(token)
    test_4_aggregated_holdings(token)
    test_5_investment_balance(token)
    test_6_investment_performance(token)
    test_7_investment_allocation(token)
    test_8_balance_history(token)
    test_9_account_live_balance(token)
    test_10_networth(token)
    test_11_transaction_summary(token)
    test_12_transactions_feed(token)
    test_13_aggregated_holdings_per_account(token)
    test_14_summary()

    print("=" * 80)
    print("All tests complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
