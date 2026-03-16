from mcp.server import Server
import inspect

server = Server("test")
try:
    print("Source of call_tool:", inspect.getsource(server.call_tool))
except:
    pass
