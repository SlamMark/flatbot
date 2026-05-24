from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flatbot.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)

    lat: Mapped[float]
    lng: Mapped[float]
    radius_km: Mapped[float]

    kind: Mapped[str] = mapped_column(String(10))  # rent | sale
    property_type: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str | None] = mapped_column(String(20))

    min_price: Mapped[int | None]
    max_price: Mapped[int | None]
    min_rooms: Mapped[int | None]
    max_rooms: Mapped[int | None]
    min_sqm: Mapped[int | None]
    max_sqm: Mapped[int | None]

    # Three-state: any | only | exclude
    ocupada: Mapped[str] = mapped_column(String(10), default="any")
    nuda_propiedad: Mapped[str] = mapped_column(String(10), default="any")

    # Amenity: any | yes | no
    elevator: Mapped[str] = mapped_column(String(5), default="any")
    furnished: Mapped[str] = mapped_column(String(5), default="any")
    garage: Mapped[str] = mapped_column(String(5), default="any")
    terrace: Mapped[str] = mapped_column(String(5), default="any")
    balcony: Mapped[str] = mapped_column(String(5), default="any")
    pets_allowed: Mapped[str] = mapped_column(String(5), default="any")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    matches: Mapped[list["Match"]] = relationship(back_populates="filter", cascade="all, delete-orphan")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Cross-portal dedup key (same property on Idealista+Fotocasa → same property_id)
    property_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10))
    price: Mapped[int]
    price_per_sqm: Mapped[float | None]
    property_type: Mapped[str] = mapped_column(String(20))
    condition: Mapped[str | None] = mapped_column(String(20))
    bedrooms: Mapped[int | None]
    bathrooms: Mapped[int | None]
    square_meters: Mapped[int | None]
    floor_number: Mapped[int | None]
    address: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    amenities: Mapped[list[str] | None] = mapped_column(JSON)
    is_agency: Mapped[bool | None]
    publisher_name: Mapped[str | None] = mapped_column(String(200))
    photos_amount: Mapped[int | None]
    flag_temporal: Mapped[bool] = mapped_column(default=False)
    flag_ocupada: Mapped[bool] = mapped_column(default=False)
    flag_alquiler_regulado: Mapped[bool] = mapped_column(default=False)
    flag_bare_ownership: Mapped[bool] = mapped_column(default=False)
    llm_summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    matches: Mapped[list["Match"]] = relationship(back_populates="listing", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("filter_id", "listing_id", name="uq_filter_listing"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    filter_id: Mapped[int] = mapped_column(ForeignKey("filters.id", ondelete="CASCADE"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    filter: Mapped[Filter] = relationship(back_populates="matches")
    listing: Mapped[Listing] = relationship(back_populates="matches")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | completed | failed
    listings_fetched: Mapped[int] = mapped_column(Integer, default=0)
    new_listings: Mapped[int] = mapped_column(Integer, default=0)
    matches_found: Mapped[int] = mapped_column(Integer, default=0)
    alerts_sent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
