"""Filtering and deduplication for place results."""

from functools import lru_cache
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .models import Place, PlaceFilters


@lru_cache(maxsize=10000)
def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Normalize URL to bare domain.

    Examples:
      https://www.example.com/path?q=1 -> example.com
      http://subdomain.example.co.uk   -> subdomain.example.co.uk
      example.com                      -> example.com
    """
    if not url or not isinstance(url, str) or url.strip() == "":
        return None
    try:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def filter_places(places: List[Place], filters: PlaceFilters) -> tuple:
    """Apply filters to place list. Returns (filtered_places, stats)."""
    if not places or not filters:
        return places, {}

    filtered = []
    stats = {
        "input_count": len(places),
        "filtered_rating": 0,
        "filtered_reviews": 0,
        "filtered_phone": 0,
        "filtered_website": 0,
        "filtered_address": 0,
        "filtered_keywords": 0,
    }

    for place in places:
        if filters.min_rating is not None:
            if not place.rating or place.rating < filters.min_rating:
                stats["filtered_rating"] += 1
                continue

        if filters.min_review_count is not None:
            if not place.ratingCount or place.ratingCount < filters.min_review_count:
                stats["filtered_reviews"] += 1
                continue

        if filters.require_phone and not place.phoneNumber:
            stats["filtered_phone"] += 1
            continue

        if filters.require_website and not place.website:
            stats["filtered_website"] += 1
            continue

        if filters.require_address and not place.address:
            stats["filtered_address"] += 1
            continue

        if filters.exclude_keywords:
            title_lower = (place.title or "").lower()
            address_lower = (place.address or "").lower()
            if any(
                kw.lower() in title_lower or kw.lower() in address_lower
                for kw in filters.exclude_keywords
            ):
                stats["filtered_keywords"] += 1
                continue

        filtered.append(place)

    stats["output_count"] = len(filtered)
    stats["filtered_total"] = stats["input_count"] - stats["output_count"]
    return filtered, stats


def deduplicate_places(places: List[Place], dedupe_by: str = "both") -> tuple:
    """Deduplicate places by cid, website domain, or both. Keeps best record."""
    if not places:
        return [], {"input_count": 0, "output_count": 0, "duplicates_removed": 0}

    seen = {}
    stats = {
        "input_count": len(places),
        "duplicates_by_cid": 0,
        "duplicates_by_website": 0,
        "output_count": 0,
        "duplicates_removed": 0,
    }

    for place in places:
        dedup_keys = []

        if dedupe_by in ("cid", "both") and place.cid:
            dedup_keys.append(("cid", place.cid))

        if dedupe_by in ("website", "both") and place.website:
            normalized = normalize_url(place.website)
            if normalized:
                dedup_keys.append(("website", normalized))

        if not dedup_keys:
            dedup_keys = [("unique", id(place))]

        for key_type, key_value in dedup_keys:
            dedup_key = (key_type, key_value)
            if dedup_key not in seen:
                seen[dedup_key] = place
            else:
                existing = seen[dedup_key]
                should_replace = False
                if place.rating and existing.rating:
                    if place.rating > existing.rating:
                        should_replace = True
                    elif place.rating == existing.rating:
                        if (place.ratingCount or 0) > (existing.ratingCount or 0):
                            should_replace = True
                elif place.rating and not existing.rating:
                    should_replace = True

                if should_replace:
                    seen[dedup_key] = place
                else:
                    stats["duplicates_removed"] += 1
                    if key_type == "cid":
                        stats["duplicates_by_cid"] += 1
                    elif key_type == "website":
                        stats["duplicates_by_website"] += 1

    result = []
    seen_ids = set()
    for place in places:
        pid = id(place)
        for _, best in seen.items():
            if best is place and pid not in seen_ids:
                result.append(place)
                seen_ids.add(pid)
                break

    stats["output_count"] = len(result)
    return result, stats
