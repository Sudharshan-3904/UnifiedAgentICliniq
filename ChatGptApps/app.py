import ollama
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mcp_server import calculate_bmi_logic, render_external_app_logic
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
    },
    {
        "type": "function",
        "function": {
            "name": "render_external_app",
            "description": "Render an external application (map, wiki, health info) in an iframe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "enum": ["map", "wiki", "bmi_info"],
                        "description": "The app to display."
                    },
                },
                "required": ["app_name"],
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
                if call['function']['name'] == "calculate_bmi":
                    return calculate_bmi_logic(args['weight_kg'], args['height_m'])
                elif call['function']['name'] == "render_external_app":
                    return render_external_app_logic(args['app_name'])
        
        # If no tool was called, return error or generic response
        raise HTTPException(status_code=400, detail="The AI didn't detect weight/height values.")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/stream")
async def chat_stream(prompt: str):
    """
    Stream the chat result back as Server-Sent Events (SSE).
    Client should connect via EventSource to `/chat/stream?prompt=...`.
    """

    async def event_generator():
        try:
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
            )

            if response.get("message", {}).get("tool_calls"):
                for call in response["message"]["tool_calls"]:
                    args = call["function"]["arguments"]
                    if call["function"]["name"] == "calculate_bmi":
                        result = calculate_bmi_logic(args["weight_kg"], args["height_m"])
                    elif call["function"]["name"] == "render_external_app":
                        result = render_external_app_logic(args["app_name"])
                    
                    # Send a single SSE "data:" event containing the JSON result
                    yield f"data: {json.dumps(result)}\n\n"
            else:
                yield f"data: {json.dumps({"error": "AI did not detect weight/height values"})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({"error": str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 3. Serve the frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("🚀 Local BMI AI App starting at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
