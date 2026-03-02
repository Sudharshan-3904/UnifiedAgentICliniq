import pytest
from app.service import calculate_bmi_logic, get_bmi_category
from app.schemas import BMIRequest

def test_metric_calculation():
    request = BMIRequest(height=1.75, weight=70, unit="metric")
    response = calculate_bmi_logic(request)
    assert response.bmi == 22.86
    assert response.category == "Normal weight"

def test_imperial_calculation():
    # 70 inches (~1.78m), 160 lbs (~72.5kg)
    # 703 * 160 / (70 * 70) = 22.95
    request = BMIRequest(height=70, weight=160, unit="imperial")
    response = calculate_bmi_logic(request)
    assert response.bmi == 22.96  # 703 * 160 / 4900 = 22.955... -> 22.96
    assert response.category == "Normal weight"

def test_categories():
    assert get_bmi_category(16.0)[0] == "Underweight"
    assert get_bmi_category(22.0)[0] == "Normal weight"
    assert get_bmi_category(27.0)[0] == "Overweight"
    assert get_bmi_category(32.0)[0] == "Obesity"

def test_invalid_input():
    with pytest.raises(Exception):
        # Pydantic validation would normally catch this, 
        # but here we're testing the function directly with invalid data
        BMIRequest(height=0, weight=70, unit="metric") # Height 0 will cause div by zero if not handled
