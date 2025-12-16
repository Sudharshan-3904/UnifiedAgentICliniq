from mcp.server.fastmcp import FastMCP
# import os, sys
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# if BASE_DIR not in sys.path:
#     sys.path.insert(0, BASE_DIR)

# from backend.src.tools.base import (
#     search_pubmed, 
#     fetch_ehr_data, 
#     rag_clinical_data,
#     calculate_bmi,
#     calculate_target_heart_rate,
#     calculate_blood_volume,
#     calculate_daily_water_intake,
#     calculate_waist_to_hip_ratio,
#     calculate_cholesterol_ldl
# )

# Initialize FastMCP server
mcp = FastMCP("MedToolAgent")


# @mcp.tool()
# def search_pubmed_tool(query: str, num_articles: int = 10, top_n: int = 3) -> str:
#     """
#     Search PubMed for medical literature and return top relevant articles.
    
#     Args:
#         query: Search query for PubMed
#         num_articles: Number of articles to fetch (default: 10)
#         top_n: Number of top ranked articles to return (default: 3)
#     """
#     return search_pubmed.invoke({"query": query, "num_articles": num_articles, "top_n": top_n})

# @mcp.tool()
# def fetch_ehr_data_tool(patient_id: str) -> str:
#     """Fetch Electronic Health Records for a patient."""
#     return fetch_ehr_data.invoke(patient_id)

# @mcp.tool()
# def rag_clinical_data_tool(query: str) -> str:
#     """Retrieve clinical data from local RAG knowledge base."""
#     return rag_clinical_data.invoke(query)

def _get_weight_in_kg(weight: float, unit: str) -> float:
    unit = unit.lower().strip()
    if unit in ['lb', 'lbs', 'pound', 'pounds']:
        return weight * 0.453592
    return weight

def _get_height_in_meters(height: float, unit: str) -> float:
    unit = unit.lower().strip()
    if unit in ['cm', 'centimeter', 'centimeters']:
        return height / 100.0
    elif unit in ['ft', 'feet', 'foot']:
        return height * 0.3048
    elif unit in ['in', 'inch', 'inches']:
        return height * 0.0254
    return height

@mcp.tool()
def calculate_bmi(weight: float, height: float = 0, height_ft: int = 0, height_in: int = 0, weight_unit: str = "kg", height_unit: str = "m") -> str:
    """
    Calculate Body Mass Index (BMI).
    
    Args:
        weight: Weight value
        height: Height value (if using metric or single unit)
        height_ft: Height in feet (optional, used with height_in)
        height_in: Height in inches (optional, used with height_ft)
        weight_unit: Unit for weight ('kg', 'lbs'). Default 'kg'
        height_unit: Unit for height ('m', 'cm', 'ft', 'in'). Default 'm'
    
    Returns:
        BMI score and category
    """
    try:
        # Normalize weight
        w_kg = _get_weight_in_kg(weight, weight_unit)
        
        # Normalize height
        h_m = 0.0
        if height_ft > 0 or height_in > 0:
            # Use feet/inches
            total_inches = (height_ft * 12) + height_in
            h_m = total_inches * 0.0254
        else:
            h_m = _get_height_in_meters(height, height_unit)
            
        if h_m <= 0:
            return "Error: Height must be greater than 0"
            
        bmi = w_kg / (h_m ** 2)
        
        category = ""
        if bmi < 18.5:
            category = "Underweight"
        elif 18.5 <= bmi < 25:
            category = "Normal weight"
        elif 25 <= bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
            
        return f"BMI: {bmi:.2f} ({category})"
    except Exception as e:
        return f"Error calculating BMI: {str(e)}"

@mcp.tool()
def calculate_target_heart_rate(age: int) -> str:
    """
    Calculate Maximum and Target Heart Rate based on age.
    
    Args:
        age: Age of the person
        
    Returns:
        Max heart rate and target zone (50-85% of max)
    """
    max_hr = 220 - age
    target_low = max_hr * 0.50
    target_high = max_hr * 0.85
    return f"Max Heart Rate: {max_hr} bpm\nTarget Heart Rate Zone (50-85%): {int(target_low)} - {int(target_high)} bpm"

@mcp.tool()
def calculate_blood_volume(weight: float, height: float, sex: str, weight_unit: str = "kg", height_unit: str = "m") -> str:
    """
    Calculate estimated blood volume using Nadler's equation.
    
    Args:
        weight: Weight value
        height: Height value
        sex: Biological sex ('male' or 'female')
        weight_unit: Unit for weight ('kg', 'lbs')
        height_unit: Unit for height ('m', 'cm', 'ft', 'in')
        
    Returns:
        Estimated blood volume in liters
    """
    try:
        w_kg = _get_weight_in_kg(weight, weight_unit)
        h_m = _get_height_in_meters(height, height_unit)
        
        sex = sex.lower().strip()
        bv = 0.0
        
        if sex in ['male', 'm', 'man']:
            bv = (0.3669 * (h_m ** 3)) + (0.03219 * w_kg) + 0.6041
        elif sex in ['female', 'f', 'woman']:
            bv = (0.3561 * (h_m ** 3)) + (0.03308 * w_kg) + 0.1833
        else:
            return "Error: Sex must be 'male' or 'female' for this calculation"
            
        return f"Estimated Blood Volume: {bv:.2f} liters"
    except Exception as e:
        return f"Error calculating blood volume: {str(e)}"

@mcp.tool()
def calculate_daily_water_intake(weight: float, weight_unit: str = "kg") -> str:
    """
    Calculate recommended daily water intake.
    
    Args:
        weight: Weight value
        weight_unit: Unit for weight ('kg', 'lbs')
        
    Returns:
        Recommended water intake in liters
    """
    try:
        w_kg = _get_weight_in_kg(weight, weight_unit)
        # General rule: 35 ml per kg
        intake_liters = w_kg * 0.035
        return f"Recommended Daily Water Intake: {intake_liters:.2f} liters"
    except Exception as e:
        return f"Error calculating water intake: {str(e)}"

@mcp.tool()
def calculate_waist_to_hip_ratio(waist: float, hip: float) -> str:
    """
    Calculate Waist to Hip Ratio (WHR).
    
    Args:
        waist: Waist circumference (same unit as hip)
        hip: Hip circumference (same unit as waist)
        
    Returns:
        WHR and health risk assessment
    """
    if hip == 0:
        return "Error: Hip circumference cannot be 0"
    
    ratio = waist / hip
    
    # WHO Guidelines
    # Men: > 0.90 is high risk
    # Women: > 0.85 is high risk
    
    return f"Waist to Hip Ratio: {ratio:.2f}\n(WHO cutoffs for abdominal obesity: >0.90 for men, >0.85 for women)"

@mcp.tool()
def calculate_cholesterol_ldl(total: float, hdl: float, triglycerides: float, unit: str = "mg/dL") -> str:
    """
    Calculate LDL Cholesterol using the Friedewald equation.
    
    Args:
        total: Total Cholesterol
        hdl: HDL Cholesterol
        triglycerides: Triglycerides
        unit: Unit ('mg/dL' or 'mmol/L')
        
    Returns:
        Estimated LDL Cholesterol
    """
    # Friedewald equation: LDL = Total - HDL - (Triglycerides / 5) for mg/dL
    # For mmol/L: LDL = Total - HDL - (Triglycerides / 2.2)
    
    unit = unit.lower().strip()
    ldl = 0.0
    
    if 'mg' in unit:
        ldl = total - hdl - (triglycerides / 5)
    elif 'mmol' in unit:
        ldl = total - hdl - (triglycerides / 2.2)
    else:
        return f"Error: Unsupported unit {unit}. Use 'mg/dL' or 'mmol/L'"
        
    return f"Estimated LDL Cholesterol: {ldl:.2f} {unit}"


if __name__ == "__main__":
    mcp.run()
