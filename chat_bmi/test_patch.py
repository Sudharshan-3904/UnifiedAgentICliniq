from mcp.types import Tool, CallToolResult, TextContent
import json

# Original behavior
t = Tool(name="test", description="...", inputSchema={}, meta={"foo": "bar"})
print("Original:", t.model_dump())

# Apply patch
_orig_tool_dump = Tool.model_dump
def _new_tool_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_tool_dump(self, **kwargs)
Tool.model_dump = _new_tool_dump

_orig_res_dump = CallToolResult.model_dump
def _new_res_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_res_dump(self, **kwargs)
CallToolResult.model_dump = _new_res_dump

print("Patched Tool:", t.model_dump())

res = CallToolResult(
    content=[TextContent(type="text", text="hi")],
    structuredContent={"a": 1},
    meta={"openai/outputTemplate": "ui://..."}
)
print("Patched Result:", res.model_dump())
