import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("BMI Calculator")

# BMI logic
def calculate_bmi_logic(weight_kg: float, height_m: float):
    weight_kg = float(weight_kg)
    height_m = float(height_m)
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category = "Underweight"
        advice = "Consider consulting with a healthcare provider about reaching a healthy weight."
    elif 18.5 <= bmi < 24.9:
        category = "Normal weight"
        advice = "Great job! Maintain your healthy lifestyle."
    elif 25 <= bmi < 29.9:
        category = "Overweight"
        advice = "You might consider a more active lifestyle and balanced diet."
    else:
        category = "Obese"
        advice = "It's highly recommended to consult a doctor for a personalized health plan."
    
    return {
        "bmi": bmi,
        "category": category,
        "advice": advice
    }

def render_external_app_logic(app_name: str):
    apps = {
        "map": "https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d15000!2d-122.084!3d37.422!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1sen!2sus!4v1625060000000",
        "wiki": "https://en.m.wikipedia.org/wiki/Body_mass_index",
        "bmi_info": "https://www.cdc.gov/healthyweight/assessing/bmi/index.html"
    }
    url = apps.get(app_name, "https://www.wikipedia.org")
    return {
        "type": "iframe",
        "url": url,
        "title": f"External App: {app_name}"
    }

@mcp.tool()
async def calculate_bmi(weight_kg: float, height_m: float) -> dict:
    """
    Calculate Body Mass Index (BMI) and provide health advice.
    
    Args:
        weight_kg: Weight in kilograms (e.g., 70.0)
        height_m: Height in meters (e.g., 1.75)
    """
    result = calculate_bmi_logic(weight_kg, height_m)
    
    # Add UI resource metadata for ChatGPT Apps SDK
    # In a real scenario, this URI would point to your hosted frontend
    # For local dev, we point it to the static file path handled by FastMCP or your dev server
    # Documentation says: _meta.ui.resourceUri
    return {
        "content": [
            {
                "type": "text",
                "text": f"Your BMI is {result['bmi']} ({result['category']}). {result['advice']}"
            }
        ],
        "structuredContent": result,
        "_meta": {
            "ui": {
                "resourceUri": "http://localhost:8000/index.html"
            }
        }
    }

@mcp.tool()
async def render_external_app(app_name: str) -> dict:
    """
    Render an external specialized application within the UI.
    
    Args:
        app_name: Name of the application to render (e.g., 'map', 'wiki', 'bmi_info')
    """
    result = render_external_app_logic(app_name)
    
    return {
        "content": [
            {
                "type": "text",
                "text": f"Launching external {app_name} component..."
            }
        ],
        "structuredContent": result,
        "_meta": {
            "ui": {
                "resourceUri": result["url"]
            }
        }
    }

if __name__ == "__main__":
    # Start the server (FastMCP handles SSE/Stdio)
    mcp.run(transport='sse')
