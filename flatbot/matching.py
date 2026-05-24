from dataclasses import dataclass, field

from flatbot.integrations.openproperties.dto import ListingDTO
from flatbot.models import Filter


@dataclass
class MatchResult:
    matched: bool
    reasons: list[str] = field(default_factory=list)
    score: int = 0  # number of optional criteria met (higher = better fit)


def _check(condition: bool, reason: str, result: MatchResult, optional: bool = False) -> bool:
    """Evaluate a criterion. Mandatory criteria short-circuit on failure."""
    if condition:
        result.reasons.append(f"+ {reason}")
        if optional:
            result.score += 1
        return True
    result.reasons.append(f"- {reason}")
    return False


def _three_state_match(value: bool, filter_val: str) -> bool:
    """Return True if the listing satisfies a three-state filter (any/only/exclude)."""
    if filter_val == "any":
        return True
    if filter_val == "only":
        return value
    # exclude
    return not value


def _amenity_match(amenities: list[str], amenity_key: str, filter_val: str) -> bool:
    """Return True if the listing satisfies an amenity filter (any/yes/no)."""
    if filter_val == "any":
        return True
    has = amenity_key in amenities
    return has if filter_val == "yes" else not has


def evaluate(listing: ListingDTO, f: Filter) -> MatchResult:
    """Evaluate a listing against a filter. Returns MatchResult with matched flag and reasons."""
    result = MatchResult(matched=True)

    # --- Mandatory criteria ---
    if f.kind != listing.kind:
        result.matched = False
        result.reasons.append(f"- kind: want {f.kind}, got {listing.kind}")
        return result

    if f.min_price is not None and listing.price < f.min_price:
        result.matched = False
        result.reasons.append(f"- price {listing.price} < min {f.min_price}")
        return result

    if f.max_price is not None and listing.price > f.max_price:
        result.matched = False
        result.reasons.append(f"- price {listing.price} > max {f.max_price}")
        return result

    if f.min_rooms is not None and listing.bedrooms is not None and listing.bedrooms < f.min_rooms:
        result.matched = False
        result.reasons.append(f"- bedrooms {listing.bedrooms} < min {f.min_rooms}")
        return result

    if f.max_rooms is not None and listing.bedrooms is not None and listing.bedrooms > f.max_rooms:
        result.matched = False
        result.reasons.append(f"- bedrooms {listing.bedrooms} > max {f.max_rooms}")
        return result

    if f.min_sqm is not None and listing.square_meters is not None and listing.square_meters < f.min_sqm:
        result.matched = False
        result.reasons.append(f"- sqm {listing.square_meters} < min {f.min_sqm}")
        return result

    if f.max_sqm is not None and listing.square_meters is not None and listing.square_meters > f.max_sqm:
        result.matched = False
        result.reasons.append(f"- sqm {listing.square_meters} > max {f.max_sqm}")
        return result

    if f.source and listing.source != f.source:
        result.matched = False
        result.reasons.append(f"- source: want {f.source}, got {listing.source}")
        return result

    if f.property_type and listing.property_type != f.property_type:
        result.matched = False
        result.reasons.append(f"- property_type: want {f.property_type}, got {listing.property_type}")
        return result

    # Three-state flags
    for flag_attr, listing_val, label in [
        ("ocupada", listing.flag_ocupada, "ocupada"),
        ("nuda_propiedad", listing.flag_bare_ownership, "nuda_propiedad"),
    ]:
        fval = getattr(f, flag_attr, "any")
        if not _three_state_match(listing_val, fval):
            result.matched = False
            result.reasons.append(f"- {label}: filter={fval}, listing={listing_val}")
            return result

    # Amenity filters
    for attr, api_key, label in [
        ("elevator", "elevator", "elevator"),
        ("furnished", "furnished", "furnished"),
        ("garage", "garage", "garage"),
        ("terrace", "terrace", "terrace"),
        ("balcony", "balcony", "balcony"),
        ("pets_allowed", "petsAllowed", "pets_allowed"),
    ]:
        fval = getattr(f, attr, "any")
        if not _amenity_match(listing.amenities, api_key, fval):
            result.matched = False
            result.reasons.append(f"- {label}: filter={fval}, amenities={listing.amenities}")
            return result

    # --- Optional scoring criteria ---
    result.reasons.append("+ kind match")
    result.reasons.append("+ price in range")

    if listing.bedrooms is not None:
        result.score += 1
        result.reasons.append(f"+ bedrooms={listing.bedrooms}")
    if listing.square_meters is not None:
        result.score += 1
        result.reasons.append(f"+ sqm={listing.square_meters}")
    if listing.llm_summary:
        result.score += 1

    return result
