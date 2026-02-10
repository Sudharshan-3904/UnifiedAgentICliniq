from dataclasses import dataclass
from enum import Enum
from typing import Optional

class BMICategory(Enum):
    UNDERWEIGHT = ("Underweight", "#3498db")
    NORMAL = ("Normal weight", "#2ecc71")
    OVERWEIGHT = ("Overweight", "#f39c12")
    OBESE = ("Obese", "#e74c3c")

    def __init__(self, label: str, color: str):
        self.label = label
        self.color = color

@dataclass(frozen=True)
class BMIResult:
    bmi: float
    category: BMICategory
    height: float
    weight: float
    ideal_weight_range: tuple[float, float]

    def to_dict(self) -> dict:
        return {
            "bmi": round(self.bmi, 2),
            "category": self.category.label,
            "color": self.category.color,
            "height": self.height,
            "weight": self.weight,
            "ideal_weight_min": round(self.ideal_weight_range[0], 2),
            "ideal_weight_max": round(self.ideal_weight_range[1], 2)
        }

def calculate_bmi(height_m: float, weight_kg: float) -> BMIResult:
    if height_m <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive.")
    
    bmi = weight_kg / (height_m**2)
    
    if bmi < 18.5:
        cat = BMICategory.UNDERWEIGHT
    elif bmi < 25:
        cat = BMICategory.NORMAL
    elif bmi < 30:
        cat = BMICategory.OVERWEIGHT
    else:
        cat = BMICategory.OBESE

    # Ideal weight range (normal BMI: 18.5 - 24.9)
    ideal_min = 18.5 * (height_m**2)
    ideal_max = 24.9 * (height_m**2)
    
    return BMIResult(bmi, cat, height_m, weight_kg, (ideal_min, ideal_max))
