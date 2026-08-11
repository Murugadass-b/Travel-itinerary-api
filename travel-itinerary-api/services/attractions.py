"""
Attractions retrieval via OpenTripMap.

We reuse the lat/long already resolved by services/weather.py (Open-Meteo
geocoding) rather than geocoding the city a second time here -- one fewer
API call, one fewer place for the two services to disagree about where
"Goa" actually is.

Requires OPENTRIPMAP_API_KEY to be set (see .env.example).
"""

import os
from typing import Any, Dict, List, Optional

import httpx

RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"

# Maps our free-text `interests` request field to OpenTripMap's controlled
# "kinds" vocabulary. Anything the user types that isn't in this map is
# just ignored -- see get_attractions() below.
INTEREST_TO_KIND = {
    "beaches": "beaches",
    "beach": "beaches",
    "history": "historic",
    "historic": "historic",
    "culture": "cultural",
    "cultural": "cultural",
    "museums": "museums",
    "nature": "natural",
    "food": "foods",
    "restaurants": "foods",
    "nightlife": "amusements",
    "shopping": "shops",
    "architecture": "architecture",
    "religion": "religion",
    "sport": "sport",
    "adventure": "adventure",
}

DEFAULT_KIND = "interesting_places"


class MissingApiKeyError(Exception):
    """Raised when OPENTRIPMAP_API_KEY is not set in the environment."""


def _get_api_key() -> str:
    api_key = os.getenv("OPENTRIPMAP_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "OPENTRIPMAP_API_KEY is not set. Add it to your .env file."
        )
    return api_key


def _resolve_kinds(interests: Optional[List[str]]) -> str:
    """Turn a list of free-text interests into an OpenTripMap `kinds` string."""
    if not interests:
        return DEFAULT_KIND

    mapped = {
        INTEREST_TO_KIND[interest.lower()]
        for interest in interests
        if interest.lower() in INTEREST_TO_KIND
    }
    return ",".join(mapped) if mapped else DEFAULT_KIND


async def get_attractions(
    latitude: float,
    longitude: float,
    interests: Optional[List[str]] = None,
    radius_meters: int = 15000,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch nearby points of interest, filtered by `interests` where possible.

    Returns a simplified list of dicts: name, kinds, xid, distance_meters, point.
    (xid can later be used to fetch full details from /places/xid/{xid} if
    we want richer descriptions -- not needed for the itinerary prompt yet.)
    """
    api_key = _get_api_key()
    kinds = _resolve_kinds(interests)

    params = {
        "radius": radius_meters,
        "lon": longitude,
        "lat": latitude,
        "kinds": kinds,
        "limit": limit,
        "rate": 2,  # only include POIs with at least some editorial rating
        "format": "json",
        "apikey": api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(RADIUS_URL, params=params)
        response.raise_for_status()
        raw_results = response.json()

    attractions = [
        {
            "name": poi.get("name"),
            "kinds": poi.get("kinds"),
            "xid": poi.get("xid"),
            "distance_meters": poi.get("dist"),
            "point": poi.get("point"),
        }
        for poi in raw_results
        if poi.get("name")  # skip unnamed POIs, not useful in an itinerary
    ]

    return attractions
