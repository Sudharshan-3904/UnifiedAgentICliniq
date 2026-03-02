import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import * as z from "zod";
import path from "node:path";

const app = express();
app.use(express.json());
app.use(express.static(path.join(process.cwd(), "public")));

const port = Number(process.env.PORT) || 3000;
let publicUrl = process.env.PUBLIC_URL || `http://localhost:${port}`;

const TEMPLATE_URI = "ui://widget/bmi-dashboard.html";

const widgetHtml = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMI Calculator</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --accent-blue: #3498db;
            --accent-green: #2ecc71;
            --accent-yellow: #f1c40f;
            --accent-red: #e74c3c;
            --bg-glass: rgba(255, 255, 255, 0.1);
            --border-glass: rgba(255, 255, 255, 0.2);
        }

        body {
            margin: 0;
            padding: 20px;
            font-family: 'Outfit', sans-serif;
            background: transparent;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
        }

        .widget-card {
            width: 320px;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
            position: relative;
            text-align: center;
        }

        .header-text {
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 20px;
            text-align: left;
        }

        .bmi-value {
            font-size: 5rem;
            font-weight: 700;
            margin: 0;
            line-height: 1;
            transition: color 0.5s ease;
        }

        .bmi-status {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            font-weight: 600;
            margin: 10px 0 30px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .check-icon {
            margin-right: 8px;
            width: 18px;
            height: 18px;
            background: currentColor;
            -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E") no-repeat center;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E") no-repeat center;
        }

        .stats-row {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-box {
            flex: 1;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-glass);
            border-radius: 15px;
            padding: 12px;
            text-align: left;
        }

        .stat-title {
            font-size: 0.65rem;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .stat-val {
            font-size: 1.2rem;
            font-weight: 600;
        }

    </style>
</head>
<body>
    <div class="widget-card">
        <div class="header-text">BMI Calculator</div>
        
        <div class="bmi-value" id="bmi-val">--</div>
        
        <div class="bmi-status" id="bmi-status-box">
            <span class="check-icon"></span>
            <span id="label-text">Calculating...</span>
        </div>

        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-title">Height</div>
                <div class="stat-val" id="h-val">--</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Weight</div>
                <div class="stat-val" id="w-val">--</div>
            </div>
        </div>
    </div>

    <script>
        function render(data) {
            if (!data) return;

            const bmi = parseFloat(data.bmi);
            const status = data.status;
            const h = (data.heightM * 100).toFixed(0);
            const w = data.weightKg.toFixed(0);

            // Set text
            document.getElementById('bmi-val').textContent = bmi.toFixed(1);
            document.getElementById('label-text').textContent = status;
            document.getElementById('h-val').textContent = h + ' cm';
            document.getElementById('w-val').textContent = w + ' kg';

            // Colors
            let color = '#2ecc71';
            let angle = 0; // -90 to 90
            
            if (bmi < 18.5) {
                color = '#3498db';
                angle = -67.5;
            } else if (bmi < 25) {
                color = '#2ecc71';
                angle = -22.5;
            } else if (bmi < 30) {
                color = '#f1c40f';
                angle = 22.5;
            } else {
                color = '#e74c3c';
                angle = 67.5;
            }

            // Apply styling
            const bmiText = document.getElementById('bmi-val');
            const statusBox = document.getElementById('bmi-status-box');

            bmiText.style.color = color;
            statusBox.style.color = color;
        }

        if (window.openai?.toolOutput) {
            render(window.openai.toolOutput);
        }

        window.addEventListener("openai:set_globals", (event) => {
            if (event.detail?.globals?.toolOutput) {
                render(event.detail.globals.toolOutput);
            }
        });
    </script>
</body>
</html>
`.trim();

/* ---------------------------------------------------------
   Detect ngrok automatically (optional but helpful)
----------------------------------------------------------*/
async function detectNgrok() {
    try {
        const res = await fetch("http://localhost:4040/api/tunnels");
        if (!res.ok) return;

        const data = await res.json() as any;
        if (data.tunnels?.length) {
            publicUrl = data.tunnels[0].public_url;
            console.log("[INIT] Detected ngrok URL:", publicUrl);
        }
    } catch {
        console.log("[INIT] Ngrok not detected (running local)");
    }
}

await detectNgrok();

/* ---------------------------------------------------------
   Serve MCP UI (CRITICAL PART)
----------------------------------------------------------*/
app.get("/ui/bmi-widget", (req, res) => {
    console.log("[UI] Widget requested");

    res.setHeader("Content-Type", "text/html; profile=mcp-app");
    // res.setHeader("Access-Control-Allow-Origin", "*");
    // res.setHeader("X-Frame-Options", "ALLOWALL");
    res.setHeader(
        "Content-Security-Policy",
        "frame-ancestors https://chatgpt.com https://*.chatgpt.com;"
    );

    res.sendFile(path.join(process.cwd(), "public", "index.html"));
});

/* ---------------------------------------------------------
   Tool Definition
----------------------------------------------------------*/
const toolDefinition = {
    name: "calculate_bmi",
    title: "BMI Calculator",
    description: "Calculates BMI and shows interactive dashboard",
    inputSchema: {
        weight: z.number(),
        weightUnit: z.enum(["kg", "lb"]).default("kg"),
        height: z.number(),
        heightUnit: z.enum(["m", "cm", "in"]).default("m"),
    },
    _meta: {
        "openai/outputTemplate": TEMPLATE_URI,
        "openai/toolInvocation/invoking": "Calculating BMI...",
        "openai/toolInvocation/invoked": "BMI calculated."
    }
};

/* ---------------------------------------------------------
   MCP Session Handling
----------------------------------------------------------*/
const transports: Record<string, StreamableHTTPServerTransport> = {};

app.post("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;

    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
        transport = transports[sessionId];
    }
    else if (!sessionId && (isInitializeRequest(req.body) || req.body.method === "initialize")) {

        transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: () => randomUUID(),
            onsessioninitialized: (sid) => {
                transports[sid] = transport;
                console.log("[SESSION] Created:", sid);
            }
        });

        transport.onclose = () => {
            if (transport.sessionId) {
                delete transports[transport.sessionId];
                console.log("[SESSION] Closed:", transport.sessionId);
            }
        };

        const server = new McpServer({
            name: "bmi-calculator-app",
            version: "3.0.0",
        });

        /* ---------------------------------------------------------
           REGISTER WIDGET RESOURCE
        ----------------------------------------------------------*/
        server.registerResource("bmi-widget", TEMPLATE_URI, {}, async () => ({
            contents: [
                {
                    uri: TEMPLATE_URI,
                    mimeType: "text/html+skybridge",
                    text: widgetHtml,
                },
            ],
        }));

        /* ---------------------------------------------------------
           REGISTER TOOL
        ----------------------------------------------------------*/
        server.registerTool(
            toolDefinition.name,
            toolDefinition as any,
            async ({ weight, weightUnit, height, heightUnit }: any) => {

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
                                    : "Obese"
                };

                console.log("[TOOL] BMI Calculated:", result);

                const response = {
                    content: [
                        { type: "text" as const, text: `BMI: ${result.bmi} (${result.status})` }
                    ],
                    structuredContent: result,
                    _meta: {
                        "openai/outputTemplate": TEMPLATE_URI
                    }
                };

                console.log("RETURNING TO CHATGPT:", JSON.stringify(response, null, 2));

                return response;
            }
        );

        await server.connect(transport as any);
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
   GET / DELETE Session
----------------------------------------------------------*/
app.get("/mcp", async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string;
    if (!sessionId || !transports[sessionId]) {
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
    console.log(`[READY] Server: http://localhost:${port}`);
    console.log(`[READY] UI Base: ${publicUrl}`);
    console.log("--------------------------------------------------");
});