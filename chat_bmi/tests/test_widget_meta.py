from app.mcp_server import call_tool, list_tools, WIDGET_URL
from app.mcp_server import bmi_server
import asyncio


def test_tool_metadata_contains_outputtemplate():
    tools = asyncio.get_event_loop().run_until_complete(list_tools())
    assert any(t.name == "calculate_bmi" for t in tools)
    calc = next(t for t in tools if t.name == "calculate_bmi")
    # the MCP model stores metadata in a private field and only exposes it when
    # serialized, so dump and inspect that dictionary rather than the attribute.
    dumped = calc.model_dump()
    assert "meta" in dumped and dumped["meta"] is not None
    assert "openai/outputTemplate" in dumped["meta"]
    assert dumped["meta"]["openai/outputTemplate"] == WIDGET_URL


def test_call_tool_includes_outputtemplate():
    # exercise the call_tool function directly
    args = {"height": 1.8, "weight": 75, "unit": "metric"}
    result = asyncio.get_event_loop().run_until_complete(call_tool("calculate_bmi", args))
    assert result.meta is not None
    assert "openai/outputTemplate" in result.meta
    assert result.meta["openai/outputTemplate"] == WIDGET_URL
