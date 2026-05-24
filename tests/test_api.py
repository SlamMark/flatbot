"""Tests for the JSON API router (F7 — consumed by the bot service)."""
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.db import get_db
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.models import Filter, Listing, Match
from flatbot.web.app import app
from flatbot.web.deps import get_alert_sender, get_scan_client


class _EmptyClient:
    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        return []


class _FakeSender(AlertSender):
    def __init__(self) -> None:
        super().__init__(bot_token="x", chat_id="x")

    def send(self, text: str) -> bool:
        return True


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def _db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_scan_client] = lambda: _EmptyClient()
    app.dependency_overrides[get_alert_sender] = lambda: _FakeSender()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _add_filter(db: Session, name: str = "test", is_active: bool = True) -> Filter:
    f = Filter()
    f.name = name
    f.is_active = is_active
    f.lat = 41.38
    f.lng = 2.17
    f.radius_km = 2.0
    f.kind = "rent"
    f.temporal = f.ocupada = f.alquiler_regulado = f.nuda_propiedad = "any"
    f.elevator = f.furnished = f.garage = f.terrace = f.balcony = f.pets_allowed = "any"
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _add_listing(db: Session, property_id: str = "p1") -> Listing:
    now = datetime.now(timezone.utc)
    lst = Listing(
        property_id=property_id, source="idealista", external_id="x",
        url="https://example.com", kind="rent", price=1200, property_type="flat",
        address="Test", published_at=now, last_scraped_at=now,
        flag_temporal=False, flag_ocupada=False,
        flag_alquiler_regulado=False, flag_bare_ownership=False,
    )
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return lst


class TestApiStatus:
    def test_returns_active_count(self, client: TestClient, db: Session) -> None:
        _add_filter(db, "f1", is_active=True)
        _add_filter(db, "f2", is_active=False)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["active_filters"] == 1

    def test_no_scan_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/status")
        assert resp.json()["last_scan"] is None


class TestApiFilters:
    def test_empty_list(self, client: TestClient) -> None:
        assert client.get("/api/filters").json() == []

    def test_returns_all_filters(self, client: TestClient, db: Session) -> None:
        _add_filter(db, "a")
        _add_filter(db, "b")
        data = client.get("/api/filters").json()
        assert len(data) == 2

    def test_activate_sets_active(self, client: TestClient, db: Session) -> None:
        f = _add_filter(db, is_active=False)
        resp = client.post(f"/api/filters/{f.id}/activate")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    def test_deactivate_sets_inactive(self, client: TestClient, db: Session) -> None:
        f = _add_filter(db)
        resp = client.post(f"/api/filters/{f.id}/deactivate")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_activate_404_for_missing(self, client: TestClient) -> None:
        assert client.post("/api/filters/9999/activate").status_code == 404

    def test_deactivate_404_for_missing(self, client: TestClient) -> None:
        assert client.post("/api/filters/9999/deactivate").status_code == 404


class TestApiScanRun:
    def test_returns_scan_run(self, client: TestClient) -> None:
        resp = client.post("/api/scan/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "listings_fetched" in data


class TestApiRecentMatches:
    def test_empty_returns_list(self, client: TestClient) -> None:
        assert client.get("/api/matches/recent").json() == []

    def test_returns_match_with_listing_and_filter(
        self, client: TestClient, db: Session
    ) -> None:
        f = _add_filter(db, "mi filtro")
        lst = _add_listing(db)
        m = Match(filter_id=f.id, listing_id=lst.id)
        db.add(m)
        db.commit()

        data = client.get("/api/matches/recent").json()
        assert len(data) == 1
        assert data[0]["filter_name"] == "mi filtro"
        assert data[0]["listing"]["property_id"] == "p1"

    def test_limit_param(self, client: TestClient, db: Session) -> None:
        f = _add_filter(db)
        for i in range(5):
            lst = _add_listing(db, property_id=f"p{i}")
            db.add(Match(filter_id=f.id, listing_id=lst.id))
        db.commit()

        data = client.get("/api/matches/recent?limit=3").json()
        assert len(data) == 3
