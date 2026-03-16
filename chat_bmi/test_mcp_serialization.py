import asyncio
import json
from app.mcp_server import bmi_server, WIDGET_URL
import mcp.types as types

async def test_mcp_response():
    # Simulate what happens when ChatGPT calls the tool via MCP
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(
            name="calculate_bmi",
            arguments={"height": 1.75, "weight": 70, "unit": "metric"}
        )
    )
    
    # Get the handler
    handler = bmi_server.request_handlers.get(types.CallToolRequest)
    if not handler:
        print("No handler found!")
        return
    
    # Call it
    response = await handler(request)
    print(f"Response type: {type(response)}")
    print(f"Response: {response}")
    
    if hasattr(response, "root"):
        result = response.root
        print(f"\nCallToolResult.meta: {result.meta}")
        print(f"\nSerialized (model_dump): {json.dumps(result.model_dump(), indent=2)}")
        print(f"\nSerialized (model_dump_json): {result.model_dump_json(indent=2)}")

asyncio.run(test_mcp_response())
