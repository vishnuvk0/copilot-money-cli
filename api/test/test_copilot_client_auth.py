import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import copilot_client as cc


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class CopilotClientAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_env = dict(os.environ)
        os.environ["COPILOT_REFRESH_TOKEN"] = "old-refresh-token"
        os.environ["COPILOT_TOKEN"] = "Bearer expired-token"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_gql_refreshes_token_and_retries(self):
        responses = [
            _FakeResponse(
                200,
                {
                    "errors": [
                        {
                            "message": (
                                "Firebase ID token has expired. Get a fresh ID token "
                                "from your client app and try again (auth/id-token-expired)."
                            ),
                            "extensions": {"code": "UNAUTHENTICATED"},
                        }
                    ]
                },
            ),
            _FakeResponse(
                200,
                {"id_token": "new-id-token", "refresh_token": "new-refresh-token"},
            ),
            _FakeResponse(200, {"data": {"accounts": [{"id": "abc"}]}}),
        ]

        with (
            patch.object(cc.requests, "post", side_effect=responses) as post_mock,
            patch.object(cc, "_save_tokens_to_env_file") as save_mock,
        ):
            data = cc._gql(
                "Bearer expired-token",
                "Accounts",
                "query Accounts { accounts { id } }",
            )

        self.assertEqual(data, {"accounts": [{"id": "abc"}]})
        self.assertEqual(os.environ["COPILOT_TOKEN"], "Bearer new-id-token")
        self.assertEqual(os.environ["COPILOT_REFRESH_TOKEN"], "new-refresh-token")
        self.assertEqual(post_mock.call_count, 3)
        save_mock.assert_called_once_with("new-id-token", "new-refresh-token")

    def test_gql_auth_error_without_refresh_token_raises(self):
        os.environ.pop("COPILOT_REFRESH_TOKEN", None)

        with patch.object(
            cc.requests,
            "post",
            return_value=_FakeResponse(
                401,
                {"errors": [{"message": "UNAUTHENTICATED", "extensions": {"code": "UNAUTHENTICATED"}}]},
            ),
        ):
            with self.assertRaises(RuntimeError):
                cc._gql(
                    "Bearer expired-token",
                    "Accounts",
                    "query Accounts { accounts { id } }",
                )

    def test_gql_retry_with_401_no_errors_key_raises(self):
        """After refresh+retry, a 401 response without an 'errors' key must still raise."""
        responses = [
            _FakeResponse(
                200,
                {
                    "errors": [
                        {
                            "message": "auth/id-token-expired",
                            "extensions": {"code": "UNAUTHENTICATED"},
                        }
                    ]
                },
            ),
            _FakeResponse(
                200,
                {"id_token": "new-id-token", "refresh_token": "new-refresh-token"},
            ),
            _FakeResponse(401, {"error": {"code": 401, "message": "UNAUTHENTICATED"}}),
        ]

        with (
            patch.object(cc.requests, "post", side_effect=responses),
            patch.object(cc, "_save_tokens_to_env_file"),
        ):
            with self.assertRaises(RuntimeError):
                cc._gql(
                    "Bearer expired-token",
                    "Accounts",
                    "query Accounts { accounts { id } }",
                )


if __name__ == "__main__":
    unittest.main()
