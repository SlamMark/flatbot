"""Smoke tests for the web portal (F6)."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.db import get_db
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.models import Filter
from flatbot.web.app import app
from flatbot.web.deps import get_alert_sender, get_scan_client


class _FakeSender(AlertSender):
    def __init__(self) -> None:
        super().__init__(bot_token="x", chat_id="x")

    def send(self, text: str) -> bool:
        return True


class _EmptyClient:
    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        return []


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


class TestDashboard:
    def test_dashboard_returns_200(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "FlatBot" in resp.text

    def test_scan_trigger_returns_html(self, client: TestClient) -> None:
        resp = client.post("/internal/scan/run")
        assert resp.status_code == 200
        assert "completed" in resp.text or "failed" in resp.text

    def test_health_still_works(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"status": "ok"}


class TestFilterCRUD:
    def test_filter_list_empty(self, client: TestClient) -> None:
        resp = client.get("/filters")
        assert resp.status_code == 200
        assert "FlatBot" in resp.text

    def test_filter_new_form(self, client: TestClient) -> None:
        resp = client.get("/filters/new")
        assert resp.status_code == 200
        assert "Nuevo filtro" in resp.text

    def test_filter_create_redirects(self, client: TestClient) -> None:
        resp = client.post(
            "/filters",
            data={"name": "Mi filtro", "lat": "41.38", "lng": "2.17",
                  "radius_km": "2", "kind": "rent", "is_active": "on"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/filters"

    def test_filter_appears_in_list_after_create(self, client: TestClient) -> None:
        client.post(
            "/filters",
            data={"name": "Mi filtro", "lat": "41.38", "lng": "2.17",
                  "radius_km": "2", "kind": "rent"},
        )
        resp = client.get("/filters")
        assert "Mi filtro" in resp.text

    def test_filter_edit_form(self, client: TestClient, db: Session) -> None:
        f = Filter()
        f.name = "edit-me"
        f.is_active = True
        f.lat = 41.0
        f.lng = 2.0
        f.radius_km = 1.0
        f.kind = "rent"
        f.temporal = "any"
        f.ocupada = "any"
        f.alquiler_regulado = "any"
        f.nuda_propiedad = "any"
        f.elevator = "any"
        f.furnished = "any"
        f.garage = "any"
        f.terrace = "any"
        f.balcony = "any"
        f.pets_allowed = "any"
        db.add(f)
        db.commit()
        db.refresh(f)

        resp = client.get(f"/filters/{f.id}/edit")
        assert resp.status_code == 200
        assert "edit-me" in resp.text

    def test_filter_edit_404_for_missing(self, client: TestClient) -> None:
        assert client.get("/filters/9999/edit").status_code == 404

    def test_filter_toggle(self, client: TestClient, db: Session) -> None:
        f = Filter()
        f.name = "toggle-me"
        f.is_active = True
        f.lat = 41.0
        f.lng = 2.0
        f.radius_km = 1.0
        f.kind = "rent"
        f.temporal = f.ocupada = f.alquiler_regulado = f.nuda_propiedad = "any"
        f.elevator = f.furnished = f.garage = f.terrace = f.balcony = f.pets_allowed = "any"
        db.add(f)
        db.commit()
        db.refresh(f)

        resp = client.post(f"/filters/{f.id}/toggle")
        assert resp.status_code == 200
        assert "inactivo" in resp.text  # was active, now inactive

    def test_filter_delete(self, client: TestClient, db: Session) -> None:
        f = Filter()
        f.name = "del-me"
        f.is_active = True
        f.lat = 41.0
        f.lng = 2.0
        f.radius_km = 1.0
        f.kind = "rent"
        f.temporal = f.ocupada = f.alquiler_regulado = f.nuda_propiedad = "any"
        f.elevator = f.furnished = f.garage = f.terrace = f.balcony = f.pets_allowed = "any"
        db.add(f)
        db.commit()
        db.refresh(f)

        resp = client.delete(f"/filters/{f.id}")
        assert resp.status_code == 200
        assert db.get(Filter, f.id) is None


class TestConfig:
    def test_config_page(self, client: TestClient) -> None:
        resp = client.get("/config")
        assert resp.status_code == 200
        assert "scan_interval_minutes" in resp.text
