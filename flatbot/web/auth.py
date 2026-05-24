"""Portal authentication — itsdangerous-signed cookie, disabled when WEB_PASSWORD is unset."""
from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from flatbot.config import settings

COOKIE_NAME = "auth"
_SALT = "flatbot-auth-v1"
_EXEMPT_PREFIXES = ("/login", "/logout", "/health", "/api/")


def make_auth_token() -> str:
    return URLSafeSerializer(settings.web_secret_key, salt=_SALT).dumps({"ok": 1})


def verify_auth_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        URLSafeSerializer(settings.web_secret_key, salt=_SALT).loads(token)
        return True
    except BadSignature:
        return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.web_password:
            return await call_next(request)
        path = request.url.path
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)
        if not verify_auth_token(request.cookies.get(COOKIE_NAME)):
            return RedirectResponse(f"/login?next={path}", status_code=302)
        return await call_next(request)
