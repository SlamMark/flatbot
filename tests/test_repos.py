from datetime import datetime, timezone

from sqlalchemy.orm import Session

from flatbot.models import Listing
from flatbot.repos import (
    AlertCarouselRepo,
    FilterRepo,
    ListingRepo,
    MatchRepo,
    ScanRunRepo,
)
from flatbot.schemas import FilterCreate, FilterUpdate
from flatbot.services.settings import SettingsService


def _filter(**kwargs) -> FilterCreate:
    return FilterCreate(
        **{"name": "Test", "lat": 41.385, "lng": 2.173, "radius_km": 2.0, "kind": "rent", **kwargs}
    )


def _listing(property_id: str = "prop-001") -> Listing:
    now = datetime.now(timezone.utc)
    return Listing(
        property_id=property_id,
        source="idealista",
        external_id="123456",
        url="https://www.idealista.com/inmueble/123456/",
        kind="rent",
        price=1200,
        property_type="flat",
        address="Calle Verdi, 12, Gràcia",
        published_at=now,
        last_scraped_at=now,
    )


class TestFilterRepo:
    def test_create_and_get(self, db: Session) -> None:
        repo = FilterRepo(db)
        f = repo.create(_filter())
        assert f.id is not None
        assert repo.get(f.id) == f

    def test_list_active_excludes_inactive(self, db: Session) -> None:
        repo = FilterRepo(db)
        repo.create(_filter(name="Active"))
        repo.create(_filter(name="Inactive", is_active=False))
        active = repo.list_active()
        assert len(active) == 1
        assert active[0].name == "Active"

    def test_update_fields(self, db: Session) -> None:
        repo = FilterRepo(db)
        f = repo.create(_filter())
        updated = repo.update(f.id, FilterUpdate(max_price=1500, is_active=False))
        assert updated is not None
        assert updated.max_price == 1500
        assert updated.is_active is False

    def test_update_nonexistent_returns_none(self, db: Session) -> None:
        assert FilterRepo(db).update(9999, FilterUpdate(name="x")) is None

    def test_delete(self, db: Session) -> None:
        repo = FilterRepo(db)
        f = repo.create(_filter())
        assert repo.delete(f.id) is True
        assert repo.get(f.id) is None

    def test_delete_nonexistent_returns_false(self, db: Session) -> None:
        assert FilterRepo(db).delete(9999) is False


class TestListingRepo:
    def test_upsert_creates_new(self, db: Session) -> None:
        _, created = ListingRepo(db).upsert(_listing())
        assert created is True

    def test_upsert_updates_price(self, db: Session) -> None:
        repo = ListingRepo(db)
        repo.upsert(_listing("prop-001"))
        newer = _listing("prop-001")
        newer.price = 999
        _, created = repo.upsert(newer)
        assert created is False
        stored = repo.get_by_property_id("prop-001")
        assert stored is not None and stored.price == 999

    def test_get_by_property_id_missing(self, db: Session) -> None:
        assert ListingRepo(db).get_by_property_id("missing") is None


class TestMatchRepo:
    def test_create_and_exists(self, db: Session) -> None:
        f = FilterRepo(db).create(_filter())
        listing, _ = ListingRepo(db).upsert(_listing())
        repo = MatchRepo(db)
        m = repo.create(f.id, listing.id)
        assert m is not None
        assert repo.exists(f.id, listing.id)

    def test_no_duplicate_match(self, db: Session) -> None:
        f = FilterRepo(db).create(_filter())
        listing, _ = ListingRepo(db).upsert(_listing())
        repo = MatchRepo(db)
        repo.create(f.id, listing.id)
        assert repo.create(f.id, listing.id) is None

    def test_mark_notified_clears_pending(self, db: Session) -> None:
        f = FilterRepo(db).create(_filter())
        listing, _ = ListingRepo(db).upsert(_listing())
        repo = MatchRepo(db)
        m = repo.create(f.id, listing.id)
        assert m is not None
        assert len(repo.list_pending()) == 1
        repo.mark_notified(m.id)
        assert len(repo.list_pending()) == 0


class TestScanRunRepo:
    def test_full_lifecycle(self, db: Session) -> None:
        repo = ScanRunRepo(db)
        run = repo.start()
        assert run.status == "running"
        assert run.finished_at is None

        done = repo.complete(run.id, listings_fetched=10, new_listings=3, matches_found=2)
        assert done is not None
        assert done.status == "completed"
        assert done.listings_fetched == 10
        assert done.finished_at is not None

    def test_fail(self, db: Session) -> None:
        repo = ScanRunRepo(db)
        run = repo.start()
        failed = repo.fail(run.id, "timeout")
        assert failed is not None
        assert failed.status == "failed"
        assert failed.error_message == "timeout"

    def test_latest(self, db: Session) -> None:
        repo = ScanRunRepo(db)
        repo.start()
        run2 = repo.start()
        latest = repo.latest()
        assert latest is not None and latest.id == run2.id


class TestAlertCarouselRepo:
    def test_create_and_get_match_at(self, db: Session) -> None:
        f = FilterRepo(db).create(_filter())
        l1, _ = ListingRepo(db).upsert(_listing("p1"))
        l2, _ = ListingRepo(db).upsert(_listing("p2"))
        m1 = MatchRepo(db).create(f.id, l1.id)
        m2 = MatchRepo(db).create(f.id, l2.id)
        assert m1 is not None and m2 is not None

        repo = AlertCarouselRepo(db)
        c = repo.create(
            chat_id="123", message_id=42, filter_id=f.id, match_ids=[m1.id, m2.id]
        )
        assert c.id is not None
        assert repo.get(c.id) == c
        assert repo.get_match_at(c.id, 0) == m1
        assert repo.get_match_at(c.id, 1) == m2

    def test_get_match_at_out_of_range(self, db: Session) -> None:
        f = FilterRepo(db).create(_filter())
        listing, _ = ListingRepo(db).upsert(_listing())
        m = MatchRepo(db).create(f.id, listing.id)
        assert m is not None

        repo = AlertCarouselRepo(db)
        c = repo.create(chat_id="c", message_id=1, filter_id=f.id, match_ids=[m.id])
        assert repo.get_match_at(c.id, -1) is None
        assert repo.get_match_at(c.id, 5) is None

    def test_get_missing_returns_none(self, db: Session) -> None:
        assert AlertCarouselRepo(db).get(9999) is None


class TestSettingsService:
    def test_default_value(self, db: Session) -> None:
        assert SettingsService(db).get_int("scan_interval_minutes") == 30

    def test_override_and_read(self, db: Session) -> None:
        svc = SettingsService(db)
        svc.set("scan_interval_minutes", "15")
        assert svc.get_int("scan_interval_minutes") == 15

    def test_all_includes_defaults(self, db: Session) -> None:
        result = SettingsService(db).all()
        assert "scan_interval_minutes" in result
