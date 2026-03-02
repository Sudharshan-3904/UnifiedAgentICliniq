from pydantic import BaseModel, Field
from typing import Literal

class BMIRequest(BaseModel):
    height: float = Field(..., gt=0, description="Height in meters (metric) or inches (imperial)")
    weight: float = Field(..., gt=0, description="Weight in kg (metric) or lbs (imperial)")
    unit: Literal["metric", "imperial"]

class BMIResponse(BaseModel):
    bmi: float
    category: str
    interpretation: str

class HealthResponse(BaseModel):
    status: str = "ok"
