"""Unit tests for F4 — Telegram alert formatting and sending."""
from datetime import datetime, timezone

from flatbot.alerts import AlertSender, format_batch, format_card
from flatbot.integrations.openproperties.dto import ListingDTO


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _listing(**overrides) -> ListingDTO:
    defaults = dict(
        id="abc",
        property_id="prop-1",
        source="idealista",
        external_id="123",
        url="https://idealista.com/inmueble/123/",
        kind="rent",
        price=1200,
        price_per_sqm=12.0,
        property_type="flat",
        condition="good",
        bedrooms=3,
        bathrooms=1,
        square_meters=80,
        floor_number=2,
        address="Calle Test, 1, Gràcia",
        lat=41.38,
        lng=2.17,
        amenities=["elevator"],
        is_agency=False,
        publisher_name=None,
        photos_amount=5,
        image_urls=[],
        flag_temporal=False,
        flag_ocupada=False,
        flag_alquiler_regulado=False,
        flag_bare_ownership=False,
        llm_summary=None,
        hours_ago=2,
        published_at=_dt(),
        last_scraped_at=_dt(),
    )
    defaults.update(overrides)
    return ListingDTO(**defaults)


# ---------------------------------------------------------------------------
# format_card
# ---------------------------------------------------------------------------


class TestFormatCard:
    def test_uses_llm_summary_when_present(self) -> None:
        lst = _listing(llm_summary="Piso · 3 hab · 80m²")
        card = format_card(lst)
        assert "Piso · 3 hab · 80m²" in card
        assert lst.url in card

    def test_fallback_without_llm_summary(self) -> None:
        lst = _listing(llm_summary=None)
        card = format_card(lst)
        assert "Flat" in card or "flat" in card.lower()
        assert "3 hab" in card
        assert "80m²" in card
        assert "1" in card and "200" in card  # price present in some format
        assert lst.url in card

    def test_rent_price_label(self) -> None:
        card = format_card(_listing(kind="rent", price=950, llm_summary=None))
        assert "€/mes" in card

    def test_sale_price_label(self) -> None:
        card = format_card(_listing(kind="sale", price=250000, llm_summary=None))
        assert "€/mes" not in card
        assert "€" in card

    def test_url_always_present(self) -> None:
        for has_summary in (True, False):
            lst = _listing(llm_summary="s" if has_summary else None)
            assert lst.url in format_card(lst)


class TestFormatBatch:
    def test_includes_header_with_count_and_name(self) -> None:
        listings = [_listing(property_id=f"p{i}") for i in range(3)]
        msg = format_batch(listings, "Mi filtro")
        assert "3" in msg
        assert "Mi filtro" in msg

    def test_contains_all_urls(self) -> None:
        listings = [_listing(property_id=f"p{i}", url=f"https://example.com/{i}") for i in range(2)]
        msg = format_batch(listings, "filtro")
        for lst in listings:
            assert lst.url in msg


# ---------------------------------------------------------------------------
# AlertSender with fake HTTP (no real Telegram calls)
# ---------------------------------------------------------------------------


class _FakeSender(AlertSender):
    """AlertSender subclass that records messages instead of calling Telegram."""

    def __init__(self, max_per_scan: int = 10, fail: bool = False) -> None:
        super().__init__(bot_token="fake", chat_id="fake", max_per_scan=max_per_scan)
        self.sent_texts: list[str] = []
        self._fail = fail

    def send(self, text: str) -> bool:
        if self._fail:
            return False
        self.sent_texts.append(text)
        return True


class TestAlertSender:
    def test_send_single_listing_sends_one_message(self) -> None:
        sender = _FakeSender()
        sent, skipped = sender.send_listings([_listing()], "filtro")
        assert sent == 1
        assert skipped == 0
        assert len(sender.sent_texts) == 1

    def test_few_listings_sent_individually(self) -> None:
        listings = [_listing(property_id=f"p{i}") for i in range(3)]
        sender = _FakeSender()
        sent, _ = sender.send_listings(listings, "filtro")
        assert sent == 3
        assert len(sender.sent_texts) == 3

    def test_many_listings_grouped_into_one_message(self) -> None:
        listings = [_listing(property_id=f"p{i}") for i in range(5)]
        sender = _FakeSender()
        sent, _ = sender.send_listings(listings, "filtro")
        assert sent == 5
        # grouped into a single batch message
        assert len(sender.sent_texts) == 1

    def test_rate_limit_caps_at_max_per_scan(self) -> None:
        listings = [_listing(property_id=f"p{i}") for i in range(15)]
        sender = _FakeSender(max_per_scan=5)
        sent, skipped = sender.send_listings(listings, "filtro")
        assert sent == 5
        assert skipped == 10
        # one batch message + one "omitidos" notice
        assert len(sender.sent_texts) == 2

    def test_skipped_notice_sent_when_capped(self) -> None:
        listings = [_listing(property_id=f"p{i}") for i in range(8)]
        sender = _FakeSender(max_per_scan=3)
        sender.send_listings(listings, "filtro")
        assert any("omitidos" in t for t in sender.sent_texts)

    def test_empty_listings_returns_zero(self) -> None:
        sender = _FakeSender()
        sent, skipped = sender.send_listings([], "filtro")
        assert sent == 0
        assert skipped == 0
        assert sender.sent_texts == []

    def test_send_failure_returns_false(self) -> None:
        sender = _FakeSender(fail=True)
        sent, _ = sender.send_listings([_listing()], "filtro")
        assert sent == 0
