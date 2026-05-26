from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from flatbot.models import Filter, Listing, Match, ScanRun
from flatbot.schemas import FilterCreate, FilterUpdate


class FilterRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: FilterCreate) -> Filter:
        f = Filter(**data.model_dump())
        self.db.add(f)
        self.db.commit()
        self.db.refresh(f)
        return f

    def get(self, filter_id: int) -> Filter | None:
        return self.db.get(Filter, filter_id)

    def list_all(self) -> list[Filter]:
        return list(self.db.execute(select(Filter)).scalars())

    def list_active(self) -> list[Filter]:
        return list(self.db.execute(select(Filter).where(Filter.is_active.is_(True))).scalars())

    def update(self, filter_id: int, data: FilterUpdate) -> Filter | None:
        f = self.db.get(Filter, filter_id)
        if f is None:
            return None
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(f, key, value)
        f.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(f)
        return f

    def delete(self, filter_id: int) -> bool:
        f = self.db.get(Filter, filter_id)
        if f is None:
            return False
        self.db.delete(f)
        self.db.commit()
        return True


class ListingRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_property_id(self, property_id: str) -> Listing | None:
        return self.db.execute(
            select(Listing).where(Listing.property_id == property_id)
        ).scalar_one_or_none()

    def upsert(self, listing: Listing) -> tuple[Listing, bool]:
        """Returns (listing, created). Updates mutable fields if already exists."""
        existing = self.get_by_property_id(listing.property_id)
        if existing is not None:
            existing.price = listing.price
            existing.price_per_sqm = listing.price_per_sqm
            existing.last_scraped_at = listing.last_scraped_at
            existing.llm_summary = listing.llm_summary
            existing.amenities = listing.amenities
            self.db.commit()
            self.db.refresh(existing)
            return existing, False
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing, True

    def get_recent(self, limit: int = 50) -> list[Listing]:
        return list(
            self.db.execute(
                select(Listing).order_by(Listing.first_seen_at.desc()).limit(limit)
            ).scalars()
        )


class MatchRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, filter_id: int, listing_id: int) -> bool:
        return (
            self.db.execute(
                select(Match).where(Match.filter_id == filter_id, Match.listing_id == listing_id)
            ).scalar_one_or_none()
            is not None
        )

    def create(self, filter_id: int, listing_id: int) -> Match | None:
        """Returns None if the match already exists (idempotent)."""
        if self.exists(filter_id, listing_id):
            return None
        m = Match(filter_id=filter_id, listing_id=listing_id)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def mark_notified(self, match_id: int) -> None:
        m = self.db.get(Match, match_id)
        if m is not None:
            m.notified_at = datetime.now(timezone.utc)
            self.db.commit()

    def list_pending(self) -> list[Match]:
        return list(
            self.db.execute(select(Match).where(Match.notified_at.is_(None))).scalars()
        )

    def list_pending_for_filter(self, filter_id: int) -> list[Match]:
        return list(
            self.db.execute(
                select(Match).where(
                    Match.filter_id == filter_id,
                    Match.notified_at.is_(None),
                )
            ).scalars()
        )

    def list_recent(self, limit: int = 10) -> list[Match]:
        return list(
            self.db.execute(
                select(Match).order_by(Match.matched_at.desc()).limit(limit)
            ).scalars()
        )


class ScanRunRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start(self) -> ScanRun:
        run = ScanRun(status="running")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def complete(self, run_id: int, **stats: int) -> ScanRun | None:
        run = self.db.get(ScanRun, run_id)
        if run is None:
            return None
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        for key, value in stats.items():
            if hasattr(run, key):
                setattr(run, key, value)
        self.db.commit()
        self.db.refresh(run)
        return run

    def fail(self, run_id: int, error: str) -> ScanRun | None:
        run = self.db.get(ScanRun, run_id)
        if run is None:
            return None
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = error
        self.db.commit()
        self.db.refresh(run)
        return run

    def latest(self) -> ScanRun | None:
        return self.db.execute(
            select(ScanRun).order_by(ScanRun.started_at.desc()).limit(1)
        ).scalar_one_or_none()
