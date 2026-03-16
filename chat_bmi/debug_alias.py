import mcp.types as types

for cls in [types.CallToolResult, types.Tool, types.TextContent]:
    field = cls.model_fields.get("meta")
    print(f"{cls.__name__}.meta alias ->", field.alias if field else None)
