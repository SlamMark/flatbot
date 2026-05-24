"""Filter CRUD routes with HTMX-friendly partials."""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from flatbot.alerts import AlertSender
from flatbot.db import get_db
from flatbot.integrations.openproperties.client import (
    MockOpenPropertiesClient,
    OpenPropertiesClient,
)
from flatbot.matching import evaluate
from flatbot.repos import FilterRepo
from flatbot.schemas import FilterCreate
from flatbot.web.deps import get_alert_sender, get_scan_client

router = APIRouter(prefix="/filters")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _int_or_none(val: str | None) -> int | None:
    if val is None or val.strip() == "":
        return None
    return int(val)


def _str_or_none(val: str | None) -> str | None:
    if val is None or val.strip() == "":
        return None
    return val.strip()


async def _parse_filter_form(request: Request) -> FilterCreate:
    form = await request.form()

    def g(key: str, default: str = "") -> str:
        return str(form.get(key, default))

    return FilterCreate(
        name=g("name"),
        is_active="is_active" in form,
        lat=float(g("lat", "0")),
        lng=float(g("lng", "0")),
        radius_km=float(g("radius_km", "2")),
        kind=g("kind", "rent"),  # type: ignore[arg-type]
        property_type=_str_or_none(g("property_type") or None),
        source=_str_or_none(g("source") or None),
        min_price=_int_or_none(g("min_price") or None),
        max_price=_int_or_none(g("max_price") or None),
        min_rooms=_int_or_none(g("min_rooms") or None),
        max_rooms=_int_or_none(g("max_rooms") or None),
        min_sqm=_int_or_none(g("min_sqm") or None),
        max_sqm=_int_or_none(g("max_sqm") or None),
        temporal=g("temporal", "any"),  # type: ignore[arg-type]
        ocupada=g("ocupada", "any"),  # type: ignore[arg-type]
        alquiler_regulado=g("alquiler_regulado", "any"),  # type: ignore[arg-type]
        nuda_propiedad=g("nuda_propiedad", "any"),  # type: ignore[arg-type]
        elevator=g("elevator", "any"),  # type: ignore[arg-type]
        furnished=g("furnished", "any"),  # type: ignore[arg-type]
        garage=g("garage", "any"),  # type: ignore[arg-type]
        terrace=g("terrace", "any"),  # type: ignore[arg-type]
        balcony=g("balcony", "any"),  # type: ignore[arg-type]
        pets_allowed=g("pets_allowed", "any"),  # type: ignore[arg-type]
    )


@router.get("", response_class=HTMLResponse)
def filter_list(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    filters = FilterRepo(db).list_all()
    return templates.TemplateResponse(request, "filters/list.html", {"filters": filters})


@router.get("/new", response_class=HTMLResponse)
def filter_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "filters/form.html", {"flt": None})


@router.post("", response_class=RedirectResponse)
async def filter_create(
    request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    data = await _parse_filter_form(request)
    FilterRepo(db).create(data)
    return RedirectResponse("/filters", status_code=303)


@router.get("/{filter_id}/edit", response_class=HTMLResponse)
def filter_edit(request: Request, filter_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    flt = FilterRepo(db).get(filter_id)
    if flt is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "filters/form.html", {"flt": flt})


@router.post("/{filter_id}", response_class=RedirectResponse)
async def filter_update(
    request: Request, filter_id: int, db: Session = Depends(get_db)
) -> RedirectResponse:
    data = await _parse_filter_form(request)
    repo = FilterRepo(db)
    if repo.get(filter_id) is None:
        raise HTTPException(status_code=404)
    # Update all fields via full replace
    from flatbot.schemas import FilterUpdate

    repo.update(filter_id, FilterUpdate(**data.model_dump()))
    return RedirectResponse("/filters", status_code=303)


@router.delete("/{filter_id}")
def filter_delete(filter_id: int, db: Session = Depends(get_db)) -> Response:
    if not FilterRepo(db).delete(filter_id):
        raise HTTPException(status_code=404)
    return Response(status_code=200)  # HTMX replaces target with empty body → removes row


@router.post("/{filter_id}/toggle", response_class=HTMLResponse)
def filter_toggle(
    request: Request, filter_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    from flatbot.schemas import FilterUpdate

    repo = FilterRepo(db)
    flt = repo.get(filter_id)
    if flt is None:
        raise HTTPException(status_code=404)
    repo.update(filter_id, FilterUpdate(is_active=not flt.is_active))
    updated = repo.get(filter_id)
    return templates.TemplateResponse(
        request, "filters/row.html", {"flt": updated}
    )


@router.post("/{filter_id}/duplicate", response_class=RedirectResponse)
def filter_duplicate(filter_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    repo = FilterRepo(db)
    flt = repo.get(filter_id)
    if flt is None:
        raise HTTPException(status_code=404)

    data: dict[str, Any] = {
        col: getattr(flt, col)
        for col in FilterCreate.model_fields
    }
    data["name"] = f"{flt.name} (copia)"
    data["is_active"] = False
    repo.create(FilterCreate(**data))
    return RedirectResponse("/filters", status_code=303)


@router.post("/{filter_id}/test", response_class=HTMLResponse)
def filter_test(
    request: Request,
    filter_id: int,
    db: Session = Depends(get_db),
    client: OpenPropertiesClient | MockOpenPropertiesClient = Depends(get_scan_client),
    sender: AlertSender = Depends(get_alert_sender),
) -> HTMLResponse:
    flt = FilterRepo(db).get(filter_id)
    if flt is None:
        raise HTTPException(status_code=404)

    dtos = client.fetch_recent(flt)
    results = [(dto, evaluate(dto, flt)) for dto in dtos]
    matched = [r for r in results if r[1].matched]
    skipped = [r for r in results if not r[1].matched]

    return templates.TemplateResponse(
        request,
        "filters/test_result.html",
        {"matched": matched, "skipped": skipped, "total": len(dtos)},
    )
