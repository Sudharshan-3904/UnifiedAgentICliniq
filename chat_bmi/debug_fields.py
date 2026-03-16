
import mcp.types as types
print("Fields in CallToolResult:")
for name, field in types.CallToolResult.model_fields.items():
    print(f"Name: {name}, Alias: {field.alias}")

result = types.CallToolResult(content=[])
print("\nInstance Dict:")
print(result.__dict__)

# Try setting via key
try:
    result = types.CallToolResult(content=[], _meta={"test": 1})
    print("\nSetting via _meta works")
except Exception as e:
    print(f"\nSetting via _meta failed: {e}")

try:
    result = types.CallToolResult(content=[], meta={"test": 1})
    print("\nSetting via meta works")
    print(result.model_dump(by_alias=True))
except Exception as e:
    print(f"\nSetting via meta failed: {e}")
