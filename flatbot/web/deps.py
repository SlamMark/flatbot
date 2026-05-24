"""Shared FastAPI dependency functions for scan client and sender (overridable in tests)."""
from flatbot.alerts import AlertSender, make_sender
from flatbot.integrations.openproperties.client import (
    MockOpenPropertiesClient,
    OpenPropertiesClient,
    make_client,
)


def get_scan_client() -> OpenPropertiesClient | MockOpenPropertiesClient:
    return make_client()


def get_alert_sender() -> AlertSender:
    return make_sender()
