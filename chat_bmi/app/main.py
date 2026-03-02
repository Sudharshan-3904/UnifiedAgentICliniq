from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from mcp.server.sse import SseServerTransport
import logging

from .api import router as api_router
from .widget import router as widget_router
from .mcp_server import bmi_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BMI MCP Server",
    description="Calculate BMI and provide health categories via official MCP.",
    version="0.2.0"
)

# Enable CORS for all origins (required for MCP and Widget integrations)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sse = SseServerTransport("/messages")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await bmi_server.run(read_stream, write_stream, bmi_server.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# Include routers for traditional API and Widget
app.include_router(api_router)
app.include_router(widget_router)

@app.on_event("startup")
async def startup_event():
    logger.info("BMI MCP Server is starting up...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
