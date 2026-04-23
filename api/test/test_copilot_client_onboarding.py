import os
import sys
import tempfile
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


class CopilotClientOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.original_env = dict(os.environ)
        self.tmp = tempfile.TemporaryDirectory()
        self.env_path = Path(self.tmp.name) / ".env"
        self.env_path.write_text("EXISTING_VAR=keep_me\n")
        self.env_path_patch = patch.object(cc, "_env_path", return_value=self.env_path)
        self.env_path_patch.start()

    def tearDown(self):
        self.env_path_patch.stop()
        os.environ.clear()
        os.environ.update(self.original_env)
        self.tmp.cleanup()

    def test_start_magic_link_success(self):
        os.environ["COPILOT_APP_CHECK_TOKEN"] = "app-check"
        with patch.object(
            cc.requests,
            "post",
            return_value=_FakeResponse(
                200,
                {"kind": "identitytoolkit#GetOobConfirmationCodeResponse", "email": "user@example.com"},
            ),
        ) as post_mock:
            data = cc.start_magic_link("user@example.com")

        self.assertEqual(data["email"], "user@example.com")
        self.assertEqual(post_mock.call_count, 1)
        self.assertIn("sendOobCode", post_mock.call_args[0][0])

    def test_start_magic_link_app_check_missing(self):
        os.environ.pop("COPILOT_APP_CHECK_TOKEN", None)
        with self.assertRaises(RuntimeError):
            cc.start_magic_link("user@example.com")

    def test_complete_magic_link_invalid_code_raises(self):
        os.environ["COPILOT_APP_CHECK_TOKEN"] = "app-check"
        with patch.object(
            cc.requests,
            "post",
            return_value=_FakeResponse(
                400,
                {"error": {"message": "INVALID_OOB_CODE"}},
            ),
        ):
            with self.assertRaises(RuntimeError):
                cc.complete_magic_link(
                    "user@example.com",
                    "https://auth.copilot.money/__/auth/action?apiKey=a&oobCode=b&mode=signIn",
                )

    def test_configure_onboarding_values_preserves_existing_vars(self):
        cc.configure_onboarding_values("new-app-check-token", "new-gmpid")
        contents = self.env_path.read_text()
        self.assertIn("EXISTING_VAR=keep_me", contents)
        self.assertIn("COPILOT_APP_CHECK_TOKEN=new-app-check-token", contents)
        self.assertIn("COPILOT_FIREBASE_GMPID=new-gmpid", contents)


if __name__ == "__main__":
    unittest.main()
