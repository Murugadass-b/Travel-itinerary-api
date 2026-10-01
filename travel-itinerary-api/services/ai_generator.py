"""
The "Generation" half of the RAG pattern: takes the retrieved context from
services/context.py and asks Gemini to turn it into a structured, day-by-day
itinerary -- explicitly instructed to only use the real attractions and
weather it was given, not to invent new places.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"


class MissingGeminiKeyError(Exception):
    """Raised when GEMINI_API_KEY is not set in the environment."""


class GenerationParseError(Exception):
    """Raised when Gemini's response isn't valid JSON matching our schema."""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise MissingGeminiKeyError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=api_key)


def _build_prompt(
    city: str,
    days: int,
    budget: Optional[str],
    interests: List[str],
    context: Dict[str, Any],
) -> str:
    weather_summary = json.dumps(context.get("weather", {}), indent=2)
    attractions_summary = json.dumps(context.get("attractions", []), indent=2)

    return f"""You are a travel itinerary planner. Build a day-by-day plan for a trip to {city} lasting {days} day(s).

Traveler details:
- Budget: {budget or "not specified"}
- Interests: {", ".join(interests) if interests else "not specified"}

GROUNDING RULES (must follow exactly):
- Only mention attractions, restaurants, or places that appear by name in the ATTRACTIONS list below. Do not invent places that aren't listed.
- Use the WEATHER data to decide indoor vs outdoor activities per day (e.g. suggest indoor options on days with high precipitation probability).
- If there are not enough attractions for all {days} day(s), reuse or combine attractions rather than inventing new ones, and say so in the summary.

WEATHER (per day forecast):
{weather_summary}

ATTRACTIONS (real places near {city}):
{attractions_summary}

Return ONLY valid JSON (no markdown fences, no commentary) matching exactly this shape:
{{
  "plan": [
    {{
      "day": 1,
      "summary": "one or two sentence overview of the day, referencing the weather",
      "activities": ["activity referencing a real attraction name", "..."]
    }}
  ]
}}
The "plan" array must have exactly {days} entries, one per day, in order."""


def _call_gemini_sync(prompt: str, model: str) -> str:
    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    return response.text


async def generate_itinerary(
    city: str,
    days: int,
    budget: Optional[str],
    interests: List[str],
    context: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """
    Calls Gemini with the grounded prompt and returns a list of day-plan
    dicts matching ItineraryDayPlan (day, summary, activities).

    Raises:
        MissingGeminiKeyError: if GEMINI_API_KEY isn't configured.
        GenerationParseError: if Gemini's output isn't valid/expected JSON.
    """
    prompt = _build_prompt(city, days, budget, interests, context)

    # The SDK call is synchronous; run it off the event loop so the
    # FastAPI server doesn't block other requests while waiting on Gemini.
    raw_text = await asyncio.to_thread(_call_gemini_sync, prompt, model)

    try:
        parsed = json.loads(raw_text)
        plan = parsed["plan"]
        if not isinstance(plan, list):
            raise ValueError("'plan' is not a list")
        return plan
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise GenerationParseError(
            f"Gemini response did not match expected JSON shape: {e}\nRaw response: {raw_text[:500]}"
        )
