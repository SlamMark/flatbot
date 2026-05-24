"""SQLite backup utility — uses sqlite3 backup API (safe with WAL mode)."""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _db_path(database_url: str) -> Path:
    # sqlite:////data/flatbot.db  →  /data/flatbot.db
    # sqlite:///relative.db       →  relative.db
    path_str = database_url.replace("sqlite:////", "/").replace("sqlite:///", "")
    return Path(path_str)


def run_backup(database_url: str, backup_dir: str = "/data/backups", keep: int = 7) -> Path | None:
    """Copy the live database to backup_dir using the sqlite3 backup API.

    Returns the path of the new backup file, or None if the source does not exist.
    Retains only the `keep` most-recent backups.
    """
    src = _db_path(database_url)
    if not src.exists():
        logger.warning("Backup skipped — DB file not found: %s", src)
        return None

    bdir = Path(backup_dir)
    bdir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dst = bdir / f"flatbot_{ts}.db"

    with sqlite3.connect(str(src)) as src_conn, sqlite3.connect(str(dst)) as dst_conn:
        src_conn.backup(dst_conn)

    logger.info("Backup created: %s (%d bytes)", dst, dst.stat().st_size)

    for old in sorted(bdir.glob("flatbot_*.db"))[:-keep]:
        old.unlink()
        logger.info("Pruned old backup: %s", old)

    return dst
