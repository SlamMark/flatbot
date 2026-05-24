from datetime import datetime, timezone
from typing import Any

from flatbot.integrations.openproperties.dto import ListingDTO


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def map_listing(raw: dict[str, Any]) -> ListingDTO:
    coords: dict[str, Any] = raw.get("coordinates") or {}
    flags: dict[str, Any] = raw.get("flags") or {}
    return ListingDTO(
        id=raw["id"],
        property_id=raw["propertyId"],
        source=raw["source"],
        external_id=raw["externalId"],
        url=raw["url"],
        kind=raw["kind"],
        price=raw["price"],
        price_per_sqm=raw.get("pricePerSqm"),
        property_type=raw["propertyType"],
        condition=raw.get("condition"),
        bedrooms=raw.get("bedrooms"),
        bathrooms=raw.get("bathrooms"),
        square_meters=raw.get("squareMeters"),
        floor_number=raw.get("floorNumber"),
        address=raw["address"],
        lat=coords.get("lat"),
        lng=coords.get("lng"),
        amenities=raw.get("amenities") or [],
        is_agency=raw.get("isAgency"),
        publisher_name=raw.get("publisherName"),
        photos_amount=raw.get("photosAmount"),
        image_urls=raw.get("imageUrls") or [],
        flag_temporal=flags.get("isTemporal", False),
        flag_ocupada=flags.get("isOkupada", False),
        flag_alquiler_regulado=flags.get("isAlquilerRegulado", False),
        flag_bare_ownership=flags.get("isBareOwnership", False),
        llm_summary=raw.get("llmSummary"),
        hours_ago=raw.get("hoursAgo"),
        published_at=_parse_dt(raw["publishedAt"]),
        last_scraped_at=_parse_dt(raw["lastScrapedAt"]),
    )


def map_listings(raw_list: list[dict[str, Any]]) -> list[ListingDTO]:
    return [map_listing(r) for r in raw_list]
