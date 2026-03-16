
import mcp.types as types
import json

# Apply the same patches as in the server
_orig_CTR_dump = types.CallToolResult.model_dump
def _patched_CTR_dump(self, **kwargs):
    kwargs["by_alias"] = True
    return _orig_CTR_dump(self, **kwargs)
types.CallToolResult.model_dump = _patched_CTR_dump

result = types.CallToolResult(
    content=[types.TextContent(type="text", text="test")],
    meta={"openai/outputTemplate": "https://example.com/widget"}
)

print("Model Dump (with patch):")
print(json.dumps(result.model_dump(), indent=2))

print("\nModel Dump JSON (might bypass patch if it calls original Pydantic methods):")
try:
    print(result.model_dump_json(indent=2))
except Exception as e:
    print(f"Error: {e}")

# Check if 'meta' has an alias
field = types.CallToolResult.model_fields.get("meta")
if field:
    print(f"\nMeta field alias: {field.alias}")
else:
    print("\nMeta field not found in model_fields")
