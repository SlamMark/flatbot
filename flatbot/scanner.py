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

                new_matches: list[tuple[Match, ListingDTO]] = []
                for dto in dtos:
                    db_listing, created = listing_repo.upsert(_dto_to_listing(dto))
                    if not created:
                        continue
                    total_new += 1
                    if not evaluate(dto, f).matched:
                        continue
                    match = match_repo.create(f.id, db_listing.id)
                    if match is not None:
                        total_matches += 1
                        new_matches.append((match, dto))

                if new_matches:
                    alert_dtos = [dto for _, dto in new_matches]
                    sent, _ = sender.send_listings(alert_dtos, f.name)
                    total_sent += sent
                    for match, _ in new_matches[:sent]:
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
