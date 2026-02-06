# BMI Advisor: Pure MCP Implementation

A high-performance BMI calculator built strictly on the **Model Context Protocol (MCP)**. This project demonstrates idiomatic Python patterns and direct browser-to-MCP interaction.

## Features
- **Pure MCP**: Built with `FastMCP`, exposing tools following the official protocol.
- **Idiomatic Python**: Uses `dataclasses` and `Enum` for a clean, type-safe backend.
- **ChatGPT UI**: A modern web interface that acts as a native MCP client over SSE (Server-Sent Events).

## Architecture
- **Backend (`backend/server.py`)**: A standalone MCP server.
- **Frontend (`frontend/`)**: A ChatGPT-inspired UI that communicates directly with the MCP server tools.

## Setup & Running

### 1. Install Dependencies
```bash
cd backend
pip install fastmcp mcp
```

### 2. Start the MCP Server
To allow the web frontend to connect, run the server in SSE mode:
```bash
python server.py --web
```
*The server will run at `http://localhost:8000` by default.*

### 3. Open the UI
Because the backend is a pure MCP server, you can open the frontend from your file system:
- Open `frontend/index.html` in any modern browser.

### 4. Direct Tool Usage
Ask the advisor: *"My weight is 72kg and I am 1.78m tall"* to trigger the MCP tool.

## Use with MCP Clients
You can also use this as a standard MCP server for apps like Claude Desktop:
```json
{
  "mcpServers": {
    "bmi-advisor": {
      "command": "python",
      "args": ["j:/Projects/Code/UnifiedAgentICliniq/Chatapp/bmi_mcp_server/backend/server.py"]
    }
  }
}
```

## ChatGPT Integration (Beta)

ChatGPT now supports **Custom MCP Servers** natively. To connect this advisor:

1. **Get a Public URL**: Install [ngrok](https://ngrok.com/) and run:
   ```bash
   ngrok http 8000
   ```
2. **Copy the URL**: Find the `Forwarding` URL (it looks like `https://xxxx-xxxx.ngrok-free.app`).
3. **Configure ChatGPT**:
   - Go to ChatGPT → **Apps** → **Add New App** (Beta).
   - Name: `BMI Advisor`.
   - **MCP Server URL**: Append `/sse` to your ngrok URL.
     - Example: `https://xxxx-xxxx.ngrok-free.app/sse`
   - Authentication: `No Auth`.
4. **Chat**: You can now ask ChatGPT "Calculate my BMI using the BMI Advisor app"!
