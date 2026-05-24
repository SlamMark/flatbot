"""F5 — APScheduler background scan loop."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from flatbot.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    # Lazy imports to avoid circular dependencies
    from flatbot.alerts import make_sender
    from flatbot.db import SessionLocal
    from flatbot.integrations.openproperties.client import make_client
    from flatbot.scanner import run_scan

    def _job() -> None:
        db = SessionLocal()
        try:
            run_scan(db, make_client(), make_sender())
        except Exception as exc:
            logger.error("Unhandled scan error in scheduler: %s", exc)
        finally:
            db.close()

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _job,
        trigger="interval",
        minutes=settings.scan_interval_minutes,
        id="scan",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — scan every %d min", settings.scan_interval_minutes)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
