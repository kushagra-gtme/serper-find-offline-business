"""Extract Place objects from Serper API responses."""

from typing import List, Dict, Any

from .models import Place
from .filters import normalize_url


BATCH_SIZE = 100
"""Maximum queries per Serper API batch request."""


def extract_places(result: List[Dict[str, Any]]) -> List[Place]:
    """Extract Place objects from a Serper API batch response.

    Parses the raw JSON response from the Serper Places batch endpoint,
    extracting each place result into a typed Place dataclass with
    normalized website URLs.

    Args:
        result: Raw batch response — a list of per-query result dicts,
                each containing 'searchParameters' and 'places' keys.

    Returns:
        List of Place objects extracted from all queries in the batch.
    """
    places: List[Place] = []
    if not isinstance(result, list):
        return places
    for qr in result:
        params = qr.get("searchParameters", {})
        for p in qr.get("places", []):
            raw_website = p.get("website")
            places.append(Place(
                q=params.get("q", ""),
                location=params.get("location", ""),
                page=params.get("page", 1),
                position=p.get("position", 0),
                title=p.get("title", ""),
                address=p.get("address", ""),
                latitude=p.get("latitude"),
                longitude=p.get("longitude"),
                rating=p.get("rating"),
                ratingCount=p.get("ratingCount"),
                category=p.get("category"),
                phoneNumber=p.get("phoneNumber"),
                website=raw_website,
                website_normalized=normalize_url(raw_website),
                cid=p.get("cid"),
            ))
    return places
