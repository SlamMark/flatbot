"""Login / logout routes for the web portal."""
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from flatbot.config import settings
from flatbot.web.auth import COOKIE_NAME, make_auth_token

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _safe_next(url: str) -> str:
    """Reject absolute URLs to prevent open redirect."""
    parsed = urlparse(url)
    return url if (not parsed.scheme and not parsed.netloc) else "/"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "", next: str = "/") -> HTMLResponse:
    if not settings.web_password:
        return RedirectResponse("/")  # type: ignore[return-value]
    return templates.TemplateResponse(
        request, "login.html", {"error": bool(error), "next_url": _safe_next(next)}
    )


@router.post("/login")
async def login_submit(request: Request, next: str = "/") -> Response:
    form = await request.form()
    password = str(form.get("password", ""))
    next_url = _safe_next(next)
    if password == settings.web_password:
        resp: Response = RedirectResponse(next_url, status_code=303)
        resp.set_cookie(COOKIE_NAME, make_auth_token(), httponly=True, max_age=_COOKIE_MAX_AGE)
        return resp
    return RedirectResponse(f"/login?error=1&next={next_url}", status_code=303)


@router.get("/logout")
def logout() -> Response:
    resp: Response = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp
