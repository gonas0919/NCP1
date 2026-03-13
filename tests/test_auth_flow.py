import os
import uuid
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def request(opener, path: str, method: str = "GET", form: dict | None = None):
    data = urllib.parse.urlencode(form).encode() if form else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    with opener.open(req, timeout=8) as response:
        body = response.read().decode("utf-8", errors="ignore")
        return response.geturl(), response.status, body


def test_health_endpoint():
    opener = urllib.request.build_opener()
    final_url, status, body = request(opener, "/health")
    assert final_url.endswith("/health")
    assert status == 200
    assert '"status"' in body and "ok" in body


def test_register_and_login_core_flow():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    suffix = uuid.uuid4().hex[:10]
    username = f"user_{suffix}"
    email = f"{username}@example.com"
    password = "StrongPass123!"

    final_url, status, _ = request(
        opener,
        "/register",
        method="POST",
        form={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert status == 200
    assert final_url.endswith("/login")

    final_url, status, body = request(
        opener,
        "/login",
        method="POST",
        form={
            "identity": username,
            "password": password,
        },
    )
    assert status == 200
    assert final_url.endswith("/")
    assert username in body
