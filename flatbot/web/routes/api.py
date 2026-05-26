"""JSON API router consumed by the bot service (and optionally external clients)."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.db import get_db
from flatbot.integrations.openproperties.client import (
    MockOpenPropertiesClient,
    OpenPropertiesClient,
)
from flatbot.models import Filter
from flatbot.repos import AlertCarouselRepo, FilterRepo, MatchRepo, ScanRunRepo
from flatbot.scanner import run_scan
from flatbot.schemas import FilterRead, ListingRead, ScanRunRead
from flatbot.web.deps import get_alert_sender, get_scan_client

router = APIRouter(prefix="/api")


@router.get("/status")
def api_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    active_count: int = (
        db.execute(select(func.count()).select_from(Filter).where(Filter.is_active.is_(True))).scalar_one()
    )
    latest = ScanRunRepo(db).latest()
    return {
        "active_filters": active_count,
        "last_scan": ScanRunRead.model_validate(latest).model_dump() if latest else None,
    }


@router.get("/filters")
def api_list_filters(db: Session = Depends(get_db)) -> list[FilterRead]:
    return [FilterRead.model_validate(f) for f in FilterRepo(db).list_all()]


@router.post("/filters/{filter_id}/activate")
def api_activate_filter(filter_id: int, db: Session = Depends(get_db)) -> FilterRead:
    from flatbot.schemas import FilterUpdate

    repo = FilterRepo(db)
    if repo.get(filter_id) is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    updated = repo.update(filter_id, FilterUpdate(is_active=True))
    assert updated is not None
    return FilterRead.model_validate(updated)


@router.post("/filters/{filter_id}/deactivate")
def api_deactivate_filter(filter_id: int, db: Session = Depends(get_db)) -> FilterRead:
    from flatbot.schemas import FilterUpdate

    repo = FilterRepo(db)
    if repo.get(filter_id) is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    updated = repo.update(filter_id, FilterUpdate(is_active=False))
    assert updated is not None
    return FilterRead.model_validate(updated)


@router.post("/scan/run")
def api_run_scan(
    db: Session = Depends(get_db),
    client: OpenPropertiesClient | MockOpenPropertiesClient = Depends(get_scan_client),
    sender: AlertSender = Depends(get_alert_sender),
) -> ScanRunRead:
    run = run_scan(db, client, sender)
    return ScanRunRead.model_validate(run)


@router.get("/carousels/{carousel_id}/listings/{idx}")
def api_carousel_listing(
    carousel_id: int, idx: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    repo = AlertCarouselRepo(db)
    carousel = repo.get(carousel_id)
    if carousel is None:
        raise HTTPException(status_code=404, detail="Carousel not found")
    match = repo.get_match_at(carousel_id, idx)
    if match is None:
        raise HTTPException(status_code=404, detail="Index out of range")
    return {
        "carousel_id": carousel.id,
        "filter_name": carousel.filter.name,
        "idx": idx,
        "total": len(carousel.match_ids),
        "listing": ListingRead.model_validate(match.listing).model_dump(mode="json"),
    }


@router.get("/matches/recent")
def api_recent_matches(
    limit: int = 10, db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    matches = MatchRepo(db).list_recent(limit)
    return [
        {
            "id": m.id,
            "filter_id": m.filter_id,
            "filter_name": m.filter.name,
            "listing": ListingRead.model_validate(m.listing).model_dump(mode="json"),
            "matched_at": m.matched_at.isoformat(),
            "notified_at": m.notified_at.isoformat() if m.notified_at else None,
        }
        for m in matches
    ]
