from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ThreeState = Literal["any", "only", "exclude"]
AmenityFilter = Literal["any", "yes", "no"]


class FilterCreate(BaseModel):
    name: str
    is_active: bool = True
    lat: float
    lng: float
    radius_km: float
    kind: Literal["rent", "sale"]
    property_type: str | None = None
    source: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_rooms: int | None = None
    max_rooms: int | None = None
    min_sqm: int | None = None
    max_sqm: int | None = None
    temporal: ThreeState = "any"
    ocupada: ThreeState = "any"
    alquiler_regulado: ThreeState = "any"
    nuda_propiedad: ThreeState = "any"
    elevator: AmenityFilter = "any"
    furnished: AmenityFilter = "any"
    garage: AmenityFilter = "any"
    terrace: AmenityFilter = "any"
    balcony: AmenityFilter = "any"
    pets_allowed: AmenityFilter = "any"


class FilterUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = None
    kind: Literal["rent", "sale"] | None = None
    property_type: str | None = None
    source: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_rooms: int | None = None
    max_rooms: int | None = None
    min_sqm: int | None = None
    max_sqm: int | None = None
    temporal: ThreeState | None = None
    ocupada: ThreeState | None = None
    alquiler_regulado: ThreeState | None = None
    nuda_propiedad: ThreeState | None = None
    elevator: AmenityFilter | None = None
    furnished: AmenityFilter | None = None
    garage: AmenityFilter | None = None
    terrace: AmenityFilter | None = None
    balcony: AmenityFilter | None = None
    pets_allowed: AmenityFilter | None = None


class FilterRead(FilterCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingRead(BaseModel):
    id: int
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
    amenities: list[str] | None
    is_agency: bool | None
    publisher_name: str | None
    photos_amount: int | None
    flag_temporal: bool
    flag_ocupada: bool
    flag_alquiler_regulado: bool
    flag_bare_ownership: bool
    llm_summary: str | None
    published_at: datetime
    last_scraped_at: datetime
    first_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchRead(BaseModel):
    id: int
    filter_id: int
    listing_id: int
    matched_at: datetime
    notified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ScanRunRead(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    listings_fetched: int
    new_listings: int
    matches_found: int
    alerts_sent: int
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)
