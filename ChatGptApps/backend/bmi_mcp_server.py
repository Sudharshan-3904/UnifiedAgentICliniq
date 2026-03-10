from fastmcp import FastMCP

mcp = FastMCP("bmi_calculator_server")

@mcp.tool
async def calculate_bmi(height: float, weight: float) -> str:
    """
    Calculate Body Mass Index (BMI) from height and weight.
    
    Args:
        height: Height in meters
        weight: Weight in kilograms
    
    Returns:
        HTML widget displaying BMI value and category
    """
    if height <= 0 or weight <= 0:
        return "<div style='color: red; font-weight: bold;'>Invalid input: height and weight must be positive numbers.</div>"
    
    bmi = weight / (height ** 2)
    
    if bmi < 18.5:
        category = "Underweight"
        color = "#3498db"  # Blue
    elif bmi < 25:
        category = "Normal weight"
        color = "#2ecc71"  # Green
    elif bmi < 30:
        category = "Overweight"
        color = "#f39c12"  # Orange
    else:
        category = "Obese"
        color = "#e74c3c"  # Red
    
    html_widget = f"""
    <div style="border: 2px solid {color}; border-radius: 10px; padding: 20px; margin: 10px; background-color: #f9f9f9; font-family: Arial, sans-serif; text-align: center;">
        <h2 style="color: {color}; margin-bottom: 10px;">BMI Calculator Result</h2>
        <p style="font-size: 24px; font-weight: bold; color: {color}; margin: 10px 0;">Your BMI: {bmi:.2f}</p>
        <p style="font-size: 18px; color: {color};">Category: {category}</p>
        <div style="margin-top: 15px; font-size: 14px; color: #666;">
            <p>Height: {height} m | Weight: {weight} kg</p>
        </div>
    </div>
    """
    
    return html_widget

if __name__ == "__main__":
    mcp.run()