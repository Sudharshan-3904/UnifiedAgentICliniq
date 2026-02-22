import ollama
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mcp_server import calculate_bmi_logic
import uvicorn

app = FastAPI()

# Model configuration
MODEL = "llama3.2" # Update this to your local model

class ChatRequest(BaseModel):
    prompt: str

# 1. Define the tool for Ollama (same as in our host script)
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_bmi",
            "description": "Calculate Body Mass Index (BMI) based on weight and height.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_kg": {"type": "number"},
                    "height_m": {"type": "number"},
                },
                "required": ["weight_kg", "height_m"],
            },
        },
    }
]

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Step 1: Initial call to Ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': request.prompt}],
            tools=tools,
        )

        # Step 2: Protocol check for tool calls
        if response.get('message', {}).get('tool_calls'):
            for call in response['message']['tool_calls']:
                args = call['function']['arguments']
                # Execute the shared logic
                result = calculate_bmi_logic(args['weight_kg'], args['height_m'])
                # Return the structured data directly to the frontend
                return result
        
        # If no tool was called, return error or generic response
        raise HTTPException(status_code=400, detail="The AI didn't detect weight/height values.")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 3. Serve the frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("🚀 Local BMI AI App starting at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
