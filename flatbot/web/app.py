from fastapi import FastAPI

from flatbot.config import settings
from flatbot.logging_conf import configure_logging

configure_logging(settings.log_level)

app = FastAPI(title="FlatBot", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
