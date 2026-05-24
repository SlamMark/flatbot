"""End-to-end tests for the scan orchestration (F5)."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.models import Filter
from flatbot.scanner import run_scan


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _dto(**overrides: object) -> ListingDTO:
    defaults: dict[str, object] = dict(
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
    return ListingDTO(**defaults)  # type: ignore[arg-type]


class _FakeClient:
    def __init__(self, dtos: list[ListingDTO]) -> None:
        self._dtos = dtos

    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]:
        return self._dtos


class _FakeSender(AlertSender):
    def __init__(self) -> None:
        super().__init__(bot_token="fake", chat_id="fake")
        self.sent: list[str] = []

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


def _add_filter(db: Session, **overrides: object) -> Filter:
    f = Filter()
    f.name = "test"
    f.is_active = True
    f.lat = 41.38
    f.lng = 2.17
    f.radius_km = 2.0
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
    for k, v in overrides.items():
        setattr(f, k, v)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


class TestRunScan:
    def test_new_listing_creates_match_and_sends_alert(self, db: Session) -> None:
        _add_filter(db)
        run = run_scan(db, _FakeClient([_dto()]), _FakeSender())

        assert run.status == "completed"
        assert run.listings_fetched == 1
        assert run.new_listings == 1
        assert run.matches_found == 1
        assert run.alerts_sent == 1

    def test_duplicate_listing_not_re_alerted(self, db: Session) -> None:
        _add_filter(db)
        sender = _FakeSender()
        client = _FakeClient([_dto(property_id="prop-dup")])

        run_scan(db, client, sender)  # first scan — persists listing
        run2 = run_scan(db, client, sender)  # second scan — same property_id

        assert run2.new_listings == 0
        assert run2.alerts_sent == 0
        assert len(sender.sent) == 1  # only from the first scan

    def test_non_matching_listing_not_alerted(self, db: Session) -> None:
        _add_filter(db, max_price=1000)  # listing price is 1200
        sender = _FakeSender()

        run = run_scan(db, _FakeClient([_dto(price=1200)]), sender)

        assert run.new_listings == 1  # listing was saved
        assert run.matches_found == 0
        assert run.alerts_sent == 0
        assert sender.sent == []

    def test_empty_fetch_returns_completed_run(self, db: Session) -> None:
        _add_filter(db)
        run = run_scan(db, _FakeClient([]), _FakeSender())

        assert run.status == "completed"
        assert run.listings_fetched == 0
        assert run.alerts_sent == 0

    def test_no_active_filters_does_nothing(self, db: Session) -> None:
        _add_filter(db, is_active=False)
        run = run_scan(db, _FakeClient([_dto()]), _FakeSender())

        assert run.status == "completed"
        assert run.listings_fetched == 0

    def test_multiple_filters_receive_alerts(self, db: Session) -> None:
        _add_filter(db, name="f1")
        _add_filter(db, name="f2")
        sender = _FakeSender()

        run = run_scan(
            db,
            _FakeClient([_dto(property_id="p1"), _dto(property_id="p2")]),
            sender,
        )

        assert run.listings_fetched == 4  # 2 dtos × 2 filters
        assert run.new_listings == 2  # deduped: only new on first filter encounter
        assert run.matches_found == 2  # only matched by the filter that first fetched them
        assert run.alerts_sent > 0
