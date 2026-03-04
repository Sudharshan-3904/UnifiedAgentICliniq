# Health Dashboard — MCP Server
### OpenAI Apps SDK · Plain JavaScript · Multi-Platform

A working MCP server prototype built with **vanilla Node.js (no TypeScript)** following the [OpenAI Apps SDK quickstart](https://developers.openai.com/apps-sdk/quickstart/).

The backend is designed so you can later plug it into **Claude** and **Grok** as well — same `/mcp` endpoint, different connector UIs.

---

## What's inside

| File | Purpose |
|---|---|
| `server.js` | MCP server — Node.js ESM, StreamableHTTP transport |
| `public/widget.html` | Self-contained widget UI rendered inside ChatGPT |
| `package.json` | Dependencies (`@modelcontextprotocol/sdk`, `zod`) |

### Tools exposed

| Tool | Description |
|---|---|
| `calculate_bmi` | Calculates BMI from weight (kg) + height (cm), shows visual result widget |
| `get_bmi_history` | Returns list of all calculated records in a history widget |
| `clear_bmi_history` | Clears all stored records |

---

## Quick Start (Windows)

### Step 1 — Install dependencies

```bash
npm install
```

### Step 2 — Run the server

```bash
node server.js
```

You should see:
```
  Server:    http://localhost:8787
  MCP URL:   http://localhost:8787/mcp
  Widget:    http://localhost:8787/widget
```

### Step 3 — Expose with ngrok (free tier)

Open a **new** terminal window:

```bash
ngrok http 8787 --host-header=localhost:8787
```

You'll get something like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8787
```

### Step 4 — Set BASE_URL (important!)

Stop the server (`Ctrl+C`) and restart with:

**Windows PowerShell:**
```powershell
$env:PORT="8787"; $env:BASE_URL="https://abc123.ngrok-free.app"; node server.js
```

**Windows CMD:**
```cmd
set PORT=8787 && set BASE_URL=https://abc123.ngrok-free.app && node server.js
```

### Step 5 — Add to ChatGPT

1. Enable **Developer Mode**: ChatGPT → Settings → Apps & Connectors → Advanced Settings
2. Go to **Settings → Connectors → Create**
3. Paste your MCP URL:
   ```
   https://abc123.ngrok-free.app/mcp
   ```
4. Name it `Health Dashboard` and click **Create**
5. Open a new chat, click **+** → **More** → select your connector

### Step 6 — Test it

Ask ChatGPT:
- _"Calculate my BMI — I weigh 75 kg and I'm 1.78 m tall"_
- _"Show me my BMI history"_
- _"What's the BMI for 90kg and 180cm?"_

---

## Adapting to Claude

Claude (Anthropic) supports the same MCP protocol over StreamableHTTP.

When Claude's connector UI is available:
1. Use the **same** `https://your-url/mcp` endpoint
2. No code changes needed — the server is platform-agnostic
3. The widget HTML won't render in Claude (Claude doesn't support the Apps SDK UI), but all **tool calls and structured data** will work perfectly

## Adapting to Grok

Same story — use the `/mcp` endpoint. Grok's MCP connector uses the same protocol. The tools will work; the widget UI is ChatGPT-specific.

---

## Development tips

- Run `node --watch server.js` for auto-restart on file changes
- Preview the widget in any browser: `http://localhost:8787/widget`
- Test MCP tools without ChatGPT:
  ```bash
  npx @modelcontextprotocol/inspector@latest http://localhost:8787/mcp
  ```
- The server is **stateless per request** — in production, replace the `bmiHistory` array with a database (SQLite, PostgreSQL, etc.)

---

## Project structure for growth

```
mcp-chatgpt-app/
├── server.js              ← MCP server (extend tools here)
├── package.json
├── public/
│   └── widget.html        ← Widget UI (extend views here)
└── README.md
```

To add a new tool: copy the `server.registerTool(...)` block pattern in `server.js`.
To add a new view: add a new `render*()` function in `widget.html` and branch on the `toolOutput` shape.
