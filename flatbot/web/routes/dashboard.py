"""Dashboard routes — home page and manual scan trigger."""
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.db import get_db
from flatbot.integrations.openproperties.client import (
    MockOpenPropertiesClient,
    OpenPropertiesClient,
)
from flatbot.models import Filter, ScanRun
from flatbot.scanner import run_scan
from flatbot.web.deps import get_alert_sender, get_scan_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    active_count = db.execute(
        select(Filter).where(Filter.is_active.is_(True))
    ).scalars().all().__len__()

    scan_runs = list(
        db.execute(select(ScanRun).order_by(ScanRun.started_at.desc()).limit(20)).scalars()
    )
    last_scan = scan_runs[0].started_at if scan_runs else None

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"active_count": active_count, "scan_runs": scan_runs, "last_scan": last_scan},
    )


@router.post("/internal/scan/run", response_class=HTMLResponse)
def trigger_scan(
    request: Request,
    db: Session = Depends(get_db),
    client: OpenPropertiesClient | MockOpenPropertiesClient = Depends(get_scan_client),
    sender: AlertSender = Depends(get_alert_sender),
) -> HTMLResponse:
    run = run_scan(db, client, sender)
    html = (
        f'<div class="alert alert-{"success" if run.status == "completed" else "danger"}">'
        f"Scan {run.status}: {run.new_listings} nuevos, {run.matches_found} matches, "
        f"{run.alerts_sent} enviados."
        f"</div>"
    )
    return HTMLResponse(html)
