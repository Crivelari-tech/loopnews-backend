"""
Backend tests for LoopNews demo reviewer auth flow (Google Play review fix).

Covers:
- Demo send-code returns success and does NOT trigger real email
- Demo verify-code with correct code (123456) succeeds and returns session
- Demo verify-code with wrong code is rejected
- Demo verify-code works WITHOUT prior send-code (restart-safe hardcoded bypass)
- Regression: send-code for a normal email still succeeds
"""
import os
import re
import time
import requests
import pytest

# Use public /api URL (frontend uses EXPO_PUBLIC_BACKEND_URL); fallback to local for backend-only tests
BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")

DEMO_EMAIL = "reviewer@loopnewsapp.com"
DEMO_CODE = "123456"
WRONG_CODE = "999999"


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Demo reviewer flow ----------
class TestDemoReviewerAuth:
    def test_send_code_demo_reviewer_success(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/send-code",
            json={"email": DEMO_EMAIL},
            timeout=15,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        # Endpoint returns a message; accept either shape
        assert "message" in body or "success" in body
        # No leakage of the demo code in response
        assert DEMO_CODE not in r.text

    def test_verify_code_demo_reviewer_success(self, api_client):
        # Ensure send-code first (typical flow)
        api_client.post(
            f"{BASE_URL}/api/auth/send-code",
            json={"email": DEMO_EMAIL},
            timeout=15,
        )
        r = api_client.post(
            f"{BASE_URL}/api/auth/verify-code",
            json={"email": DEMO_EMAIL, "code": DEMO_CODE},
            timeout=15,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        # Must return a session token and a user object
        assert "user" in data, f"Missing 'user' in response: {data}"
        assert isinstance(data["user"], dict)
        assert data["user"].get("email") == DEMO_EMAIL
        # session token can be under session_token / token / access_token
        token_keys = [k for k in ("session_token", "token", "access_token") if k in data]
        assert token_keys, f"No session token key found. Keys={list(data.keys())}"
        assert data[token_keys[0]], "Session token is empty"

    def test_verify_code_demo_reviewer_wrong_code_rejected(self, api_client):
        api_client.post(
            f"{BASE_URL}/api/auth/send-code",
            json={"email": DEMO_EMAIL},
            timeout=15,
        )
        r = api_client.post(
            f"{BASE_URL}/api/auth/verify-code",
            json={"email": DEMO_EMAIL, "code": WRONG_CODE},
            timeout=15,
        )
        assert r.status_code == 400, f"Expected 400 for wrong code, got {r.status_code}: {r.text}"
        # detail should describe invalid/incorrect code
        detail = (r.json().get("detail") or "").lower()
        assert any(w in detail for w in ["incorreto", "inválido", "invalid", "expirado"]), (
            f"Unexpected error detail: {detail}"
        )

    def test_verify_code_demo_reviewer_without_send_code(self, api_client):
        """Restart-safe hardcoded bypass: verify must work even if send-code was never called."""
        # Try to purge in-memory state by using verify directly on a "fresh" email path.
        # Since we can't restart the server from tests, this still exercises the bypass branch
        # because the demo email+code combination re-seeds verification_codes inside verify-code.
        # First, we simulate absence by verifying with wrong code (which deletes the entry if any),
        # then verifying with the correct one should still succeed thanks to the bypass.
        api_client.post(
            f"{BASE_URL}/api/auth/verify-code",
            json={"email": DEMO_EMAIL, "code": WRONG_CODE},
            timeout=15,
        )
        r = api_client.post(
            f"{BASE_URL}/api/auth/verify-code",
            json={"email": DEMO_EMAIL, "code": DEMO_CODE},
            timeout=15,
        )
        assert r.status_code == 200, (
            f"Restart-safe demo bypass failed. status={r.status_code} body={r.text}"
        )
        data = r.json()
        assert data.get("user", {}).get("email") == DEMO_EMAIL


# ---------- Regression: normal email flow ----------
class TestNormalEmailRegression:
    def test_send_code_normal_email_success(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/send-code",
            json={"email": "testeuser123@gmail.com"},
            timeout=20,
        )
        # We don't assert email delivery, only that endpoint responds successfully
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert "message" in body or "success" in body

    def test_send_code_invalid_email_rejected(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/send-code",
            json={"email": "not-an-email"},
            timeout=10,
        )
        assert r.status_code in (400, 422), (
            f"Expected 400/422 for invalid email, got {r.status_code}: {r.text}"
        )
