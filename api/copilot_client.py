"""
Copilot Money GraphQL API client.
Wraps queries from test_copilot_api.py into reusable functions.
"""

import base64
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

API_URL = "https://app.copilot.money/api/graphql"
SECURETOKEN_URL = "https://securetoken.googleapis.com/v1/token"
IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/v1"
DEFAULT_FIREBASE_API_KEY = "AIzaSyAMgjkeOSkHj4J4rlswOkD16N3WQOoNPpk"
DEFAULT_FIREBASE_GMPID = "1:445606440735:web:b0ac6d52da1d4c16c90a2a"
DEFAULT_FIREBASE_CLIENT_VERSION = "Chrome/JsCore/11.7.3/FirebaseCore-web"

HEADERS_TEMPLATE = {
    "content-type": "application/json",
    "accept": "*/*",
    "apollographql-client-name": "web",
    "apollographql-client-version": "26.4.8+1387",
    "origin": "https://app.copilot.money",
    "referer": "https://app.copilot.money/investments",
}


def _env_path() -> Path:
    return Path.home() / "Documents" / "copilot" / ".env"


def _read_env_value(key: str) -> str | None:
    env_path = _env_path()
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _normalize_bearer(token: str) -> str:
    token = token.strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _load_token() -> str:
    """Load JWT from env var or .env file."""
    token = os.environ.get("COPILOT_TOKEN")
    if token:
        return token.strip()
    token = _read_env_value("COPILOT_TOKEN")
    if token:
        return token
    raise RuntimeError("COPILOT_TOKEN not set. Set env var or create backend/.env")


def _load_refresh_token() -> str | None:
    token = os.environ.get("COPILOT_REFRESH_TOKEN")
    if token:
        return token.strip()
    return _read_env_value("COPILOT_REFRESH_TOKEN")


def _save_env_values(updates: dict[str, str]) -> None:
    env_path = _env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    replaced = {k: False for k in updates}
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        did_replace = False
        for key, value in updates.items():
            if stripped.startswith(f"{key}="):
                out_lines.append(value)
                replaced[key] = True
                did_replace = True
                break
        if not did_replace:
            out_lines.append(line)
    for key, value in updates.items():
        if not replaced[key]:
            out_lines.append(value)
    env_path.write_text("\n".join(out_lines).rstrip() + "\n")


def _save_tokens_to_env_file(id_token: str, refresh_token: str) -> None:
    _save_env_values({
        "COPILOT_TOKEN": f"COPILOT_TOKEN=Bearer {id_token}",
        "COPILOT_REFRESH_TOKEN": f"COPILOT_REFRESH_TOKEN={refresh_token}",
    })


def _refresh_id_token(refresh_token: str) -> tuple[str, str]:
    api_key = os.environ.get("COPILOT_FIREBASE_API_KEY", DEFAULT_FIREBASE_API_KEY)
    resp = requests.post(
        f"{SECURETOKEN_URL}?key={api_key}",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=30,
    )
    data = resp.json()
    if resp.status_code != 200 or "id_token" not in data:
        raise RuntimeError(f"Token refresh failed: {data}")
    return data["id_token"], data.get("refresh_token", refresh_token)


def _decode_jwt_payload(token: str) -> dict | None:
    raw = token.strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:]
    parts = raw.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    padding = 4 - (len(payload) % 4)
    if padding != 4:
        payload += "=" * padding
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return None


def _firebase_api_key() -> str:
    return os.environ.get("COPILOT_FIREBASE_API_KEY") or _read_env_value("COPILOT_FIREBASE_API_KEY") or DEFAULT_FIREBASE_API_KEY


def _app_check_token() -> str | None:
    return os.environ.get("COPILOT_APP_CHECK_TOKEN") or _read_env_value("COPILOT_APP_CHECK_TOKEN")


def _firebase_gmpid() -> str:
    return os.environ.get("COPILOT_FIREBASE_GMPID") or _read_env_value("COPILOT_FIREBASE_GMPID") or DEFAULT_FIREBASE_GMPID


def _firebase_auth_headers() -> dict[str, str]:
    token = _app_check_token()
    if not token:
        raise RuntimeError(
            "COPILOT_APP_CHECK_TOKEN is required for email-link auth. "
            "Set it in .env from Copilot web auth requests."
        )
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://app.copilot.money",
        "user-agent": "Mozilla/5.0",
        "x-client-version": DEFAULT_FIREBASE_CLIENT_VERSION,
        "x-firebase-appcheck": token,
        "x-firebase-gmpid": _firebase_gmpid(),
    }


def start_magic_link(email: str) -> dict:
    """Start email-link auth by sending a magic link to the email."""
    payload = {
        "requestType": "EMAIL_SIGNIN",
        "email": email,
        "canHandleCodeInApp": True,
        "continueUrl": "https://app.copilot.money/login",
        "clientType": "CLIENT_TYPE_WEB",
    }
    resp = requests.post(
        f"{IDENTITY_TOOLKIT_URL}/accounts:sendOobCode?key={_firebase_api_key()}",
        json=payload,
        headers=_firebase_auth_headers(),
        timeout=30,
    )
    data = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Magic link request failed: {data}")
    return data


def _parse_magic_link(link: str) -> tuple[str, str]:
    parsed = urlparse(link)
    qs = parse_qs(parsed.query)
    api_key = qs.get("apiKey", [None])[0]
    oob_code = qs.get("oobCode", [None])[0]
    if not api_key or not oob_code:
        raise RuntimeError("Magic link is missing apiKey or oobCode")
    return api_key, oob_code


def complete_magic_link(email: str, magic_link: str) -> dict:
    """Exchange magic link for id and refresh tokens and persist them."""
    api_key, oob_code = _parse_magic_link(magic_link)
    payload = {
        "email": email,
        "oobCode": oob_code,
        "clientType": "CLIENT_TYPE_WEB",
    }
    resp = requests.post(
        f"{IDENTITY_TOOLKIT_URL}/accounts:signInWithEmailLink?key={api_key}",
        json=payload,
        headers=_firebase_auth_headers(),
        timeout=30,
    )
    data = resp.json()
    if resp.status_code != 200 or "idToken" not in data:
        raise RuntimeError(f"Magic link exchange failed: {data}")

    id_token = data["idToken"]
    refresh_token = data["refreshToken"]
    os.environ["COPILOT_TOKEN"] = f"Bearer {id_token}"
    os.environ["COPILOT_REFRESH_TOKEN"] = refresh_token
    _save_tokens_to_env_file(id_token, refresh_token)
    return data


def configure_onboarding_values(app_check_token: str | None = None, gmpid: str | None = None) -> None:
    """Persist optional onboarding values used by email-link auth."""
    updates: dict[str, str] = {}
    if app_check_token:
        updates["COPILOT_APP_CHECK_TOKEN"] = f"COPILOT_APP_CHECK_TOKEN={app_check_token.strip()}"
    if gmpid:
        updates["COPILOT_FIREBASE_GMPID"] = f"COPILOT_FIREBASE_GMPID={gmpid.strip()}"
    if updates:
        _save_env_values(updates)


def get_auth_status() -> dict:
    """Return token presence and expiry diagnostics."""
    token = os.environ.get("COPILOT_TOKEN") or _read_env_value("COPILOT_TOKEN")
    refresh = _load_refresh_token()
    payload = _decode_jwt_payload(token) if token else None
    exp = payload.get("exp") if payload else None
    expires_at = datetime.fromtimestamp(exp, tz=UTC).isoformat() if exp else None
    now = datetime.now(tz=UTC).timestamp()
    expired = bool(exp and exp <= now)
    return {
        "has_token": bool(token),
        "has_refresh_token": bool(refresh),
        "has_app_check_token": bool(_app_check_token()),
        "email": payload.get("email") if payload else None,
        "expires_at": expires_at,
        "expired": expired,
    }


def refresh_access_token() -> dict:
    """Refresh access token using refresh token and persist rotated tokens."""
    refresh_token = _load_refresh_token()
    if not refresh_token:
        raise RuntimeError("COPILOT_REFRESH_TOKEN is not set")
    id_token, new_refresh_token = _refresh_id_token(refresh_token)
    os.environ["COPILOT_TOKEN"] = f"Bearer {id_token}"
    os.environ["COPILOT_REFRESH_TOKEN"] = new_refresh_token
    _save_tokens_to_env_file(id_token, new_refresh_token)
    payload = _decode_jwt_payload(id_token) or {}
    return {
        "email": payload.get("email"),
        "expires_at": datetime.fromtimestamp(payload["exp"], tz=UTC).isoformat() if payload.get("exp") else None,
    }


def _has_auth_error(resp_status: int, data: dict) -> bool:
    if resp_status == 401:
        return True
    if "errors" not in data:
        return False
    for err in data.get("errors", []):
        msg = str(err.get("message", "")).lower()
        code = str(err.get("extensions", {}).get("code", "")).upper()
        if (
            "id-token-expired" in msg
            or "auth/id-token-expired" in msg
            or "unauthenticated" in msg
            or code == "UNAUTHENTICATED"
        ):
            return True
    return False


def _gql(token: str, operation: str, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query, auto-refreshing token when expired."""
    auth_token = _normalize_bearer(token)
    headers = {**HEADERS_TEMPLATE, "authorization": auth_token}
    payload = {"operationName": operation, "query": query, "variables": variables or {}}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
    data = resp.json()

    if _has_auth_error(resp.status_code, data):
        refresh_token = _load_refresh_token()
        if refresh_token:
            id_token, new_refresh_token = _refresh_id_token(refresh_token)
            os.environ["COPILOT_TOKEN"] = f"Bearer {id_token}"
            os.environ["COPILOT_REFRESH_TOKEN"] = new_refresh_token
            _save_tokens_to_env_file(id_token, new_refresh_token)

            retry_headers = {**HEADERS_TEMPLATE, "authorization": f"Bearer {id_token}"}
            retry_resp = requests.post(API_URL, json=payload, headers=retry_headers, timeout=60)
            try:
                retry_data = retry_resp.json()
            except ValueError:
                retry_data = {}
            if _has_auth_error(retry_resp.status_code, retry_data):
                raise RuntimeError(
                    f"Authentication failed after token refresh in {operation} "
                    f"(status {retry_resp.status_code}): {retry_data or retry_resp.text!r}"
                )
            if retry_resp.status_code >= 400:
                raise RuntimeError(
                    f"GraphQL request failed in {operation} after refresh "
                    f"(status {retry_resp.status_code}): {retry_data or retry_resp.text!r}"
                )
            if "errors" in retry_data:
                raise RuntimeError(f"GraphQL error in {operation}: {retry_data['errors']}")
            return retry_data.get("data", {})

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
