from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from starlette.types import Scope, Receive, Send
from starlette.routing import Route as StarletteRoute
import logging

from .api import router as api_router
from .widget import router as widget_router
from .mcp_server import bmi_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable redirect_slashes to prevent 307 redirects to /sse/
app = FastAPI(
    title="BMI MCP Server",
    description="Calculate BMI and provide health categories via official MCP.",
    version="0.2.0",
    redirect_slashes=False
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared SSE transport instance
sse = SseServerTransport("/messages")

# --- ASGI APP WRAPPER ---
# This wrapper explicitly signals to Starlette/FastAPI that these are raw ASGI apps,
# bypassing all the high-level response wrapping that was causing TypeError and RuntimeError.
class ASGIAppWrapper:
    def __init__(self, func):
        self.func = func
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        await self.func(scope, receive, send)

async def handle_sse(scope: Scope, receive: Receive, send: Send):
    """Raw ASGI handler for SSE transport."""
    logger.info("SSE connection initiated")
    try:
        async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await bmi_server.run(read_stream, write_stream, bmi_server.create_initialization_options())
    except Exception as e:
        logger.error(f"Error in SSE handler: {e}")

async def handle_messages(scope: Scope, receive: Receive, send: Send):
    """Raw ASGI handler for POST messages."""
    try:
        await sse.handle_post_message(scope, receive, send)
    except Exception as e:
        logger.error(f"Error in Messages handler: {e}")

# Inject raw ASGI routes directly into the router using StarletteRoute + Wrapper
# This is the cleanest way to have raw ASGI handlers in a FastAPI app.
app.router.routes.append(StarletteRoute("/sse", ASGIAppWrapper(handle_sse), methods=["GET"]))
app.router.routes.append(StarletteRoute("/messages", ASGIAppWrapper(handle_messages), methods=["POST"]))

# Include routers for traditional API and Widget
app.include_router(api_router)
app.include_router(widget_router)

@app.on_event("startup")
async def startup_event():
    logger.info("BMI MCP Server is starting up...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
