import logging
import time
from dataclasses import dataclass

import httpx

from flatbot.config import settings
from flatbot.integrations.openproperties.dto import ListingDTO

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"
_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}


def format_card(listing: ListingDTO) -> str:
    """Build a Telegram-friendly text card for a listing."""
    lines: list[str] = []

    if listing.llm_summary:
        lines.append(listing.llm_summary)
    else:
        parts = [listing.property_type.capitalize()]
        if listing.bedrooms is not None:
            parts.append(f"{listing.bedrooms} hab")
        if listing.square_meters is not None:
            parts.append(f"{listing.square_meters}m²")
        price_str = f"{listing.price:,}€/mes" if listing.kind == "rent" else f"{listing.price:,}€"
        parts.append(price_str)
        parts.append(listing.address)
        lines.append(" · ".join(parts))

    lines.append(listing.url)
    return "\n".join(lines)


def format_batch(listings: list[ListingDTO], filter_name: str) -> str:
    """Bundle multiple listings into a single message (used when many matches arrive at once)."""
    header = f"🏠 {len(listings)} pisos nuevos — {filter_name}"
    cards = [format_card(listing) for listing in listings]
    return header + "\n\n" + "\n\n---\n\n".join(cards)


@dataclass
class AlertSender:
    """Sends Telegram messages with exponential backoff on rate-limit / server errors."""

    bot_token: str
    chat_id: str
    max_per_scan: int = 10

    def send(self, text: str) -> bool:
        """Send a single message. Returns True on success."""
        url = f"{_TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        delay = 1.0
        with httpx.Client(timeout=10.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = client.post(url, json=payload)
                    if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    resp.raise_for_status()
                    return True
                except httpx.HTTPError as exc:
                    logger.warning("Telegram send error (attempt %d): %s", attempt + 1, exc)
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(delay)
                        delay *= 2
        return False

    def send_listings(
        self, listings: list[ListingDTO], filter_name: str = ""
    ) -> tuple[int, int]:
        """
        Send alert cards for a list of new listings, respecting max_per_scan.

        Returns (sent, skipped) counts.
        """
        if not listings:
            return 0, 0

        capped = listings[: self.max_per_scan]
        skipped = len(listings) - len(capped)

        sent = 0
        if len(capped) > 3:
            # Group into a single message when many listings arrive at once
            ok = self.send(format_batch(capped, filter_name))
            if ok:
                sent = len(capped)
        else:
            for listing in capped:
                ok = self.send(format_card(listing))
                if ok:
                    sent += 1

        if skipped:
            self.send(f"ℹ️ {skipped} pisos adicionales omitidos (límite {self.max_per_scan}/scan).")

        return sent, skipped


def make_sender() -> AlertSender:
    return AlertSender(
        bot_token=settings.telegram_token,
        chat_id=settings.telegram_chat_id,
    )
