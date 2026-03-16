
import mcp.types as types
print("CallToolResult fields and their aliases:")
for name, field in types.CallToolResult.model_fields.items():
    print(f"Name: {name}, Alias: {field.alias}, Serialization: {field.serialization_alias}")

result = types.CallToolResult(content=[], meta={"foo": "bar"})
print("\nJSON (No alias):")
print(result.model_dump_json())
print("\nJSON (By alias):")
print(result.model_dump_json(by_alias=True))
