from mcp.server import Server
from mcp.types import Tool, TextContent
from .schemas import BMIRequest
from .service import calculate_bmi_logic
import json

# Create the MCP Server
bmi_server = Server("bmi-mcp-server")

@bmi_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available BMI tools."""
    return [
        Tool(
            name="calculate_bmi",
            description="Calculate BMI based on height, weight, and unit (metric/imperial).",
            inputSchema={
                "type": "object",
                "properties": {
                    "height": {"type": "number", "description": "Height (meters for metric, inches for imperial)"},
                    "weight": {"type": "number", "description": "Weight (kg for metric, lbs for imperial)"},
                    "unit": {"type": "string", "enum": ["metric", "imperial"], "description": "Unit system"}
                },
                "required": ["height", "weight", "unit"]
            }
        )
    ]

@bmi_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle BMI tool calls."""
    if name == "calculate_bmi":
        try:
            # Validate and calculate
            request = BMIRequest(**arguments)
            response = calculate_bmi_logic(request)
            
            # Format result for MCP with a prompt for the interactive widget
            result_text = (
                f"BMI Calculation Results:\n"
                f"- BMI: {response.bmi}\n"
                f"- Category: {response.category}\n"
                f"- Interpretation: {response.interpretation}\n\n"
                f"You can also use the interactive calculator here: [Open BMI Widget](/widget)"
            )
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
            
    raise ValueError(f"Tool not found: {name}")
