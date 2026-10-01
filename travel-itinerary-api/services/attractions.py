"""
Attractions retrieval via Geoapify Places.

We reuse the lat/long already resolved by services/weather.py (Open-Meteo
geocoding) rather than geocoding the city a second time here -- one fewer
API call, one fewer place for the two services to disagree about where
"Goa" actually is.

Geoapify's free tier (3,000 requests/day) doesn't require a credit card --
switched to this from OpenTripMap after OpenTripMap's signup started
asking for billing details.

Requires GEOAPIFY_API_KEY to be set (see .env.example).
Get a free key at: https://myprojects.geoapify.com/
"""

import os
from typing import Any, Dict, List, Optional

import httpx

PLACES_URL = "https://api.geoapify.com/v2/places"

# Maps our free-text `interests` request field to Geoapify's controlled
# category vocabulary. Anything the user types that isn't in this map is
# just ignored -- see get_attractions() below.
INTEREST_TO_CATEGORY = {
    "beaches": "beach",
    "beach": "beach",
    "history": "heritage",
    "historic": "heritage",
    "culture": "entertainment.culture",
    "cultural": "entertainment.culture",
    "museums": "entertainment.museum",
    "nature": "natural",
    "food": "catering.restaurant,catering.cafe",
    "restaurants": "catering.restaurant",
    "nightlife": "entertainment.nightclub,catering.bar",
    "shopping": "commercial.shopping_mall",
    "architecture": "heritage",
    "religion": "religion",
    "sport": "sport",
    "adventure": "leisure.park",
}

DEFAULT_CATEGORY = "tourism.attraction"


class MissingApiKeyError(Exception):
    """Raised when GEOAPIFY_API_KEY is not set in the environment."""


def _get_api_key() -> str:
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "GEOAPIFY_API_KEY is not set. Add it to your .env file."
        )
    return api_key


def _resolve_categories(interests: Optional[List[str]]) -> str:
    """Turn a list of free-text interests into a Geoapify `categories` string."""
    if not interests:
        return DEFAULT_CATEGORY

    mapped = set()
    for interest in interests:
        category = INTEREST_TO_CATEGORY.get(interest.lower())
        if category:
            mapped.update(category.split(","))

    return ",".join(mapped) if mapped else DEFAULT_CATEGORY


async def get_attractions(
    latitude: float,
    longitude: float,
    interests: Optional[List[str]] = None,
    radius_meters: int = 15000,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch nearby points of interest, filtered by `interests` where possible.

    Returns a simplified list of dicts: name, categories, place_id, address.
    """
    api_key = _get_api_key()
    categories = _resolve_categories(interests)

    params = {
        "categories": categories,
        "filter": f"circle:{longitude},{latitude},{radius_meters}",
        "bias": f"proximity:{longitude},{latitude}",
        "limit": limit,
        "lang": "en",
        "apiKey": api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(PLACES_URL, params=params)
        response.raise_for_status()
        data = response.json()

    features = data.get("features", [])

    attractions = [
        {
            "name": feature["properties"].get("name"),
            "categories": feature["properties"].get("categories"),
            "place_id": feature["properties"].get("place_id"),
            "address": feature["properties"].get("formatted"),
        }
        for feature in features
        if feature.get("properties", {}).get("name")  # skip unnamed POIs
    ]

    return attractions
