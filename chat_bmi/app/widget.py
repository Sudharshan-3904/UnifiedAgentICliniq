from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()

@router.get("/widget", response_class=HTMLResponse)
async def get_widget():
    # Construct the path to the widget.html file
    widget_path = os.path.join(os.getcwd(), "static", "widget.html")
    
    if not os.path.exists(widget_path):
        return HTMLResponse(content="<h1>Widget Not Found</h1>", status_code=404)
        
    with open(widget_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Standard widget serving with headers to allow iframing in ChatGPT
    headers = {
        "Content-Security-Policy": "frame-ancestors https://chatgpt.com https://*.chatgpt.com",
        "X-Frame-Options": "ALLOWALL" # Legacy fallback for some clients
    }
        
    return HTMLResponse(content=content, headers=headers)
