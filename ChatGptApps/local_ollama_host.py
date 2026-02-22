import ollama
import json
from mcp_server import calculate_bmi_logic

# Configure your model name
MODEL = "llama3.2" # Change this to "gemma3" or your specific local model

# 1. Define the tool for Ollama
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_bmi",
            "description": "Calculate Body Mass Index (BMI) based on weight and height.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_kg": {
                        "type": "number",
                        "description": "User's weight in kilograms",
                    },
                    "height_m": {
                        "type": "number",
                        "description": "User's height in meters",
                    },
                },
                "required": ["weight_kg", "height_m"],
            },
        },
    }
]

def run_local_chat(user_prompt):
    print(f"--- User Prompt: {user_prompt} ---")
    
    # 2. Initial chat with tools
    response = ollama.chat(
        model=MODEL,
        messages=[{'role': 'user', 'content': user_prompt}],
        tools=tools,
    )

    # 3. Check if the model wants to call the tool
    if response.get('message', {}).get('tool_calls'):
        for call in response['message']['tool_calls']:
            args = call['function']['arguments']
            print(f"Model wants to use tool with args: {args}")
            
            # Execute the BMI tool logic
            result = calculate_bmi_logic(args['weight_kg'], args['height_m'])
            
            # Formulate the response as ChatGPT would
            # (In ChatGPT, this 'result' would trigger the 'index.html' UI)
            print(f"BMI Tool Results: {result}")
            
            # 4. Return the result to the model
            final_response = ollama.chat(
                model=MODEL,
                messages=[
                    {'role': 'user', 'content': user_prompt},
                    response['message'],
                    {
                        'role': 'tool',
                        'content': json.dumps(result),
                    }
                ],
            )
            print(f"Final Answer: {final_response['message']['content']}")
            
            # Reminder for the UI
            print("\nUI Note: To see the 'structuredContent' inside your index.html,")
            print("   open index.html in a browser and paste the following into the console:")
            print(f"   window.postMessage({{jsonrpc: '2.0', method: 'ui/notifications/tool-result', params: {{structuredContent: {json.dumps(result)} }} }}, '*');")

if __name__ == "__main__":
    # Test with a local prompt
    run_local_chat("I weigh 75kg and my height is 1.8 meters. What's my BMI?")
