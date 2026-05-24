from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ListingDTO:
    id: str
    property_id: str
    source: str
    external_id: str
    url: str
    kind: str
    price: int
    price_per_sqm: float | None
    property_type: str
    condition: str | None
    bedrooms: int | None
    bathrooms: int | None
    square_meters: int | None
    floor_number: int | None
    address: str
    lat: float | None
    lng: float | None
    amenities: list[str] = field(default_factory=list)
    is_agency: bool | None = None
    publisher_name: str | None = None
    photos_amount: int | None = None
    image_urls: list[str] = field(default_factory=list)
    flag_temporal: bool = False
    flag_ocupada: bool = False
    flag_alquiler_regulado: bool = False
    flag_bare_ownership: bool = False
    llm_summary: str | None = None
    hours_ago: int | None = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    last_scraped_at: datetime = field(default_factory=datetime.utcnow)
