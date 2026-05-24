"""Contract tests for the OpenProperties integration.

These tests validate that the mapper and query builder work correctly against
the real API fixture — no network calls, no quota consumed.
"""
import json
from datetime import timezone
from pathlib import Path

import pytest

from flatbot.integrations.openproperties.client import MockOpenPropertiesClient
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.integrations.openproperties.mapper import map_listing, map_listings
from flatbot.integrations.openproperties.query_builder import (
    build_listings_params,
    build_recent_params,
)
from flatbot.models import Filter

FIXTURE = Path(__file__).parent / "fixtures" / "openproperties_listings.json"


@pytest.fixture
def raw_listings() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["data"]


@pytest.fixture
def first_raw(raw_listings: list[dict]) -> dict:
    return raw_listings[0]


@pytest.fixture
def minimal_filter() -> Filter:
    f = Filter()
    f.id = 1
    f.name = "test"
    f.is_active = True
    f.lat = 41.3851
    f.lng = 2.1734
    f.radius_km = 3.0
    f.kind = "rent"
    f.property_type = None
    f.source = None
    f.min_price = None
    f.max_price = 1500
    f.min_rooms = 2
    f.max_rooms = None
    f.min_sqm = None
    f.max_sqm = None
    f.ocupada = "any"
    f.nuda_propiedad = "any"
    f.elevator = "any"
    f.furnished = "any"
    f.garage = "any"
    f.terrace = "any"
    f.balcony = "any"
    f.pets_allowed = "any"
    return f


# ---------------------------------------------------------------------------
# Mapper contract tests
# ---------------------------------------------------------------------------


class TestMapListing:
    def test_maps_required_string_fields(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert dto.id == first_raw["id"]
        assert dto.property_id == first_raw["propertyId"]
        assert dto.source == first_raw["source"]
        assert dto.external_id == first_raw["externalId"]
        assert dto.url == first_raw["url"]
        assert dto.kind == first_raw["kind"]

    def test_maps_price(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert dto.price == first_raw["price"]
        assert isinstance(dto.price, int)
        assert isinstance(dto.price_per_sqm, float)

    def test_maps_coordinates(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert dto.lat == first_raw["coordinates"]["lat"]
        assert dto.lng == first_raw["coordinates"]["lng"]

    def test_maps_flags(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        flags = first_raw["flags"]
        assert dto.flag_temporal == flags["isTemporal"]
        assert dto.flag_ocupada == flags["isOkupada"]
        assert dto.flag_alquiler_regulado == flags["isAlquilerRegulado"]
        assert dto.flag_bare_ownership == flags["isBareOwnership"]

    def test_maps_datetimes_as_utc(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert dto.published_at.tzinfo == timezone.utc
        assert dto.last_scraped_at.tzinfo == timezone.utc

    def test_maps_amenities_as_list(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert isinstance(dto.amenities, list)

    def test_maps_nullable_floor(self, raw_listings: list[dict]) -> None:
        # second fixture listing has floorNumber=null
        dto = map_listing(raw_listings[1])
        assert dto.floor_number is None

    def test_returns_listing_dto(self, first_raw: dict) -> None:
        dto = map_listing(first_raw)
        assert isinstance(dto, ListingDTO)

    def test_map_listings_batch(self, raw_listings: list[dict]) -> None:
        dtos = map_listings(raw_listings)
        assert len(dtos) == len(raw_listings)
        assert all(isinstance(d, ListingDTO) for d in dtos)


# ---------------------------------------------------------------------------
# Query builder contract tests
# ---------------------------------------------------------------------------


class TestBuildListingsParams:
    def test_required_geo_params(self, minimal_filter: Filter) -> None:
        params = build_listings_params(minimal_filter)
        assert params["lat"] == minimal_filter.lat
        assert params["lng"] == minimal_filter.lng
        assert params["radiusKm"] == minimal_filter.radius_km
        assert params["kind"] == minimal_filter.kind

    def test_optional_price_room_params(self, minimal_filter: Filter) -> None:
        params = build_listings_params(minimal_filter)
        assert "maxPrice" in params
        assert params["maxPrice"] == 1500
        assert "minRooms" in params
        assert params["minRooms"] == 2
        assert "minPrice" not in params

    def test_any_filters_omitted(self, minimal_filter: Filter) -> None:
        params = build_listings_params(minimal_filter)
        for key in ("ocupada", "nudaPropiedad",
                    "elevator", "furnished", "garage", "terrace", "balcony", "petsAllowed"):
            assert key not in params

    def test_non_any_filter_included(self, minimal_filter: Filter) -> None:
        minimal_filter.elevator = "only"
        minimal_filter.ocupada = "exclude"
        params = build_listings_params(minimal_filter)
        assert params["elevator"] == "only"
        assert params["ocupada"] == "exclude"

    def test_pagination_defaults(self, minimal_filter: Filter) -> None:
        params = build_listings_params(minimal_filter)
        assert params["page"] == 1
        assert params["pageSize"] == 20

    def test_max_age_days_optional(self, minimal_filter: Filter) -> None:
        params = build_listings_params(minimal_filter, max_age_days=7)
        assert params["maxAgeDays"] == 7


class TestBuildRecentParams:
    def test_includes_hours_and_limit(self, minimal_filter: Filter) -> None:
        params = build_recent_params(minimal_filter, hours=6, limit=20)
        assert params["hours"] == 6
        assert params["limit"] == 20

    def test_includes_geo(self, minimal_filter: Filter) -> None:
        params = build_recent_params(minimal_filter)
        assert "lat" in params
        assert "lng" in params
        assert "radiusKm" in params


# ---------------------------------------------------------------------------
# MockOpenPropertiesClient smoke test
# ---------------------------------------------------------------------------


class TestMockClient:
    def test_fetch_recent_returns_dtos(self, minimal_filter: Filter) -> None:
        client = MockOpenPropertiesClient(fixture_path=FIXTURE)
        dtos = client.fetch_recent(minimal_filter)
        assert len(dtos) > 0
        assert all(isinstance(d, ListingDTO) for d in dtos)

    def test_fetch_listings_returns_dtos_and_meta(self, minimal_filter: Filter) -> None:
        client = MockOpenPropertiesClient(fixture_path=FIXTURE)
        dtos, meta = client.fetch_listings(minimal_filter)
        assert len(dtos) > 0
        assert isinstance(meta, dict)
        assert "total" in meta

    def test_fetch_listing_by_id(self, minimal_filter: Filter, first_raw: dict) -> None:
        client = MockOpenPropertiesClient(fixture_path=FIXTURE)
        detail = client.fetch_listing(first_raw["id"])
        assert detail["propertyId"] == first_raw["propertyId"]

    def test_fetch_listing_unknown_id_returns_empty(self, minimal_filter: Filter) -> None:
        client = MockOpenPropertiesClient(fixture_path=FIXTURE)
        assert client.fetch_listing("nonexistent-id") == {}
