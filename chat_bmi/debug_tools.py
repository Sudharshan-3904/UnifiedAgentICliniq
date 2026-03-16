import asyncio
from app.mcp_server import list_tools, widget_url

async def main():
    tools = await list_tools()
    print(tools)
    for t in tools:
        print('name', t.name, 'meta', t.meta)
        print('dump', t.model_dump())
    print('widget url returned', widget_url())

asyncio.run(main())
