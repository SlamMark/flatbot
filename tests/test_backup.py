"""Tests for the SQLite backup utility (F8)."""
import sqlite3
from pathlib import Path

import pytest

from flatbot.services.backup import run_backup


@pytest.fixture
def live_db(tmp_path: Path) -> Path:
    """Create a minimal SQLite database to back up."""
    db_file = tmp_path / "flatbot.db"
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO t VALUES (1)")
    return db_file


class TestRunBackup:
    def test_creates_backup_file(self, live_db: Path, tmp_path: Path) -> None:
        backup_dir = str(tmp_path / "backups")
        result = run_backup(f"sqlite:///{live_db}", backup_dir)
        assert result is not None
        assert result.exists()
        assert result.stat().st_size > 0

    def test_backup_is_valid_sqlite(self, live_db: Path, tmp_path: Path) -> None:
        backup_dir = str(tmp_path / "backups")
        result = run_backup(f"sqlite:///{live_db}", backup_dir)
        assert result is not None
        with sqlite3.connect(str(result)) as conn:
            row = conn.execute("SELECT id FROM t").fetchone()
        assert row == (1,)

    def test_prunes_old_backups(self, live_db: Path, tmp_path: Path) -> None:
        backup_dir = str(tmp_path / "backups")
        db_url = f"sqlite:///{live_db}"
        # Create 5 backups
        for _ in range(5):
            run_backup(db_url, backup_dir, keep=3)
        remaining = list(Path(backup_dir).glob("flatbot_*.db"))
        assert len(remaining) == 3

    def test_missing_db_returns_none(self, tmp_path: Path) -> None:
        result = run_backup("sqlite:////nonexistent/flatbot.db", str(tmp_path / "bak"))
        assert result is None

    def test_creates_backup_dir_if_missing(self, live_db: Path, tmp_path: Path) -> None:
        nested = str(tmp_path / "a" / "b" / "backups")
        result = run_backup(f"sqlite:///{live_db}", nested)
        assert result is not None and result.exists()
