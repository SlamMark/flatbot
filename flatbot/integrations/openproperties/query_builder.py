from flatbot.models import Filter

_THREE_STATE = {
    "ocupada": "ocupada",
    "nuda_propiedad": "nudaPropiedad",
}

_AMENITIES = {
    "elevator": "elevator",
    "furnished": "furnished",
    "garage": "garage",
    "terrace": "terrace",
    "balcony": "balcony",
    "pets_allowed": "petsAllowed",
}


def build_listings_params(
    f: Filter,
    page: int = 1,
    page_size: int = 20,
    max_age_days: int | None = None,
) -> dict[str, str | int | float]:
    params: dict[str, str | int | float] = {
        "kind": f.kind,
        "lat": f.lat,
        "lng": f.lng,
        "radiusKm": f.radius_km,
        "page": page,
        "pageSize": page_size,
    }
    if max_age_days is not None:
        params["maxAgeDays"] = max_age_days
    if f.property_type:
        params["propertyType"] = f.property_type
    if f.source:
        params["source"] = f.source
    if f.min_price is not None:
        params["minPrice"] = f.min_price
    if f.max_price is not None:
        params["maxPrice"] = f.max_price
    if f.min_rooms is not None:
        params["minRooms"] = f.min_rooms
    if f.max_rooms is not None:
        params["maxRooms"] = f.max_rooms
    if f.min_sqm is not None:
        params["minSqm"] = f.min_sqm
    if f.max_sqm is not None:
        params["maxSqm"] = f.max_sqm
    for attr, key in _THREE_STATE.items():
        val = getattr(f, attr, "any")
        if val != "any":
            params[key] = val
    for attr, key in _AMENITIES.items():
        val = getattr(f, attr, "any")
        if val != "any":
            params[key] = val
    return params


def build_recent_params(
    f: Filter,
    hours: int = 6,
    limit: int = 20,
) -> dict[str, str | int | float]:
    params: dict[str, str | int | float] = {
        "kind": f.kind,
        "lat": f.lat,
        "lng": f.lng,
        "radiusKm": f.radius_km,
        "hours": hours,
        "limit": limit,
    }
    if f.source:
        params["source"] = f.source
    if f.min_price is not None:
        params["minPrice"] = f.min_price
    if f.max_price is not None:
        params["maxPrice"] = f.max_price
    if f.min_rooms is not None:
        params["minRooms"] = f.min_rooms
    if f.max_rooms is not None:
        params["maxRooms"] = f.max_rooms
    return params
