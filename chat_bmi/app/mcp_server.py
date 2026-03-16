from mcp.server import Server
import mcp.types as types
from .schemas import BMIRequest
from .service import calculate_bmi_logic
import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create the MCP Server
bmi_server = Server("bmi-mcp-server")

# --- WIDGET URL FOR MCP APP ---
# For MCP apps in ChatGPT, ChatGPT fetches widgets via HTTP, not MCP resources
# Update this when you move to a permanent host
PUBLIC_URL = "https://hefty-phototropically-thomas.ngrok-free.dev"
WIDGET_URL = f"{PUBLIC_URL}/widget"

# --- CRITICAL PATCHES FOR SKYBRIDGE INTEGRATION ---
# 1. Force Pydantic models to use aliases (meta -> _meta) during serialization
_orig_CTR_dump = types.CallToolResult.model_dump
def _patched_CTR_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_CTR_dump(self, **kwargs)
types.CallToolResult.model_dump = _patched_CTR_dump

_orig_CTR_dump_json = types.CallToolResult.model_dump_json
def _patched_CTR_dump_json(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_CTR_dump_json(self, **kwargs)
types.CallToolResult.model_dump_json = _patched_CTR_dump_json

_orig_Tool_dump = types.Tool.model_dump
def _patched_Tool_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_Tool_dump(self, **kwargs)
types.Tool.model_dump = _patched_Tool_dump

_orig_Tool_dump_json = types.Tool.model_dump_json
def _patched_Tool_dump_json(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_Tool_dump_json(self, **kwargs)
types.Tool.model_dump_json = _patched_Tool_dump_json

_orig_TextContent_dump = types.TextContent.model_dump
def _patched_TextContent_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_TextContent_dump(self, **kwargs)
types.TextContent.model_dump = _patched_TextContent_dump

_orig_TextContent_dump_json = types.TextContent.model_dump_json
def _patched_TextContent_dump_json(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_TextContent_dump_json(self, **kwargs)
types.TextContent.model_dump_json = _patched_TextContent_dump_json
# --------------------------------------------------

@bmi_server.list_resources()
async def list_resources() -> list[types.Resource]:
    """List available resources (like the interactive widget)."""
    return [
        types.Resource(
            uri="ui://widget/bmi-dashboard.html",
            name="BMI Widget",
            mimeType="text/html+skybridge",
            description="Interactive BMI calculator dashboard"
        )
    ]

@bmi_server.read_resource()
async def read_resource(uri: str) -> types.ReadResourceResult:
    """Read the content of a resource."""
    logger.info(f"read_resource called with uri: {uri}")
    if str(uri) == "ui://widget/bmi-dashboard.html":
        widget_path = os.path.join(os.getcwd(), "static", "widget.html")
        logger.info(f"Reading widget from: {widget_path}")
        if os.path.exists(widget_path):
            with open(widget_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Widget content loaded, size: {len(content)} bytes")
                return types.ReadResourceResult(
                    contents=[
                        types.TextResourceContents(
                            uri=uri,
                            mimeType="text/html+skybridge",
                            text=content
                        )
                    ]
                )
        else:
            logger.error(f"Widget file not found at: {widget_path}")
    logger.error(f"Resource not found: {uri}")
    raise ValueError(f"Resource not found: {uri}")

@bmi_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available BMI tools with OpenAI-specific metadata."""
    return [
        types.Tool(
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
            meta={
                "openai/outputTemplate": WIDGET_URL,
                "openai/toolInvocation/invoking": "Calculating BMI...",
                "openai/toolInvocation/invoked": "BMI calculated."
            }
        )
    ]

@bmi_server.call_tool()
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    """Handle BMI tool calls."""
    if name == "calculate_bmi":
        try:
            # Validate and calculate
            request = BMIRequest(**arguments)
            response = calculate_bmi_logic(request)
            
            # Map input to metric for widget
            if request.unit == "metric":
                weight_kg = request.weight
                # Handle cases where height might be in cm or m
                height_m = request.height / 100 if request.height > 10 else request.height
            else:
                weight_kg = request.weight * 0.453592
                height_m = request.height * 0.0254
            
            result_text = (
                f"Your BMI for {request.weight} {'kg' if request.unit == 'metric' else 'lbs'} and {request.height} {'m' if request.unit == 'metric' else 'in'} ({height_m:.2f} m) is:\n\n"
                f"**BMI: {response.bmi}**\n"
                f"**Category: {response.category}**\n\n"
                f"Interpretation: {response.interpretation}\n\n"
                f"📞 The interactive BMI dashboard is being displayed above."
            )
            
            # Match keys exactly as expected by widget.html
            structured_data = {
                "bmi": response.bmi,
                "status": response.category,
                "heightM": height_m,
                "weightKg": weight_kg,
                "interpretation": response.interpretation
            }

            logger.info(f"Tool calculate_bmi success. BMI: {response.bmi}")

            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result_text)],
                structuredContent=structured_data,
                meta={
                    "openai/outputTemplate": WIDGET_URL
                }
            )
        except Exception as e:
            logger.error(f"Error in call_tool: {str(e)}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error during calculation: {str(e)}")],
                isError=True
            )
            
    raise ValueError(f"Tool not found: {name}")

# --- FIX SDK STRIPPING META ---
# The SDK's call_tool decorator manually reconstructs CallToolResult WITHOUT the meta field.
# We must wrap the handler to re-inject the meta field before it gets serialized.
_orig_handler = bmi_server.request_handlers.get(types.CallToolRequest)

async def _patched_handler(request):
    logger.info(f"Patched handler intercepted call for: {getattr(request.params, 'name', 'unknown')}")
    response = await _orig_handler(request)
    
    # response is likely a ServerResult wrapping a CallToolResult
    if hasattr(response, "root") and isinstance(response.root, types.CallToolResult):
        if getattr(request.params, "name", None) == "calculate_bmi":
            logger.info("Re-injecting openai/outputTemplate meta into CallToolResult")
            response.root.meta = {
                "openai/outputTemplate": WIDGET_URL
            }
            logger.info(f"After injection, response.root.meta = {response.root.meta}")
            logger.info(f"READY TO SEND TO CHATGPT")
            logger.info(f"Tool result - text: {len(response.root.content[0].text) if response.root.content else 0} chars")
            logger.info(f"Tool result - structuredContent keys: {list(response.root.structuredContent.keys()) if response.root.structuredContent else None}")
            logger.info(f"Tool result - meta outputTemplate: {response.root.meta.get('openai/outputTemplate')}")
    return response

# Re-register the patched handler
if _orig_handler:
    bmi_server.request_handlers[types.CallToolRequest] = _patched_handler
# ------------------------------
