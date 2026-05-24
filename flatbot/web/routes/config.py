"""Config/settings page — read-only view of active settings."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from flatbot.config import settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/config", response_class=HTMLResponse)
def config_page(request: Request) -> HTMLResponse:
    cfg = {
        "scan_interval_minutes": settings.scan_interval_minutes,
        "mock_api": settings.mock_api,
        "log_level": settings.log_level,
        "database_url": settings.database_url,
        "telegram_chat_id": settings.telegram_chat_id,
        "rapidapi_key": "***" if settings.rapidapi_key else "(no configurada)",
        "telegram_token": "***" if settings.telegram_token else "(no configurado)",
    }
    return templates.TemplateResponse(request, "config.html", {"cfg": cfg})
