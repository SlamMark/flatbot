"""Async client that wraps the FlatBot web API for use by the bot service."""
from typing import Any

import httpx


class BotApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    async def _get(self, path: str, **params: Any) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}{path}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base}{path}")
            resp.raise_for_status()
            return resp.json()

    async def get_status(self) -> dict[str, Any]:
        result: dict[str, Any] = await self._get("/api/status")
        return result

    async def get_filters(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = await self._get("/api/filters")
        return result

    async def activate_filter(self, filter_id: int) -> dict[str, Any]:
        result: dict[str, Any] = await self._post(f"/api/filters/{filter_id}/activate")
        return result

    async def deactivate_filter(self, filter_id: int) -> dict[str, Any]:
        result: dict[str, Any] = await self._post(f"/api/filters/{filter_id}/deactivate")
        return result

    async def run_scan(self) -> dict[str, Any]:
        # Scan may take a while — use longer timeout
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base}/api/scan/run")
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result

    async def get_recent_matches(self, limit: int = 5) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = await self._get("/api/matches/recent", limit=limit)
        return result

    async def get_carousel_listing(self, carousel_id: int, idx: int) -> dict[str, Any]:
        result: dict[str, Any] = await self._get(
            f"/api/carousels/{carousel_id}/listings/{idx}"
        )
        return result
