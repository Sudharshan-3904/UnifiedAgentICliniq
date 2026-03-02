from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Final

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

# --- 1. Idiomatic Logic & Models ---

class BMICategory(Enum):
    UNDERWEIGHT = ("Underweight", "#3498db")
    NORMAL = ("Normal weight", "#2ecc71")
    OVERWEIGHT = ("Overweight", "#f39c12")
    OBESE = ("Obese", "#e74c3c")

    def __init__(self, label: str, color: str):
        self.label = label
        self.color = color

@dataclass(frozen=True)
class BMIResult:
    bmi: float
    category: BMICategory
    height: float
    weight: float

    def render_widget(self) -> str:
        return f"""
        <div class="bmi-card" style="border-radius: 12px; overflow: hidden; font-family: sans-serif; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 350px; margin: 10px 0;">
            <div style="background: {self.category.color}; padding: 15px; color: white; text-align: center;">
                <h3 style="margin: 0; font-size: 1.1rem;">BMI Health Advisor</h3>
            </div>
            <div style="padding: 20px; text-align: center;">
                <div style="font-size: 3rem; font-weight: 800; color: {self.category.color}; line-height: 1;">{self.bmi:.1f}</div>
                <div style="color: #666; margin-top: 5px; font-weight: 600;">{self.category.label}</div>
                
                <div style="display: flex; justify-content: space-around; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
                    <div>
                        <div style="font-size: 0.7rem; color: #999; text-transform: uppercase;">Height</div>
                            <div style="font-weight: 600;">{self.height:.2f}m</div>
                    </div>
                    <div>
                        <div style="font-size: 0.7rem; color: #999; text-transform: uppercase;">Weight</div>
                        <div style="font-weight: 600;">{self.weight:.1f}kg</div>
                    </div>
                </div>
            </div>
        </div>
        """

def calculate_bmi_core(height: float, weight: float) -> BMIResult:
    if height <= 0 or weight <= 0:
        raise ValueError("Height and weight must be positive.")
    # Normalize height: if a user (or client) supplied height in centimeters
    # (e.g. 167) we should convert to meters for BMI calculation.
    height_m = (height / 100.0) if height > 10 else height
    bmi = weight / (height_m ** 2)
    if bmi < 18.5: cat = BMICategory.UNDERWEIGHT
    elif bmi < 25: cat = BMICategory.NORMAL
    elif bmi < 30: cat = BMICategory.OVERWEIGHT
    else: cat = BMICategory.OBESE
    return BMIResult(bmi, cat, height_m, weight)

# --- 2. MCP Server Definition ---

mcp = FastMCP("BMI Advisor MCP")

@mcp.tool()
async def calculate_bmi(height: float, weight: float) -> str:
    """Calculate BMI and return a health widget."""
    try:
        result = calculate_bmi_core(height, weight)
        return result.render_widget()
    except Exception as e:
        return f"<div style='color:red;'>Error: {str(e)}</div>"

# --- 3. Unified Web Server (FastAPI) ---

if "--web" in sys.argv:
    # Use the established sse_app but we will wrap it to ensure it's fully ready
    app = mcp.sse_app()
    
    # Path relative to script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files (serve index.html at root)
    if os.path.exists(FRONTEND_PATH):
        app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
        print(f"[*] Serving frontend from {FRONTEND_PATH}")

    print("[*] Starting MCP Server on http://127.0.0.1:8000")
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
else:
    mcp.run()
