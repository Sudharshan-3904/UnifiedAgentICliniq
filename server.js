/**
 * ============================================================
 *  Health Dashboard — MCP Server (Plain JavaScript / Node.js)
 * ============================================================
 *
 *  Uses the official @modelcontextprotocol/sdk with the
 *  StreamableHTTP transport so it works with:
 *    • ChatGPT  (Settings → Connectors → /mcp)
 *    • Claude   (same /mcp endpoint, different connector UI)
 *    • Grok     (same /mcp endpoint)
 *
 *  Endpoint:  POST/GET/DELETE  /mcp
 *  Health:    GET              /
 *  Widget UI: GET              /widget
 *
 *  Run:   node server.js
 *  Env:   PORT=8787   BASE_URL=https://your-ngrok-url.app
 * ============================================================
 */

import { createServer }                    from "node:http";
import { readFileSync }                    from "node:fs";
import { McpServer }                       from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport }   from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z }                               from "zod";

// ─── Config ────────────────────────────────────────────────────────────────
const PORT     = Number(process.env.PORT ?? 8787);
const BASE_URL = process.env.BASE_URL ?? `http://localhost:${PORT}`;
const MCP_PATH = "/mcp";

// ─── Widget HTML (served inline for the Apps SDK resource) ─────────────────
// Note: the original example stored this under public/widget.html, but our
// root-level `widget.html` already contains the full markup. Reading directly
// from the top–level file avoids an empty public copy and keeps a single
// source of truth.
const WIDGET_HTML = readFileSync("widget.html", "utf8");

// ─── In-memory BMI history  (replace with a DB in production) ──────────────
let bmiHistory = [];

// ─── BMI calculation helpers ────────────────────────────────────────────────
function calcBMI(weightKg, heightM) {
  return Math.round((weightKg / (heightM * heightM)) * 10) / 10;
}

function bmiCategory(bmi) {
  if (bmi < 18.5) return "Underweight";
  if (bmi < 25)   return "Normal weight";
  if (bmi < 30)   return "Overweight";
  if (bmi < 35)   return "Obese (Class I)";
  if (bmi < 40)   return "Obese (Class II)";
  return "Obese (Class III)";
}

function bmiAdvice(bmi) {
  if (bmi < 18.5)
    return "Your BMI suggests you may be underweight. Consider consulting a nutritionist to build a balanced diet plan that supports healthy weight gain.";
  if (bmi < 25)
    return "Great news — your BMI is in the healthy range! Keep up your current lifestyle with regular exercise and a balanced diet.";
  if (bmi < 30)
    return "Your BMI is slightly above the healthy range. Small changes like 30 minutes of daily walking and reducing processed foods can make a big difference.";
  if (bmi < 35)
    return "Your BMI indicates obesity. Speaking with a healthcare provider about a structured plan for nutrition and physical activity is recommended.";
  return "Your BMI indicates a higher health risk. Please consult a doctor for personalised guidance — professional support can make a real difference.";
}

function healthyWeightRange(heightM) {
  const low  = Math.round(18.5 * heightM * heightM * 10) / 10;
  const high = Math.round(24.9 * heightM * heightM * 10) / 10;
  return `${low}–${high} kg`;
}

// ─── MCP server factory  (one per request — stateless mode) ────────────────
function createHealthServer() {
  const server = new McpServer({
    name:    "health-dashboard",
    version: "1.0.0",
  });

  // ── Resource: register the widget HTML bundle ────────────────────────────
  server.registerResource(
    "health-widget",
    "ui://widget/health.html",
    {
      description: "Health Dashboard UI widget displayed inside ChatGPT.",
    },
    async () => ({
      contents: [
        {
          uri:      "ui://widget/health.html",
          mimeType: "text/html+skybridge",   // required MIME for Apps SDK
          text:     WIDGET_HTML,
          _meta: {
            "openai/widgetPrefersBorder":   true,
            "openai/allowedDomains":        [BASE_URL],
          },
        },
      ],
    })
  );

  // ── Tool 1: calculate_bmi ────────────────────────────────────────────────
  server.registerTool(
    "calculate_bmi",
    {
      title:       "Calculate BMI",
      description:
        "Calculates the Body Mass Index (BMI) for a person given their weight " +
        "and height. Returns a visual health dashboard widget.",
      inputSchema: {
        weight_kg: z.number().positive().describe("Body weight in kilograms."),
        height_cm: z.number().positive().describe("Height in centimetres."),
        name:      z.string().optional().describe("Optional name or label for this record."),
      },
      _meta: {
        "openai/outputTemplate":            "ui://widget/health.html",
        "openai/toolInvocation/invoking":   "Calculating BMI…",
        "openai/toolInvocation/invoked":    "BMI calculated",
      },
    },
    async ({ weight_kg, height_cm, name }) => {
      const heightM = height_cm / 100;
      const bmi     = calcBMI(weight_kg, heightM);
      const category = bmiCategory(bmi);

      const record = {
        id:                  `bmi-${Date.now()}`,
        name:                name ?? "BMI Record",
        weight_kg,
        height_cm,
        bmi,
        category,
        advice:              bmiAdvice(bmi),
        healthy_weight_range: healthyWeightRange(heightM),
        timestamp:           new Date().toISOString(),
      };

      // Save to in-memory history
      bmiHistory = [record, ...bmiHistory].slice(0, 20); // keep last 20

      return {
        content: [
          {
            type: "text",
            text:
              `BMI for ${record.name}: **${bmi}** (${category}). ` +
              `Healthy weight range for this height: ${record.healthy_weight_range}. ` +
              record.advice,
          },
        ],
        structuredContent: record,  // drives the widget UI
      };
    }
  );

  // ── Tool 2: get_bmi_history ──────────────────────────────────────────────
  server.registerTool(
    "get_bmi_history",
    {
      title:       "BMI History",
      description: "Returns the list of previously calculated BMI records as a visual dashboard.",
      inputSchema: {
        limit: z
          .number()
          .int()
          .min(1)
          .max(20)
          .optional()
          .describe("Maximum number of records to return (default 10)."),
      },
      _meta: {
        "openai/outputTemplate":            "ui://widget/health.html",
        "openai/toolInvocation/invoking":   "Fetching BMI history…",
        "openai/toolInvocation/invoked":    "History loaded",
      },
    },
    async ({ limit = 10 }) => {
      const entries = bmiHistory.slice(0, limit);
      const summary =
        entries.length === 0
          ? "No BMI records found yet. Ask me to calculate a BMI first!"
          : `Showing ${entries.length} BMI record${entries.length > 1 ? "s" : ""}.`;

      return {
        content: [{ type: "text", text: summary }],
        structuredContent: { entries },  // drives the history list in widget
      };
    }
  );

  // ── Tool 3: clear_bmi_history ────────────────────────────────────────────
  server.registerTool(
    "clear_bmi_history",
    {
      title:       "Clear BMI History",
      description: "Clears all stored BMI records.",
      inputSchema: {},
      _meta: {
        "openai/toolInvocation/invoking": "Clearing history…",
        "openai/toolInvocation/invoked":  "History cleared",
      },
    },
    async () => {
      const count = bmiHistory.length;
      bmiHistory  = [];
      return {
        content: [{ type: "text", text: `Cleared ${count} BMI record(s).` }],
        structuredContent: { cleared: count },
      };
    }
  );

  return server;
}

// ─── CORS headers helper ────────────────────────────────────────────────────
function setCORSHeaders(res) {
  res.setHeader("Access-Control-Allow-Origin",  "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "content-type, mcp-session-id");
  res.setHeader("Access-Control-Expose-Headers","Mcp-Session-Id");
}

// ─── HTTP server ────────────────────────────────────────────────────────────
const httpServer = createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);

  // ── CORS preflight ────────────────────────────────────────────
  if (req.method === "OPTIONS") {
    setCORSHeaders(res);
    res.writeHead(204).end();
    return;
  }

  setCORSHeaders(res);

  // ── Health check ──────────────────────────────────────────────
  if (req.method === "GET" && url.pathname === "/") {
    res.writeHead(200, { "content-type": "application/json" }).end(
      JSON.stringify({
        status:  "ok",
        server:  "health-dashboard-mcp",
        mcp_url: `${BASE_URL}${MCP_PATH}`,
      })
    );
    return;
  }

  // ── Serve widget HTML directly (for browser preview / Claude) ─
  if (req.method === "GET" && url.pathname === "/widget") {
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" }).end(WIDGET_HTML);
    return;
  }

  // ── MCP endpoint  (POST | GET | DELETE) ───────────────────────
  const MCP_METHODS = new Set(["POST", "GET", "DELETE"]);
  if (url.pathname === MCP_PATH && req.method && MCP_METHODS.has(req.method)) {
    const server    = createHealthServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless — one server per request
      enableJsonResponse: true,
    });

    res.on("close", () => {
      transport.close();
      server.close();
    });

    try {
      await server.connect(transport);
      await transport.handleRequest(req, res);
    } catch (err) {
      console.error("[MCP] Error handling request:", err);
      if (!res.headersSent) {
        res.writeHead(500).end(JSON.stringify({ error: "Internal server error" }));
      }
    }
    return;
  }

  // ── 404 ───────────────────────────────────────────────────────
  res.writeHead(404, { "content-type": "text/plain" }).end("Not Found");
});

httpServer.listen(PORT, () => {
  console.log("─────────────────────────────────────────────");
  console.log("  Health Dashboard — MCP Server");
  console.log("─────────────────────────────────────────────");
  console.log(`  Server:    http://localhost:${PORT}`);
  console.log(`  MCP URL:   http://localhost:${PORT}${MCP_PATH}`);
  console.log(`  Widget:    http://localhost:${PORT}/widget`);
  console.log("");
  console.log("  ▸ To expose publicly via ngrok:");
  console.log(`    ngrok http ${PORT} --host-header=localhost:${PORT}`);
  console.log("    Then set BASE_URL=https://<your-id>.ngrok-free.app");
  console.log("");
  console.log("  ▸ Add to ChatGPT:");
  console.log("    Settings → Connectors → Create");
  console.log(`    URL: ${BASE_URL}${MCP_PATH}`);
  console.log("─────────────────────────────────────────────");
});
