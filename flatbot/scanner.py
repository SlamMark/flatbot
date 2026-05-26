"""F5 — Scan orchestration: fetch → match → dedup → alert → persist."""
import logging
from typing import Protocol

from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.config import settings
from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.matching import evaluate
from flatbot.models import Filter, Listing, Match, ScanRun
from flatbot.repos import FilterRepo, ListingRepo, MatchRepo, ScanRunRepo

logger = logging.getLogger(__name__)


class ListingClient(Protocol):
    """Structural type for anything that can return recent listings for a filter."""

    def fetch_recent(self, f: Filter, hours: int = 6, limit: int = 20) -> list[ListingDTO]: ...


def _dto_to_listing(dto: ListingDTO) -> Listing:
    return Listing(
        property_id=dto.property_id,
        source=dto.source,
        external_id=dto.external_id,
        url=dto.url,
        kind=dto.kind,
        price=dto.price,
        price_per_sqm=dto.price_per_sqm,
        property_type=dto.property_type,
        condition=dto.condition,
        bedrooms=dto.bedrooms,
        bathrooms=dto.bathrooms,
        square_meters=dto.square_meters,
        floor_number=dto.floor_number,
        address=dto.address,
        lat=dto.lat,
        lng=dto.lng,
        amenities=dto.amenities,
        is_agency=dto.is_agency,
        publisher_name=dto.publisher_name,
        photos_amount=dto.photos_amount,
        flag_temporal=dto.flag_temporal,
        flag_ocupada=dto.flag_ocupada,
        flag_alquiler_regulado=dto.flag_alquiler_regulado,
        flag_bare_ownership=dto.flag_bare_ownership,
        llm_summary=dto.llm_summary,
        published_at=dto.published_at,
        last_scraped_at=dto.last_scraped_at,
    )


def _listing_to_dto(listing: Listing) -> ListingDTO:
    return ListingDTO(
        id=listing.property_id,
        property_id=listing.property_id,
        source=listing.source,
        external_id=listing.external_id,
        url=listing.url,
        kind=listing.kind,
        price=listing.price,
        price_per_sqm=listing.price_per_sqm,
        property_type=listing.property_type,
        condition=listing.condition,
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        square_meters=listing.square_meters,
        floor_number=listing.floor_number,
        address=listing.address,
        lat=listing.lat,
        lng=listing.lng,
        amenities=listing.amenities or [],
        is_agency=listing.is_agency,
        publisher_name=listing.publisher_name,
        photos_amount=listing.photos_amount,
        flag_temporal=listing.flag_temporal,
        flag_ocupada=listing.flag_ocupada,
        flag_alquiler_regulado=listing.flag_alquiler_regulado,
        flag_bare_ownership=listing.flag_bare_ownership,
        llm_summary=listing.llm_summary,
        published_at=listing.published_at,
        last_scraped_at=listing.last_scraped_at,
    )


def run_scan(
    db: Session,
    client: ListingClient,
    sender: AlertSender,
) -> ScanRun:
    """Run one full scan cycle. Returns the completed or failed ScanRun record."""
    scan_repo = ScanRunRepo(db)
    filter_repo = FilterRepo(db)
    listing_repo = ListingRepo(db)
    match_repo = MatchRepo(db)

    run = scan_repo.start()
    total_fetched = total_new = total_matches = total_sent = 0

    try:
        for f in filter_repo.list_active():
            try:
                dtos = client.fetch_recent(f, hours=settings.scan_lookback_hours)
                total_fetched += len(dtos)

                to_alert: list[tuple[Match, ListingDTO]] = []
                for dto in dtos:
                    db_listing, created = listing_repo.upsert(_dto_to_listing(dto))
                    if created:
                        total_new += 1
                    if not evaluate(dto, f).matched:
                        continue
                    # Evaluate every fetched listing against the filter. MatchRepo.create
                    # is idempotent on (filter_id, listing_id), so previously-matched
                    # listings won't re-fire — but a freshly added/edited filter will
                    # now match listings already in the DB.
                    match = match_repo.create(f.id, db_listing.id)
                    if match is not None:
                        total_matches += 1
                        to_alert.append((match, dto))

                # Retry matches whose previous send failed (notified_at IS NULL).
                queued_ids = {m.id for m, _ in to_alert}
                for pending in match_repo.list_pending_for_filter(f.id):
                    if pending.id in queued_ids:
                        continue
                    to_alert.append((pending, _listing_to_dto(pending.listing)))

                if to_alert:
                    alert_dtos = [dto for _, dto in to_alert]
                    sent, _ = sender.send_listings(alert_dtos, f.name)
                    total_sent += sent
                    for match, _ in to_alert[:sent]:
                        match_repo.mark_notified(match.id)

            except Exception as exc:
                logger.error("Scan error for filter %d (%s): %s", f.id, f.name, exc)

        result = scan_repo.complete(
            run.id,
            listings_fetched=total_fetched,
            new_listings=total_new,
            matches_found=total_matches,
            alerts_sent=total_sent,
        )
        return result if result is not None else run

    except Exception as exc:
        logger.exception("Scan run %d failed: %s", run.id, exc)
        failed = scan_repo.fail(run.id, str(exc))
        return failed if failed is not None else run
