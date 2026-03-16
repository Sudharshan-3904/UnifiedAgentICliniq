from mcp.server import Server
import inspect

server = Server("test")
print("call_tool methods:", [m for m in dir(server) if "call_tool" in m])
print("list_tools methods:", [m for m in dir(server) if "list_tools" in m])

# Inspect the decorator implementation
try:
    print("Source of list_tools:", inspect.getsource(server.list_tools))
except:
    pass
