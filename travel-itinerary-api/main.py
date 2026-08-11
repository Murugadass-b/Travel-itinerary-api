from fastapi import FastAPI, HTTPException

from models import ItineraryRequest, ItineraryResponse, ItineraryDayPlan
from services.weather import get_weather_for_city, CityNotFoundError

app = FastAPI(
    title="AI Travel Itinerary Planner API",
    description="Generates a grounded, day-by-day travel itinerary using real attractions and weather data.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "AI Travel Itinerary Planner API is running"}


@app.get("/debug/weather")
async def debug_weather(city: str, days: int = 3):
    """
    TEMPORARY test endpoint for Step 2.
    Lets us verify the Open-Meteo integration with raw output
    before wiring it into the main /itinerary pipeline.
    Will be removed once Step 4 combines all retrieval into one function.
    """
    try:
        return await get_weather_for_city(city, days)
    except CityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/itinerary", response_model=ItineraryResponse)
def create_itinerary(request: ItineraryRequest):
    """
    Step 1: dummy hardcoded response.
    This will later be replaced by the full retrieval + generation pipeline
    (weather -> attractions -> Gemini -> cache).
    """
    dummy_plan = [
        ItineraryDayPlan(
            day=day_num,
            summary=f"Placeholder plan for day {day_num} in {request.city}",
            activities=[
                "Placeholder activity 1",
                "Placeholder activity 2",
                "Placeholder activity 3",
            ],
        )
        for day_num in range(1, request.days + 1)
    ]

    return ItineraryResponse(
        city=request.city,
        days=request.days,
        budget=request.budget,
        interests=request.interests,
        plan=dummy_plan,
        cached=False,
    )
