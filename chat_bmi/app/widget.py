from fastapi import APIRouter, Response, Request
import os
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/widget")
async def get_widget(request: Request):
    """Serve the BMI widget HTML."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(f"=== WIDGET REQUEST ===")
    logger.info(f"From: {client_ip}")
    logger.info(f"User-Agent: {user_agent}")
    logger.info(f"All headers: {dict(request.headers)}")
    
    # Construct the path to the widget.html file
    widget_path = os.path.join(os.getcwd(), "static", "widget.html")
    logger.info(f"Looking for widget at: {widget_path}")
    
    if not os.path.exists(widget_path):
        logger.error(f"Widget file NOT FOUND at: {widget_path}")
        return Response(content="<h1>Widget Not Found</h1>", status_code=404)
    
    logger.info(f"Widget file found")
        
    with open(widget_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    logger.info(f"Widget content loaded: {len(content)} bytes")
        
    # Critical headers for Skybridge interactive widgets
    headers = {
        "Content-Security-Policy": "frame-ancestors https://chatgpt.com https://*.chatgpt.com *;",
        "X-Frame-Options": "ALLOWALL",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }
    
    logger.info(f"Serving widget with headers: {headers}")
    logger.info(f"=== END WIDGET REQUEST ===")

    # The profile=mcp-app is required for ChatGPT to render the widget correctly
    return Response(
        content=content, 
        media_type="text/html; profile=mcp-app; charset=utf-8", 
        headers=headers
    )
