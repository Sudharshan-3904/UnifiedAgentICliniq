from __future__ import annotations

import os
import sys
import json
from typing import Final

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP

from bmi_logic import calculate_bmi

# --- MCP Server Definition ---
mcp = FastMCP("Sujit BMI Advisor")

@mcp.tool()
async def calculate_bmi_tool(height: float, weight: float) -> str:
    """
    Calculate Body Mass Index (BMI) and return detailed results.
    :param height: Height in meters (e.g., 1.75)
    :param weight: Weight in kilograms (e.g., 70)
    :return: JSON string with BMI results or Error message.
    """
    try:
        result = calculate_bmi(height, weight)
        return json.dumps(result.to_dict())
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- SSE Web Server (FastAPI) ---
# This allows the MCP server to be accessed via HTTP/SSE by the frontend
if "--web" in sys.argv:
    app = mcp.sse_app()
    
    # Path to frontend build (we will build it later)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

    # Add CORS - CRITICAL for browser-based MCP clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve static files from the frontend build directory
    if os.path.exists(FRONTEND_DIST):
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
        print(f"[*] Serving frontend from {FRONTEND_DIST}")
    else:
        print(f"[!] Warning: Frontend dist folder not found at {FRONTEND_DIST}. Running without static UI.")

    print("[*] Starting Sujit BMI MCP Server on http://127.0.0.1:8000")
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
else:
    # Default MCP run (for Claude Desktop etc.)
    mcp.run()
