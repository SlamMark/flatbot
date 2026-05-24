"""Tests for portal authentication middleware and login routes (F8)."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.config import settings
from flatbot.db import get_db
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.models import Filter
from flatbot.web.app import app
from flatbot.web.auth import make_auth_token
from flatbot.web.deps import get_alert_sender, get_scan_client

_PASSWORD = "s3cr3t"


class _EmptyClient:
    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        return []


class _FakeSender(AlertSender):
    def __init__(self) -> None:
        super().__init__(bot_token="x", chat_id="x")

    def send(self, text: str) -> bool:
        return True


@pytest.fixture
def auth_client(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "web_password", _PASSWORD)

    def _db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_scan_client] = lambda: _EmptyClient()
    app.dependency_overrides[get_alert_sender] = lambda: _FakeSender()

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


class TestAuthMiddleware:
    def test_unauthenticated_redirects_to_login(self, auth_client: TestClient) -> None:
        resp = auth_client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_health_exempt_from_auth(self, auth_client: TestClient) -> None:
        assert auth_client.get("/health").status_code == 200

    def test_api_status_exempt_from_auth(self, auth_client: TestClient) -> None:
        assert auth_client.get("/api/status").status_code == 200

    def test_login_page_accessible_without_cookie(self, auth_client: TestClient) -> None:
        assert auth_client.get("/login").status_code == 200

    def test_valid_cookie_grants_access(
        self, auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "web_password", _PASSWORD)
        token = make_auth_token()
        resp = auth_client.get("/", cookies={"auth": token})
        assert resp.status_code == 200

    def test_tampered_cookie_redirects_to_login(self, auth_client: TestClient) -> None:
        resp = auth_client.get("/", cookies={"auth": "bad.token"}, follow_redirects=False)
        assert resp.status_code == 302


class TestLoginRoutes:
    def test_login_page_returns_200(self, auth_client: TestClient) -> None:
        assert auth_client.get("/login").status_code == 200

    def test_correct_password_sets_cookie(self, auth_client: TestClient) -> None:
        resp = auth_client.post(
            "/login", data={"password": _PASSWORD}, follow_redirects=False
        )
        assert resp.status_code == 303
        assert "auth" in resp.cookies

    def test_wrong_password_redirects_with_error(self, auth_client: TestClient) -> None:
        resp = auth_client.post(
            "/login", data={"password": "wrong"}, follow_redirects=False
        )
        assert resp.status_code == 303
        assert "error=1" in resp.headers["location"]

    def test_logout_clears_cookie(
        self, auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "web_password", _PASSWORD)
        token = make_auth_token()
        resp = auth_client.get("/logout", cookies={"auth": token}, follow_redirects=False)
        assert resp.status_code == 303
        # Cookie should be cleared (max_age=0 or deleted)
        assert resp.cookies.get("auth") in (None, "")

    def test_open_redirect_blocked(self, auth_client: TestClient) -> None:
        # next=https://evil.com should be sanitised to /
        resp = auth_client.post(
            "/login?next=https://evil.com",
            data={"password": _PASSWORD},
            follow_redirects=False,
        )
        location = resp.headers["location"]
        assert not location.startswith("https://evil.com")
