from .schemas import BMIRequest, BMIResponse

def calculate_bmi_logic(data: BMIRequest) -> BMIResponse:
    """
    Calculates BMI based on the provided height, weight, and unit.
    """
    if data.unit == "metric":
        # Metric: bmi = weight / (height ** 2)
        bmi = data.weight / (data.height ** 2)
    else:
        # Imperial: bmi = 703 * weight / (height ** 2)
        bmi = 703 * data.weight / (data.height ** 2)
    
    bmi = round(bmi, 2)
    category, interpretation = get_bmi_category(bmi)
    
    return BMIResponse(
        bmi=bmi,
        category=category,
        interpretation=interpretation
    )

def get_bmi_category(bmi: float) -> tuple[str, str]:
    """
    Returns the BMI category and interpretation based on the BMI value.
    """
    if bmi < 18.5:
        return "Underweight", "You are below the healthy weight range."
    elif 18.5 <= bmi < 25:
        return "Normal weight", "You have a healthy body weight."
    elif 25 <= bmi < 30:
        return "Overweight", "You are above the healthy weight range."
    else:
        return "Obesity", "You are in the obesity range."
