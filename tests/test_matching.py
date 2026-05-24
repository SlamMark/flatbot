"""Unit tests for the matching engine (F3)."""
from datetime import datetime, timezone

from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.matching import MatchResult, evaluate
from flatbot.models import Filter


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _listing(**overrides) -> ListingDTO:
    defaults = dict(
        id="abc",
        property_id="prop-1",
        source="idealista",
        external_id="123",
        url="https://example.com",
        kind="rent",
        price=1200,
        price_per_sqm=12.0,
        property_type="flat",
        condition="good",
        bedrooms=3,
        bathrooms=1,
        square_meters=80,
        floor_number=2,
        address="Calle Test, 1",
        lat=41.38,
        lng=2.17,
        amenities=["elevator"],
        is_agency=False,
        publisher_name=None,
        photos_amount=5,
        image_urls=[],
        flag_temporal=False,
        flag_ocupada=False,
        flag_alquiler_regulado=False,
        flag_bare_ownership=False,
        llm_summary="summary",
        hours_ago=2,
        published_at=_dt(),
        last_scraped_at=_dt(),
    )
    defaults.update(overrides)
    return ListingDTO(**defaults)


def _filter(**overrides) -> Filter:
    f = Filter()
    f.id = 1
    f.name = "test"
    f.is_active = True
    f.lat = 41.38
    f.lng = 2.17
    f.radius_km = 2.0
    f.kind = "rent"
    f.property_type = None
    f.source = None
    f.min_price = None
    f.max_price = None
    f.min_rooms = None
    f.max_rooms = None
    f.min_sqm = None
    f.max_sqm = None
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
    for k, v in overrides.items():
        setattr(f, k, v)
    return f


class TestKindFilter:
    def test_same_kind_matches(self) -> None:
        assert evaluate(_listing(kind="rent"), _filter(kind="rent")).matched

    def test_different_kind_no_match(self) -> None:
        result = evaluate(_listing(kind="sale"), _filter(kind="rent"))
        assert not result.matched


class TestPriceFilter:
    def test_within_range_matches(self) -> None:
        result = evaluate(_listing(price=1000), _filter(min_price=800, max_price=1200))
        assert result.matched

    def test_below_min_no_match(self) -> None:
        assert not evaluate(_listing(price=700), _filter(min_price=800)).matched

    def test_above_max_no_match(self) -> None:
        assert not evaluate(_listing(price=1500), _filter(max_price=1200)).matched

    def test_no_price_filter_always_matches(self) -> None:
        assert evaluate(_listing(price=9999), _filter()).matched


class TestRoomsFilter:
    def test_enough_rooms_matches(self) -> None:
        assert evaluate(_listing(bedrooms=3), _filter(min_rooms=2)).matched

    def test_too_few_rooms_no_match(self) -> None:
        assert not evaluate(_listing(bedrooms=1), _filter(min_rooms=2)).matched

    def test_too_many_rooms_no_match(self) -> None:
        assert not evaluate(_listing(bedrooms=5), _filter(max_rooms=4)).matched

    def test_null_bedrooms_skips_filter(self) -> None:
        assert evaluate(_listing(bedrooms=None), _filter(min_rooms=2)).matched


class TestSqmFilter:
    def test_within_sqm_range_matches(self) -> None:
        assert evaluate(_listing(square_meters=80), _filter(min_sqm=60, max_sqm=100)).matched

    def test_too_small_no_match(self) -> None:
        assert not evaluate(_listing(square_meters=50), _filter(min_sqm=60)).matched


class TestSourceFilter:
    def test_source_match(self) -> None:
        assert evaluate(_listing(source="idealista"), _filter(source="idealista")).matched

    def test_source_mismatch(self) -> None:
        assert not evaluate(_listing(source="fotocasa"), _filter(source="idealista")).matched

    def test_no_source_filter_matches_any(self) -> None:
        assert evaluate(_listing(source="fotocasa"), _filter()).matched


class TestPropertyTypeFilter:
    def test_type_match(self) -> None:
        assert evaluate(_listing(property_type="flat"), _filter(property_type="flat")).matched

    def test_type_mismatch(self) -> None:
        assert not evaluate(_listing(property_type="house"), _filter(property_type="flat")).matched


class TestThreeStateFilters:
    def test_any_always_passes(self) -> None:
        assert evaluate(_listing(flag_temporal=True), _filter(temporal="any")).matched

    def test_only_requires_true(self) -> None:
        assert evaluate(_listing(flag_temporal=True), _filter(temporal="only")).matched
        assert not evaluate(_listing(flag_temporal=False), _filter(temporal="only")).matched

    def test_exclude_requires_false(self) -> None:
        assert evaluate(_listing(flag_temporal=False), _filter(temporal="exclude")).matched
        assert not evaluate(_listing(flag_temporal=True), _filter(temporal="exclude")).matched

    def test_ocupada_exclude(self) -> None:
        assert not evaluate(_listing(flag_ocupada=True), _filter(ocupada="exclude")).matched


class TestAmenityFilters:
    def test_yes_requires_amenity_present(self) -> None:
        assert evaluate(_listing(amenities=["elevator"]), _filter(elevator="yes")).matched
        assert not evaluate(_listing(amenities=[]), _filter(elevator="yes")).matched

    def test_no_requires_amenity_absent(self) -> None:
        assert evaluate(_listing(amenities=[]), _filter(elevator="no")).matched
        assert not evaluate(_listing(amenities=["elevator"]), _filter(elevator="no")).matched

    def test_any_ignores_amenity(self) -> None:
        assert evaluate(_listing(amenities=[]), _filter(elevator="any")).matched
        assert evaluate(_listing(amenities=["elevator"]), _filter(elevator="any")).matched


class TestScoring:
    def test_score_increases_with_optional_criteria(self) -> None:
        r1 = evaluate(_listing(bedrooms=3, square_meters=80, llm_summary="s"), _filter())
        r2 = evaluate(_listing(bedrooms=None, square_meters=None, llm_summary=None), _filter())
        assert r1.score > r2.score

    def test_no_match_score_is_zero(self) -> None:
        result = evaluate(_listing(kind="sale"), _filter(kind="rent"))
        assert result.score == 0


class TestMatchResult:
    def test_returns_match_result(self) -> None:
        assert isinstance(evaluate(_listing(), _filter()), MatchResult)

    def test_reasons_non_empty_on_match(self) -> None:
        result = evaluate(_listing(), _filter())
        assert len(result.reasons) > 0

    def test_reasons_contain_failure_on_no_match(self) -> None:
        result = evaluate(_listing(price=5000), _filter(max_price=1000))
        assert any("price" in r for r in result.reasons)
