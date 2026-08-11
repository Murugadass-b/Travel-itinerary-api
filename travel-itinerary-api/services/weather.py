"""
Weather retrieval via Open-Meteo.

Two calls happen here:
1. Geocoding: turn a city name into latitude/longitude
   (https://geocoding-api.open-meteo.com/v1/search)
2. Forecast: turn latitude/longitude into a daily weather forecast
   (https://api.open-meteo.com/v1/forecast)

No API key is required for either endpoint.
"""

from typing import Any, Dict

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class CityNotFoundError(Exception):
    """Raised when the geocoding API has no match for the given city name."""


async def geocode_city(city: str) -> Dict[str, Any]:
    """
    Resolve a city name to its coordinates and metadata.

    Returns a dict with at least: name, latitude, longitude, country, timezone.
    Raises CityNotFoundError if no match is found.
    """
    params = {"name": city, "count": 1, "language": "en", "format": "json"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        data = response.json()

    results = data.get("results")
    if not results:
        raise CityNotFoundError(f"No location found for city: '{city}'")

    top_match = results[0]
    return {
        "name": top_match["name"],
        "latitude": top_match["latitude"],
        "longitude": top_match["longitude"],
        "country": top_match.get("country"),
        "timezone": top_match.get("timezone"),
    }


async def get_forecast(latitude: float, longitude: float, days: int) -> Dict[str, Any]:
    """
    Fetch a daily weather forecast for the given coordinates.

    `days` is clamped to Open-Meteo's supported range (1-16) so an
    oversized trip request doesn't cause an API error.
    """
    forecast_days = max(1, min(days, 16))

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
        ],
        "forecast_days": forecast_days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()
        return response.json()


async def get_weather_for_city(city: str, days: int) -> Dict[str, Any]:
    """
    Convenience wrapper: city name -> full daily forecast.
    Combines geocode_city + get_forecast into a single call.
    """
    location = await geocode_city(city)
    forecast = await get_forecast(location["latitude"], location["longitude"], days)

    return {
        "location": location,
        "forecast": forecast,
    }
