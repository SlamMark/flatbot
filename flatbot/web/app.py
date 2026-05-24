"""FastAPI web application — entry point for the FlatBot portal."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from flatbot.config import settings
from flatbot.logging_conf import configure_logging
from flatbot.scheduler import start_scheduler, stop_scheduler
from flatbot.web.routes.api import router as api_router
from flatbot.web.routes.config import router as config_router
from flatbot.web.routes.dashboard import router as dashboard_router
from flatbot.web.routes.filters import router as filters_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="FlatBot", version="0.1.0", lifespan=lifespan)

app.include_router(api_router)
app.include_router(dashboard_router)
app.include_router(filters_router)
app.include_router(config_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
