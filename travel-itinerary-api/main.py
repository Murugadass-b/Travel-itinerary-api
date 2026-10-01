from dotenv import load_dotenv

load_dotenv()  # must run before services read os.getenv() at call time

from fastapi import FastAPI, HTTPException

from models import ItineraryRequest, ItineraryResponse, ItineraryDayPlan
from services.context import get_travel_context, CityNotFoundError, MissingApiKeyError
from services.ai_generator import generate_itinerary, MissingGeminiKeyError, GenerationParseError

app = FastAPI(
    title="AI Travel Itinerary Planner API",
    description="Generates a grounded, day-by-day travel itinerary using real attractions and weather data.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "AI Travel Itinerary Planner API is running"}


@app.get("/debug/context")
async def debug_context(city: str, days: int = 3, interests: str = ""):
    """
    TEMPORARY test endpoint for Step 4.
    Exercises the combined get_travel_context() function -- weather and
    attractions retrieved together, sharing one geocode call.
    `interests` is a comma-separated string in the URL, e.g. ?interests=beaches,food
    Will be removed once Step 6 wires this into the main /itinerary pipeline.
    """
    interest_list = [i.strip() for i in interests.split(",") if i.strip()]

    try:
        return await get_travel_context(city=city, days=days, interests=interest_list)
    except CityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MissingApiKeyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/generate")
async def debug_generate(request: ItineraryRequest):
    """
    TEMPORARY test endpoint for Step 5.
    Runs the full retrieval + generation pipeline and returns Gemini's
    parsed plan directly, so we can inspect it before wiring it into
    /itinerary as the real response (Step 6).
    """
    try:
        context = await get_travel_context(
            city=request.city, days=request.days, interests=request.interests
        )
    except CityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MissingApiKeyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        plan = await generate_itinerary(
            city=request.city,
            days=request.days,
            budget=request.budget,
            interests=request.interests,
            context=context,
        )
    except MissingGeminiKeyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except GenerationParseError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"plan": plan, "context_used": context}


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
