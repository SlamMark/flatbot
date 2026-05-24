from sqlalchemy import select
from sqlalchemy.orm import Session

from flatbot.models import Setting

_DEFAULTS: dict[str, str] = {
    "scan_interval_minutes": "30",
    "max_alerts_per_scan": "10",
    "alert_hours_window": "24",
}


class SettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> str:
        row = self.db.get(Setting, key)
        return row.value if row is not None else _DEFAULTS.get(key, "")

    def get_int(self, key: str) -> int:
        return int(self.get(key))

    def set(self, key: str, value: str) -> None:
        row = self.db.get(Setting, key)
        if row is None:
            self.db.add(Setting(key=key, value=value))
        else:
            row.value = value
        self.db.commit()

    def all(self) -> dict[str, str]:
        rows = self.db.execute(select(Setting)).scalars()
        result = dict(_DEFAULTS)
        for row in rows:
            result[row.key] = row.value
        return result
