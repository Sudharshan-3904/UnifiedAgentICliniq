import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import * as z from "zod/v3";

const app = express();
app.use(express.json());

const port = Number(process.env.PORT) || 3000;

const TEMPLATE_URI = "ui://widget/bmi.html";

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

        const server = new McpServer(
            { name: "bmi-calculator-app", version: "5.0.0" },
            { capabilities: { tools: {} } }
        );

        /* ---------------------------------------------------------
           🖼 REGISTER WIDGET RESOURCE
        ----------------------------------------------------------*/

        const widgetHtml = `
      <div style="font-family:system-ui;padding:16px;max-width:420px;">
        <h2 style="margin-top:0;">BMI Dashboard</h2>

        <div style="font-size:36px;font-weight:bold;" id="bmi">--</div>
        <div id="status" style="margin-bottom:12px;">--</div>

        <div style="background:#eee;height:14px;border-radius:8px;overflow:hidden;">
          <div id="bar" style="height:100%;width:0%;transition:0.4s;"></div>
        </div>

        <div style="margin-top:12px;font-size:14px;">
          <div>Weight: <span id="weight"></span> kg</div>
          <div>Height: <span id="height"></span> m</div>
        </div>
      </div>

      <script>
        function render(data) {
          if (!data) return;

          const { bmi, status, weightKg, heightM } = data;

          document.getElementById("bmi").textContent = bmi;
          document.getElementById("status").textContent = status;
          document.getElementById("weight").textContent = weightKg;
          document.getElementById("height").textContent = heightM;

          const percent = Math.min((bmi / 40) * 100, 100);
          const bar = document.getElementById("bar");
          bar.style.width = percent + "%";

          if (bmi < 18.5) bar.style.background = "#3498db";
          else if (bmi < 25) bar.style.background = "#2ecc71";
          else if (bmi < 30) bar.style.background = "#f1c40f";
          else bar.style.background = "#e74c3c";
        }

        render(window.openai?.toolOutput);

        window.addEventListener(
          "openai:set_globals",
          (event) => {
            render(event.detail?.globals?.toolOutput);
          },
          { passive: true }
        );
      </script>
    `.trim();

        server.registerResource("bmi-widget", TEMPLATE_URI, {}, async () => ({
            contents: [
                {
                    uri: TEMPLATE_URI,
                    mimeType: "text/html;profile=mcp-app",
                    text: widgetHtml,
                },
            ],
        }));

        /* ---------------------------------------------------------
           🧮 SINGLE TOOL (CALCULATE + RENDER)
        ----------------------------------------------------------*/

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
                    "openai/toolInvocation/invoking": "Calculating BMI…",
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
                        {
                            type: "text",
                            text: `BMI: ${result.bmi} (${result.status})`,
                        },
                    ],
                };
            }
        );

        await server.connect(transport);
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

/* --------------------------------------------------------- */

app.listen(port, () => {
    console.log("--------------------------------------------------");
    console.log(`[READY] MCP Server running on port ${port}`);
    console.log("--------------------------------------------------");
});