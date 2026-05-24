import json
import time
from pathlib import Path
from typing import Any

import httpx

from flatbot.config import settings
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.integrations.openproperties.mapper import map_listings
from flatbot.integrations.openproperties.query_builder import (
    build_listings_params,
    build_recent_params,
)
from flatbot.models import Filter

_HOST = "openproperties.p.rapidapi.com"
_BASE_URL = f"https://{_HOST}/public/v2"
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "openproperties_listings.json"
)


class OpenPropertiesClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.rapidapi_key
        self._headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": _HOST,
        }

    def _get(self, path: str, params: dict[str, str | int | float]) -> dict[str, Any]:
        delay = 1.0
        url = f"{_BASE_URL}{path}"
        with httpx.Client(headers=self._headers, timeout=15.0) as client:
            for attempt in range(_MAX_RETRIES):
                resp = client.get(url, params=params)
                if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
        return {}

    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        data = self._get("/listings/recent", build_recent_params(f, hours=hours, limit=limit))
        return map_listings(data.get("data") or [])

    def fetch_listings(
        self, f: Filter, page: int = 1, page_size: int = 20, max_age_days: int | None = None
    ) -> tuple[list[ListingDTO], dict[str, Any]]:
        params = build_listings_params(f, page=page, page_size=page_size, max_age_days=max_age_days)
        data = self._get("/listings", params)
        return map_listings(data.get("data") or []), data.get("meta") or {}

    def fetch_listing(self, listing_id: str) -> dict[str, Any]:
        return self._get(f"/listings/{listing_id}", {})

    def fetch_market_stats(self, lat: float, lng: float, radius_km: float, kind: str) -> dict[str, Any]:
        return self._get("/market/stats", {"lat": lat, "lng": lng, "radiusKm": radius_km, "kind": kind})


class MockOpenPropertiesClient:
    """Loads fixture JSON from tests/fixtures/ — no API calls, no quota burned."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        path = fixture_path or _FIXTURE_PATH
        with open(path, encoding="utf-8") as fh:
            self._fixture: dict[str, Any] = json.load(fh)

    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        return map_listings(self._fixture.get("data") or [])

    def fetch_listings(
        self, f: Filter, page: int = 1, page_size: int = 20, max_age_days: int | None = None
    ) -> tuple[list[ListingDTO], dict[str, Any]]:
        return map_listings(self._fixture.get("data") or []), self._fixture.get("meta") or {}

    def fetch_listing(self, listing_id: str) -> dict[str, Any]:
        for item in self._fixture.get("data") or []:
            if item.get("id") == listing_id:
                return item  # type: ignore[no-any-return]
        return {}

    def fetch_market_stats(self, lat: float, lng: float, radius_km: float, kind: str) -> dict[str, Any]:
        return {}


def make_client(api_key: str | None = None) -> OpenPropertiesClient | MockOpenPropertiesClient:
    if settings.mock_api:
        return MockOpenPropertiesClient()
    return OpenPropertiesClient(api_key=api_key)
