from mcp.types import Tool
import pydantic

# Attempt to set _meta in constructor
try:
    t = Tool(name="test", description="...", inputSchema={}, _meta={"foo": "bar"})
    print("Constructor _meta:", t.model_dump_json(by_alias=True))
except Exception as e:
    print("Constructor _meta error:", e)

# Attempt to set via meta but with alias behavior
t2 = Tool(name="test", description="...", inputSchema={}, meta={"foo": "bar"})
print("Default dump:", t2.model_dump_json())
print("Alias dump:", t2.model_dump_json(by_alias=True))
