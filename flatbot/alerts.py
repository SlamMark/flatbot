import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from flatbot.config import settings
from flatbot.integrations.openproperties.dto import ListingDTO

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"
_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}

NAV_NOOP = "n:0:0"


def _card_lines(
    *,
    llm_summary: str | None,
    property_type: str,
    bedrooms: int | None,
    square_meters: int | None,
    kind: str,
    price: int,
    address: str,
    url: str,
) -> str:
    """Shared card formatter for both DTO and dict inputs."""
    lines: list[str] = []
    if llm_summary:
        lines.append(llm_summary)
    else:
        parts = [property_type.capitalize()]
        if bedrooms is not None:
            parts.append(f"{bedrooms} hab")
        if square_meters is not None:
            parts.append(f"{square_meters}m²")
        price_str = f"{price:,}€/mes" if kind == "rent" else f"{price:,}€"
        parts.append(price_str)
        parts.append(address)
        lines.append(" · ".join(parts))
    lines.append(url)
    return "\n".join(lines)


def format_card(listing: ListingDTO) -> str:
    """Build a Telegram-friendly text card for a listing."""
    return _card_lines(
        llm_summary=listing.llm_summary,
        property_type=listing.property_type,
        bedrooms=listing.bedrooms,
        square_meters=listing.square_meters,
        kind=listing.kind,
        price=listing.price,
        address=listing.address,
        url=listing.url,
    )


def format_card_from_dict(listing: dict[str, Any]) -> str:
    """Same card layout as format_card, but consuming the JSON dict the API returns."""
    return _card_lines(
        llm_summary=listing.get("llm_summary"),
        property_type=listing["property_type"],
        bedrooms=listing.get("bedrooms"),
        square_meters=listing.get("square_meters"),
        kind=listing["kind"],
        price=listing["price"],
        address=listing["address"],
        url=listing["url"],
    )


def format_carousel_card(listing: ListingDTO, idx: int, total: int, filter_name: str) -> str:
    """Card text for a carousel page: header + listing card."""
    header = f"🏠 {filter_name} — {idx + 1}/{total}"
    return f"{header}\n\n{format_card(listing)}"


def format_carousel_card_from_dict(
    listing: dict[str, Any], idx: int, total: int, filter_name: str
) -> str:
    """Carousel card built from a dict payload — used by bot callback handlers."""
    header = f"🏠 {filter_name} — {idx + 1}/{total}"
    return f"{header}\n\n{format_card_from_dict(listing)}"


def build_carousel_keyboard(carousel_id: int, idx: int, total: int) -> dict[str, Any]:
    """Build the inline keyboard for carousel navigation."""
    prev_data = f"n:{carousel_id}:{idx - 1}" if idx > 0 else NAV_NOOP
    next_data = f"n:{carousel_id}:{idx + 1}" if idx < total - 1 else NAV_NOOP
    return {
        "inline_keyboard": [
            [
                {"text": "◀️ Anterior" if idx > 0 else "—", "callback_data": prev_data},
                {"text": f"{idx + 1}/{total}", "callback_data": NAV_NOOP},
                {"text": "Siguiente ▶️" if idx < total - 1 else "—", "callback_data": next_data},
            ]
        ]
    }


@dataclass
class AlertSender:
    """Sends Telegram messages with exponential backoff on rate-limit / server errors."""

    bot_token: str
    chat_id: str

    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """POST sendMessage with retries. Returns the response JSON 'result' dict, or None on failure."""
        url = f"{_TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        delay = 1.0
        with httpx.Client(timeout=10.0) as client:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = client.post(url, json=payload)
                    if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    if resp.status_code >= 400:
                        logger.warning(
                            "Telegram send failed (HTTP %d): %s",
                            resp.status_code,
                            resp.text[:500],
                        )
                        resp.raise_for_status()
                    data = resp.json()
                    result = data.get("result")
                    return result if isinstance(result, dict) else None
                except httpx.HTTPError as exc:
                    logger.warning("Telegram send error (attempt %d): %s", attempt + 1, exc)
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(delay)
                        delay *= 2
        return None

    def send(self, text: str) -> bool:
        """Send a plain-text message. Returns True on success."""
        # No parse_mode: alert cards are plain text. URLs still auto-link.
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
        return self._post(payload) is not None

    def send_with_keyboard(self, text: str, reply_markup: dict[str, Any]) -> int | None:
        """Send a message with an inline keyboard. Returns the Telegram message_id, or None on failure."""
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": False,
            "reply_markup": reply_markup,
        }
        result = self._post(payload)
        if result is None:
            return None
        msg_id = result.get("message_id")
        return int(msg_id) if isinstance(msg_id, int) else None


def make_sender() -> AlertSender:
    return AlertSender(
        bot_token=settings.telegram_token,
        chat_id=settings.telegram_chat_id,
    )
