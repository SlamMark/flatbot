"""Unit tests for F4 — Telegram alert formatting and helpers."""
from datetime import datetime, timezone

from flatbot.alerts import (
    NAV_NOOP,
    build_carousel_keyboard,
    format_card,
    format_card_from_dict,
    format_carousel_card,
    format_carousel_card_from_dict,
)
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


def _dict_listing(**overrides) -> dict:
    payload = {
        "llm_summary": None,
        "property_type": "flat",
        "bedrooms": 3,
        "square_meters": 80,
        "kind": "rent",
        "price": 1200,
        "address": "Calle Test, 1, Gràcia",
        "url": "https://idealista.com/inmueble/123/",
    }
    payload.update(overrides)
    return payload


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
        assert "1" in card and "200" in card
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


class TestFormatCardFromDict:
    def test_matches_dto_output_for_same_fields(self) -> None:
        dto_card = format_card(_listing())
        dict_card = format_card_from_dict(_dict_listing())
        assert dto_card == dict_card

    def test_llm_summary_preferred(self) -> None:
        card = format_card_from_dict(_dict_listing(llm_summary="Resumen"))
        assert "Resumen" in card


class TestFormatCarouselCard:
    def test_header_includes_filter_name_and_position(self) -> None:
        text = format_carousel_card(_listing(), idx=2, total=10, filter_name="Pis")
        assert "Pis" in text
        assert "3/10" in text

    def test_dict_variant_matches_layout(self) -> None:
        text = format_carousel_card_from_dict(
            _dict_listing(), idx=0, total=4, filter_name="X"
        )
        assert "1/4" in text
        assert "X" in text


class TestBuildCarouselKeyboard:
    def test_first_page_disables_prev(self) -> None:
        kb = build_carousel_keyboard(carousel_id=5, idx=0, total=3)
        buttons = kb["inline_keyboard"][0]
        assert buttons[0]["callback_data"] == NAV_NOOP  # prev disabled
        assert buttons[2]["callback_data"] == "n:5:1"   # next active
        assert buttons[1]["text"] == "1/3"

    def test_middle_page_both_active(self) -> None:
        kb = build_carousel_keyboard(carousel_id=7, idx=2, total=5)
        buttons = kb["inline_keyboard"][0]
        assert buttons[0]["callback_data"] == "n:7:1"
        assert buttons[2]["callback_data"] == "n:7:3"

    def test_last_page_disables_next(self) -> None:
        kb = build_carousel_keyboard(carousel_id=9, idx=4, total=5)
        buttons = kb["inline_keyboard"][0]
        assert buttons[2]["callback_data"] == NAV_NOOP
        assert buttons[0]["callback_data"] == "n:9:3"
