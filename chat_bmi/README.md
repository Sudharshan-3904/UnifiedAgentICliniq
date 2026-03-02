# 🚀 BMI Real MCP Server (SSE) & Widget UI

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for BMI calculations, featuring an official SSE transport and a premium widget UI.

## 📁 Project Structure
```
bmi-mcp/
│
├── app/
│   ├── main.py       # App entry point & CORS
│   ├── api.py        # Logic endpoints
│   ├── schemas.py    # Pydantic models
│   ├── service.py    # Business logic
│   └── widget.py     # Widget renderer
│
├── static/
│   └── widget.html   # Premium Widget UI
│
├── tests/
│   └── test_bmi.py   # Pytest suite
│
├── pyproject.toml    # Dependencies
├── tool_schema.json  # OpenAI Tool Schema
└── README.md         # This guide
```

## 🛠️ Setup Instructions

### 1. Install Dependencies
Ensure you have Python 3.10+ and Poetry (or just use pip).
```bash
pip install fastapi uvicorn pydantic httpx pytest
```

### 2. Run Locally
```bash
uvicorn app.main:app --reload
```
The server will be available at `http://localhost:8000`.

### 3. Verify Health
```bash
curl http://localhost:8000/health
```

## 🧪 Testing
Run the test suite using pytest:
```bash
pytest
```

## � Connection as a Real MCP Server

This server now supports the official MCP SSE transport.

- **SSE Endpoint**: `https://your-domain.com/sse`
- **Messages Endpoint**: `https://your-domain.com/messages`

### How it works:
1. **Handshake**: The client connects to `/sse` to receive a `text/event-stream`.
2. **Endpoint Discovery**: The server sends an `endpoint` event containing the URL for posting messages (typically `/messages`).
3. **Tool Listing**: The client requests available tools via JSON-RPC.
4. **Execution**: The `calculate_bmi` tool is executed on the server.

To make this server work inside ChatGPT as an Action with a Widget:

### 1. Deploy Your Server
ChatGPT requires a public **HTTPS** URL. 
- **Production**: Deploy to [Render](https://render.com), [Railway](https://railway.app), or [Fly.io](https://fly.io).
- **Local Testing**: Use [ngrok](https://ngrok.com/) to create a secure tunnel to your local port 8000:
  ```bash
  ngrok http 8000
  ```

### 2. Configure GPT Actions
1. Go to **[ChatGPT](https://chatgpt.com)** and select **Explore GPTs** -> **+ Create**.
2. Go to the **Configure** tab.
3. Scroll down and click **Create new action**.
4. In the **Schema** section, copy and paste the entire content of your `tool_schema.json`.
5. Under **Authentication**, select **None** (unless you add an API key later).
6. Under **Privacy Policy**, enter your deployment URL (e.g., `https://your-app.render.com/privacy`).

### 3. Enable the Custom Widget
If your ChatGPT account supports Custom Widgets:
1. Look for the **Widget URL** field in the Action configuration.
2. Set it to: `https://your-domain.com/widget`
3. Ensure **CORS** is working (pre-configured in `app/main.py`).

### 4. Test the Integration
In the GPT Preview pane, type:
> "Calculate BMI for 70kg and 1.75m"

- ChatGPT should ask for permission to talk to your server.
- After you click **Allow**, the `/bmi` tool will be called.
- The **BMI Widget** should appear in the chat interface, allowing you to interact with the UI directly.

## 🚀 Deployment
You can deploy this to **Render**, **Railway**, or any Python-compatible host.
- **Render**: Connect your repo, select "Web Service", and use `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **CORS**: This server is pre-configured with CORS enabled for all origins to ensure smooth iframe integration.

## 📊 Example cURL
```bash
curl -X POST http://localhost:8000/bmi \
     -H "Content-Type: application/json" \
     -d '{"height": 1.75, "weight": 70, "unit": "metric"}'
```
