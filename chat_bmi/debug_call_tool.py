import asyncio
from app.mcp_server import call_tool

async def main():
    res = await call_tool("calculate_bmi", {"height":1.75, "weight":70, "unit":"metric"})
    print(res)
    # show the pydantic json output with default and alias modes
    print("dump_json (default):\n", res.model_dump_json(indent=2))
    print("dump_json (by_alias=True):\n", res.model_dump_json(by_alias=True, indent=2))

asyncio.run(main())
