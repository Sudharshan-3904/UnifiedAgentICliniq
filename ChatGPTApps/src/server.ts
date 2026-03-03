import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import * as z from "zod";

const app = express();
app.use(express.json());

const port = Number(process.env.PORT) || 3000;

const TEMPLATE_URI = "ui://widget/bmi-dashboard.html";

const widgetHtml = `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>BMI Dashboard</title>
<style>
body {
  margin:0;
  font-family: system-ui, sans-serif;
  background: transparent;
}
.card {
  background: #0f172a;
  color: white;
  border-radius: 20px;
  padding: 24px;
  width: 320px;
  box-shadow: 0 20px 30px rgba(0,0,0,0.4);
}
.bmi {
  font-size: 48px;
  font-weight: bold;
}
.status {
  margin-top: 8px;
  font-weight: 600;
}
.stat {
  margin-top: 12px;
  font-size: 14px;
}
</style>
</head>
<body>
<div class="card">
  <div>BMI Result</div>
  <div class="bmi" id="bmi">--</div>
  <div class="status" id="status">--</div>
  <div class="stat">Height: <span id="h"></span></div>
  <div class="stat">Weight: <span id="w"></span></div>
</div>

<script>
function render(data){
  if(!data) return;

  document.getElementById("bmi").textContent = data.bmi;
  document.getElementById("status").textContent = data.status;
  document.getElementById("h").textContent = data.heightM + " m";
  document.getElementById("w").textContent = data.weightKg + " kg";

  let color = "#2ecc71";
  if(data.bmi < 18.5) color = "#3498db";
  else if(data.bmi < 25) color = "#2ecc71";
  else if(data.bmi < 30) color = "#f1c40f";
  else color = "#e74c3c";

  document.getElementById("bmi").style.color = color;
  document.getElementById("status").style.color = color;
}

render(window.openai?.toolOutput);

window.addEventListener("openai:set_globals", (event) => {
  render(event.detail?.globals?.toolOutput);
});
</script>
</body>
</html>
`.trim();

/* ---------------------------------------------------------
   MCP Server Factory
----------------------------------------------------------*/
function createMcpServer() {
    const server = new McpServer(
        { name: "bmi-calculator-app", version: "6.0.0" },
        { capabilities: { tools: {}, resources: {} } }
    );

    server.registerResource("bmi-widget", TEMPLATE_URI, {}, async () => ({
        contents: [
            {
                uri: TEMPLATE_URI,
                mimeType: "text/html+skybridge",
                text: widgetHtml,
            },
        ],
    }));

    server.registerTool(
        "calculate_bmi",
        {
            title: "BMI Calculator",
            description: "Calculate BMI and render dashboard.",
            inputSchema: {
                weight: z.number(),
                weightUnit: z.enum(["kg", "lb"]).default("kg"),
                height: z.number(),
                heightUnit: z.enum(["m", "cm", "in"]).default("m"),
            },
            _meta: {
                "openai/outputTemplate": TEMPLATE_URI,
                "openai/toolInvocation/invoking": "Calculating BMI...",
                "openai/toolInvocation/invoked": "BMI calculated.",
            },
        },
        async ({ weight, weightUnit, height, heightUnit }) => {
            let weightKg = weightUnit === "lb" ? weight * 0.453592 : weight;
            let heightM = height;
            if (heightUnit === "cm") heightM = height / 100;
            if (heightUnit === "in") heightM = height * 0.0254;

            const bmi = weightKg / (heightM * heightM);
            const result = {
                bmi: Number(bmi.toFixed(2)),
                weightKg: Number(weightKg.toFixed(2)),
                heightM: Number(heightM.toFixed(2)),
                status:
                    bmi < 18.5
                        ? "Underweight"
                        : bmi < 25
                            ? "Healthy Weight"
                            : bmi < 30
                                ? "Overweight"
                                : "Obese",
            };

            return {
                structuredContent: result,
                content: [
                    { type: "text", text: `BMI: ${result.bmi} (${result.status})` },
                ],
                _meta: {
                    "openai/outputTemplate": TEMPLATE_URI
                }
            };
        }
    );

    return server;
}

/* ---------------------------------------------------------
   MCP Session Storage
----------------------------------------------------------*/
const transports: Record<string, StreamableHTTPServerTransport> = {};

/* ---------------------------------------------------------
   MCP Endpoint
----------------------------------------------------------*/
app.post("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;

    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
        transport = transports[sessionId];
    }
    else if ((!sessionId || !transports[sessionId]) && (isInitializeRequest(req.body) || req.body.method === "initialize")) {

        transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: () => randomUUID(),
            onsessioninitialized: async (sid) => {
                transports[sid] = transport;
                console.log("[SESSION] Created:", sid);

                // Create a new server instance for this transport
                const server = createMcpServer();
                await server.connect(transport);
            },
        });

        transport.onclose = () => {
            if (transport.sessionId) {
                delete transports[transport.sessionId];
                console.log("[SESSION] Closed:", transport.sessionId);
            }
        };
    }
    else {
        res.status(400).json({
            jsonrpc: "2.0",
            error: { code: -32000, message: "Invalid session" },
            id: req.body.id || null,
        });
        return;
    }

    await transport.handleRequest(req, res, req.body);
});

/* ---------------------------------------------------------
   GET & DELETE for session handling
----------------------------------------------------------*/
app.get("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string;
    if (!sessionId) {
        console.log("[MCP] GET /mcp - Health check received (no session ID)");
        res.status(200).send("MCP Server Running");
        return;
    }
    if (!transports[sessionId]) {
        console.log(`[MCP] GET /mcp - Invalid session ID: ${sessionId}`);
        res.status(400).send("Invalid session");
        return;
    }
    await transports[sessionId].handleRequest(req, res);
});

app.delete("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string;
    if (!sessionId || !transports[sessionId]) {
        res.status(400).send("Invalid session");
        return;
    }
    await transports[sessionId].handleRequest(req, res);
});

/* ---------------------------------------------------------
   START SERVER
----------------------------------------------------------*/
app.listen(port, () => {
    console.log("--------------------------------------------------");
    console.log(`[READY] MCP Server running on http://localhost:${port}`);
    console.log("--------------------------------------------------");
});
