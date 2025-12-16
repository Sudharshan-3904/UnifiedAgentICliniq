from langchain_core.tools import tool
from typing import Optional
from ..utils.logger import logger
from dotenv import load_dotenv
import os
from Bio import Entrez
import requests


load_dotenv()

def setup_pubmed_api() -> None:
    NCBI_API_KEY = os.getenv("NCBI_API_KEY")
    NCBI_EMAIL = os.getenv("NCBI_EMAIL")

    if not NCBI_API_KEY:
        logger.warning("NCBI API key not found in .env file. Rate limits will be lower.")

    # Set Entrez email and API key
    Entrez.email = NCBI_EMAIL
    Entrez.api_key = NCBI_API_KEY

    # Base URL for NCBI E-utilities (for requests fallback)
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

@tool
def search_pubmed(query: str, num_articles: int = 10, top_n: int = 3) -> str:
    """
    Search PubMed for medical literature and return top relevant articles.
    
    Args:
        query: Search query for PubMed
        num_articles: Number of articles to fetch (default: 10)
        top_n: Number of top ranked articles to return (default: 3)
    
    Returns:
        Formatted string with article details
    """
    logger.info(f"Searching PubMed for: {query}")
    
    from .pubmed_fetcher import search_and_fetch_pubmed_articles
    
    # Fetch and rank articles
    result = search_and_fetch_pubmed_articles(
        query=query,
        num_articles=num_articles,
        top_n=top_n,
        save_to_disk=False
    )
    
    if result["status"] == "error":
        return f"Error searching PubMed: {result['message']}"
    
    if result["status"] == "no_results":
        return f"No articles found for query: {query}"
    
    # Format the best articles for output
    best_articles = result["best_articles"]
    output_lines = [
        f"Found {result['total_found']} articles for query: '{query}'",
        f"Fetched and analyzed {result['total_fetched']} articles",
        f"\nTop {len(best_articles)} most relevant articles:\n"
    ]
    
    for idx, article in enumerate(best_articles, 1):
        output_lines.append(f"\n--- Article #{idx} ---")
        output_lines.append(f"Title: {article.get('title', 'N/A')}")
        output_lines.append(f"Authors: {', '.join(article.get('authors', [])[:3])}{'...' if len(article.get('authors', [])) > 3 else ''}")
        output_lines.append(f"Journal: {article.get('journal', 'N/A')}")
        output_lines.append(f"Publication Date: {article.get('pubdate', 'N/A')}")
        output_lines.append(f"PMID: {article.get('pmid', 'N/A')}")
        output_lines.append(f"PMCID: {article.get('pmcid', 'N/A')}")
        
        # Include abstract
        abstract = article.get('abstract', 'No abstract available')
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
        output_lines.append(f"Abstract: {abstract}")
        
        # Mention if full text is available
        if article.get('full_text'):
            output_lines.append("Full text: Available")
        
        output_lines.append("")
    
    return "\n".join(output_lines)

@tool
def fetch_ehr_data(patient_id: str) -> str:
    """Fetch Electronic Health Records for a patient."""
    logger.info(f"Fetching EHR for patient: {patient_id}")
    # Mock implementation
    return f"EHR Data for {patient_id}: Age: 45, History: Hypertension, Medications: Lisinopril"

@tool
def rag_clinical_data(query: str) -> str:
    """Retrieve clinical data from local RAG knowledge base."""
    logger.info(f"Querying RAG for: {query}")
    # Mock implementation
    return f"Clinical Guidelines for {query}: First-line treatment is..."

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

@tool
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

@tool
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

@tool
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

@tool
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

@tool
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

@tool
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

# List of tools available to the agent
agent_tools = [
    search_pubmed, 
    fetch_ehr_data, 
    rag_clinical_data,
    calculate_bmi,
    calculate_target_heart_rate,
    calculate_blood_volume,
    calculate_daily_water_intake,
    calculate_waist_to_hip_ratio,
    calculate_cholesterol_ldl
]
