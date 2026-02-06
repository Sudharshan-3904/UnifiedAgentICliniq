from dataclasses import dataclass
from enum import Enum
from typing import Optional

class BMICategory(Enum):
    UNDERWEIGHT = "Underweight"
    NORMAL = "Normal weight"
    OVERWEIGHT = "Overweight"
    OBESE = "Obese"

@dataclass(frozen=True)
class BMIResult:
    bmi: float
    category: BMICategory
    ideal_weight_range: tuple[float, float]
    
    def to_dict(self) -> dict:
        return {
            "bmi": round(self.bmi, 2),
            "category": self.category.value,
            "ideal_weight_min": round(self.ideal_weight_range[0], 2),
            "ideal_weight_max": round(self.ideal_weight_range[1], 2)
        }

def calculate_bmi(weight_kg: float, height_m: float) -> BMIResult:
    """
    Calculates Body Mass Index (BMI) and provides classification.
    Formula: weight (kg) / [height (m)]^2
    """
    if height_m <= 0:
        raise ValueError("Height must be greater than zero.")
    if weight_kg <= 0:
        raise ValueError("Weight must be greater than zero.")

    bmi = weight_kg / (height_m ** 2)
    
    if bmi < 18.5:
        category = BMICategory.UNDERWEIGHT
    elif 18.5 <= bmi < 25:
        category = BMICategory.NORMAL
    elif 25 <= bmi < 30:
        category = BMICategory.OVERWEIGHT
    else:
        category = BMICategory.OBESE

    # Ideal weight range based on normal BMI (18.5 to 24.9)
    ideal_min = 18.5 * (height_m ** 2)
    ideal_max = 24.9 * (height_m ** 2)
    
    return BMIResult(bmi, category, (ideal_min, ideal_max))
