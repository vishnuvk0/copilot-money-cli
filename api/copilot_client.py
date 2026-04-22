"""
Copilot Money GraphQL API client.
Wraps queries from test_copilot_api.py into reusable functions.
"""

import os
from pathlib import Path

import requests

API_URL = "https://app.copilot.money/api/graphql"

HEADERS_TEMPLATE = {
    "content-type": "application/json",
    "accept": "*/*",
    "apollographql-client-name": "web",
    "apollographql-client-version": "26.4.8+1387",
    "origin": "https://app.copilot.money",
    "referer": "https://app.copilot.money/investments",
}


def _load_token() -> str:
    """Load JWT from env var or .env file."""
    token = os.environ.get("COPILOT_TOKEN")
    if token:
        return token.strip()
    env_path = Path.home() / "Documents" / "copilot" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("COPILOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("COPILOT_TOKEN not set. Set env var or create backend/.env")


def _gql(token: str, operation: str, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query."""
    headers = {**HEADERS_TEMPLATE, "authorization": f"{token}"}
    payload = {"operationName": operation, "query": query, "variables": variables or {}}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error in {operation}: {data['errors']}")
    return data.get("data", {})


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

Q_ACCOUNTS = """
query Accounts($filter: AccountFilter) {
  accounts(filter: $filter) {
    hasHistoricalUpdates
    latestBalanceUpdate
    hasLiveBalance
    institutionId
    isManual
    balance
    subType
    itemId
    name
    type
    id
    __typename
  }
}
"""

Q_BALANCE_HISTORY = """
query BalanceHistory($itemId: ID!, $accountId: ID!, $timeFrame: TimeFrame) {
  accountBalanceHistory(itemId: $itemId, accountId: $accountId, timeFrame: $timeFrame) {
    balance
    date
    __typename
  }
}
"""

Q_TRANSACTIONS_FEED = """
query TransactionsFeed($first: Int, $after: String, $filter: TransactionFilter, $sort: [TransactionSort!]) {
  feed: transactionsFeed(first: $first, after: $after, filter: $filter, sort: $sort) {
    edges {
      cursor
      node {
        ... on Transaction {
          recurringId
          categoryId
          accountId
          itemId
          amount
          date
          name
          type
          id
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      endCursor
      hasNextPage
      __typename
    }
    __typename
  }
}
"""

Q_HOLDINGS = """
query Holdings {
  holdings {
    security {
      currentPrice
      symbol
      name
      type
      id
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

Q_INVESTMENT_ALLOCATION = """
query InvestmentAllocation($filter: AllocationFilter) {
  investmentAllocation(filter: $filter) {
    percentage
    amount
    type
    id
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

Q_HOLDING_QUANTITY_BY_SECURITY = """
query HoldingQuantityBySecurity($id: ID!, $timeFrame: TimeFrame) {
  holdingQuantitiesBySecurity(securityId: $id, timeFrame: $timeFrame) {
    quantity
    date
    __typename
  }
}
"""

Q_SECURITY_PRICES = """
query SecurityPrices($id: ID!, $timeFrame: TimeFrame) {
  securityPrices(securityId: $id, timeFrame: $timeFrame) {
    price
    date
    __typename
  }
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_accounts(token: str | None = None) -> list[dict]:
    """Fetch all investment accounts."""
    token = token or _load_token()
    data = _gql(token, "Accounts", Q_ACCOUNTS, {"filter": {"type": "INVESTMENT"}})
    return data.get("accounts", [])


def fetch_balance_history(account_id: str, item_id: str, timeframe: str = "ALL",
                          token: str | None = None) -> list[dict]:
    """Fetch daily balance history for a single account."""
    token = token or _load_token()
    data = _gql(token, "BalanceHistory", Q_BALANCE_HISTORY, {
        "accountId": account_id,
        "itemId": item_id,
        "timeFrame": timeframe,
    })
    return data.get("accountBalanceHistory", [])


def fetch_transactions(account_id: str, item_id: str,
                        token: str | None = None) -> list[dict]:
    """Fetch ALL transactions for an account (auto-paginates)."""
    token = token or _load_token()
    all_txns: list[dict] = []
    cursor = None
    page = 0

    while True:
        page += 1
        variables: dict = {
            "first": 50,
            "filter": {
                "accountIds": [{"accountId": account_id, "itemId": item_id}]
            },
            "sort": [{"direction": "DESC", "field": "DATE"}],
        }
        if cursor:
            variables["after"] = cursor

        data = _gql(token, "TransactionsFeed", Q_TRANSACTIONS_FEED, variables)
        feed = data.get("feed", {})
        edges = feed.get("edges", [])

        for edge in edges:
            node = edge.get("node", {})
            if node.get("__typename") == "Transaction":
                all_txns.append(node)

        page_info = feed.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor or page >= 100:
            break

    return all_txns


def fetch_holdings(token: str | None = None) -> list[dict]:
    """Fetch all holdings with cost basis."""
    token = token or _load_token()
    data = _gql(token, "Holdings", Q_HOLDINGS)
    return data.get("holdings", [])


def fetch_networth(timeframe: str = "ALL", token: str | None = None) -> list[dict]:
    """Fetch daily networth history."""
    token = token or _load_token()
    data = _gql(token, "Networth", Q_NETWORTH, {"timeFrame": timeframe})
    return data.get("networthHistory", [])


def fetch_aggregated_holdings(
    timeframe: str = "ONE_WEEK",
    account_id: str | None = None,
    item_id: str | None = None,
    token: str | None = None,
) -> list[dict]:
    """Fetch aggregated holdings grouped by security with change/value."""
    token = token or _load_token()
    variables: dict = {"timeFrame": timeframe, "filter": "LAST_PRICE"}
    if account_id:
        variables["accountId"] = account_id
    if item_id:
        variables["itemId"] = item_id
    data = _gql(token, "AggregatedHoldings", Q_AGGREGATED_HOLDINGS, variables)
    return data.get("aggregatedHoldings", [])


def fetch_investment_allocation(
    account_id: str | None = None,
    item_id: str | None = None,
    token: str | None = None,
) -> list[dict]:
    """Fetch asset class allocation (e.g. US Equity, International, etc.)."""
    token = token or _load_token()
    variables: dict = {}
    if account_id and item_id:
        variables["filter"] = {"accountId": account_id, "itemId": item_id}
    data = _gql(token, "InvestmentAllocation", Q_INVESTMENT_ALLOCATION, variables)
    return data.get("investmentAllocation", [])


def fetch_investment_performance(
    timeframe: str = "ALL",
    token: str | None = None,
) -> list[dict]:
    """Fetch daily investment performance in basis points."""
    token = token or _load_token()
    data = _gql(token, "InvestmentPerformance", Q_INVESTMENT_PERFORMANCE, {"timeFrame": timeframe})
    return data.get("investmentPerformance", [])


def fetch_investment_balance(
    timeframe: str = "ALL",
    token: str | None = None,
) -> list[dict]:
    """Fetch daily aggregate investment balance."""
    token = token or _load_token()
    data = _gql(token, "InvestmentBalance", Q_INVESTMENT_BALANCE, {"timeFrame": timeframe})
    return data.get("investmentBalance", [])


def fetch_holding_quantity_by_security(
    security_id: str,
    timeframe: str = "ALL",
    token: str | None = None,
) -> list[dict]:
    """Fetch daily total quantity for a security across all accounts."""
    token = token or _load_token()
    data = _gql(token, "HoldingQuantityBySecurity", Q_HOLDING_QUANTITY_BY_SECURITY, {
        "id": security_id,
        "timeFrame": timeframe,
    })
    return data.get("holdingQuantitiesBySecurity", [])


def fetch_security_prices(
    security_id: str,
    timeframe: str = "ONE_YEAR",
    token: str | None = None,
) -> list[dict]:
    """Fetch daily market price for a security."""
    token = token or _load_token()
    data = _gql(token, "SecurityPrices", Q_SECURITY_PRICES, {
        "id": security_id,
        "timeFrame": timeframe,
    })
    return data.get("securityPrices", [])
