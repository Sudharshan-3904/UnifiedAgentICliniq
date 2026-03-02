from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from .schemas import BMIRequest
from .service import calculate_bmi_logic
import json
import os

# Create the MCP Server
bmi_server = Server("bmi-mcp-server")

@bmi_server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (like the interactive widget)."""
    return [
        Resource(
            uri="ui://widget/bmi-dashboard.html",
            name="BMI Widget",
            mimeType="text/html+skybridge",
            description="Interactive BMI calculator dashboard"
        )
    ]

@bmi_server.read_resource()
async def read_resource(uri: str) -> str:
    """Read the content of a resource."""
    if str(uri) == "ui://widget/bmi-dashboard.html":
        # Get the path relative to the current working directory
        widget_path = os.path.join(os.getcwd(), "static", "widget.html")
        if os.path.exists(widget_path):
            with open(widget_path, "r", encoding="utf-8") as f:
                return f.read()
    raise ValueError(f"Resource not found: {uri}")

@bmi_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available BMI tools with OpenAI-specific metadata."""
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
            },
            # MCP meta field (serializes to _meta)
            meta={
                "openai/outputTemplate": "ui://widget/bmi-dashboard.html",
                "openai/toolInvocation/invoking": "Calculating BMI...",
                "openai/toolInvocation/invoked": "BMI calculated."
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
            
            result_text = (
                f"BMI Calculation Results:\n"
                f"- BMI: {response.bmi}\n"
                f"- Category: {response.category}\n"
                f"- Interpretation: {response.interpretation}\n\n"
                f"The interactive BMI dashboard has been rendered above with the full visual breakdown."
            )
            
            structured_data = {
                "bmi": response.bmi,
                "category": response.category,
                "interpretation": response.interpretation,
                "height": request.height,
                "weight": request.weight,
                "unit": request.unit
            }

            # Return TextContent with the meta field
            return [
                TextContent(
                    type="text",
                    text=result_text,
                    meta={
                        "openai/outputTemplate": "ui://widget/bmi-dashboard.html",
                        "structuredContent": structured_data
                    }
                )
            ]
        except Exception as e:
            return [TextContent(type="text", text=f"Error during calculation: {str(e)}")]
            
    raise ValueError(f"Tool not found: {name}")
