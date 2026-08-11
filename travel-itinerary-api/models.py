from typing import List, Optional
from pydantic import BaseModel, Field


class ItineraryRequest(BaseModel):
    city: str = Field(..., description="City to generate the itinerary for", examples=["Goa"])
    days: int = Field(..., gt=0, le=30, description="Number of days for the trip")
    budget: Optional[str] = Field(
        default=None,
        description="Rough budget level, e.g. 'low', 'medium', 'high'",
        examples=["medium"],
    )
    interests: List[str] = Field(
        default_factory=list,
        description="List of interests, e.g. ['beaches', 'food', 'history']",
    )


class ItineraryDayPlan(BaseModel):
    day: int
    summary: str
    activities: List[str] = Field(default_factory=list)


class ItineraryResponse(BaseModel):
    city: str
    days: int
    budget: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    plan: List[ItineraryDayPlan]
    cached: bool = False
