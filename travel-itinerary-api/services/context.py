"""
Combines weather and attractions retrieval into a single "context" object.

This is the Retrieval half of the RAG pattern: given a trip request, gather
every real-world fact the AI generation step (Step 5) will need, so the
prompt only has to inject data -- it never has to go fetch anything itself.

Geocoding happens exactly once here and is reused for both the weather
forecast and the attractions search, instead of each service re-resolving
the city independently.
"""

import asyncio
from typing import Any, Dict, List, Optional

from services.weather import geocode_city, get_forecast, CityNotFoundError
from services.attractions import get_attractions, MissingApiKeyError

# Re-exported so callers (main.py) only need to import from this module.
__all__ = ["get_travel_context", "CityNotFoundError", "MissingApiKeyError"]


async def get_travel_context(
    city: str,
    days: int,
    interests: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Resolve a trip request into grounded real-world context.

    Returns:
        {
            "location": {...},      # from geocode_city()
            "weather": {...},        # from get_forecast()
            "attractions": [...],    # from get_attractions()
        }

    Raises:
        CityNotFoundError: if the city can't be geocoded.
        MissingApiKeyError: if OPENTRIPMAP_API_KEY isn't configured.
    """
    location = await geocode_city(city)

    # Weather and attractions don't depend on each other once we have
    # coordinates, so fetch them concurrently rather than one after another.
    forecast, attractions = await asyncio.gather(
        get_forecast(location["latitude"], location["longitude"], days),
        get_attractions(location["latitude"], location["longitude"], interests),
    )

    return {
        "location": location,
        "weather": forecast,
        "attractions": attractions,
    }
