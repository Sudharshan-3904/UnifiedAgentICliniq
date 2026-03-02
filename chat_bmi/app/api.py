from fastapi import APIRouter
from .schemas import BMIRequest, BMIResponse, HealthResponse
from .service import calculate_bmi_logic

router = APIRouter()

@router.post("/bmi", response_model=BMIResponse)
async def calculate_bmi(request: BMIRequest):
    return calculate_bmi_logic(request)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()
