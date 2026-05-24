"""Tests for BotApiClient using httpx mocking."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from flatbot.bot.api_client import BotApiClient

BASE = "http://web:8000"


@pytest.fixture
def api() -> BotApiClient:
    return BotApiClient(BASE)


class TestBotApiClient:
    async def test_get_status(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/status",
            json={"active_filters": 2, "last_scan": None},
        )
        status = await api.get_status()
        assert status["active_filters"] == 2
        assert status["last_scan"] is None

    async def test_get_filters(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/filters",
            json=[{"id": 1, "name": "Gràcia", "is_active": True, "kind": "rent", "radius_km": 2.0}],
        )
        filters = await api.get_filters()
        assert len(filters) == 1
        assert filters[0]["name"] == "Gràcia"

    async def test_activate_filter(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/filters/1/activate",
            method="POST",
            json={"id": 1, "name": "test", "is_active": True},
        )
        result = await api.activate_filter(1)
        assert result["is_active"] is True

    async def test_deactivate_filter(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/filters/1/deactivate",
            method="POST",
            json={"id": 1, "name": "test", "is_active": False},
        )
        result = await api.deactivate_filter(1)
        assert result["is_active"] is False

    async def test_run_scan(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/scan/run",
            method="POST",
            json={
                "id": 1, "status": "completed",
                "listings_fetched": 10, "new_listings": 2,
                "matches_found": 1, "alerts_sent": 1,
                "started_at": "2026-05-24T10:00:00+00:00",
                "finished_at": "2026-05-24T10:00:05+00:00",
                "error_message": None,
            },
        )
        run = await api.run_scan()
        assert run["status"] == "completed"
        assert run["new_listings"] == 2

    async def test_get_recent_matches(self, api: BotApiClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{BASE}/api/matches/recent?limit=5",
            json=[{"id": 1, "filter_name": "test", "listing": {"url": "https://x.com"}}],
        )
        matches = await api.get_recent_matches(limit=5)
        assert len(matches) == 1
        assert matches[0]["filter_name"] == "test"

    async def test_http_error_propagates(
        self, api: BotApiClient, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(url=f"{BASE}/api/status", status_code=500)
        with pytest.raises(httpx.HTTPStatusError):
            await api.get_status()
