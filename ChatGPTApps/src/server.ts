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
        ui: { url: `${publicUrl}/ui/bmi-widget` }
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
                        { type: "text", text: `BMI: ${result.bmi} (${result.status})` }
                    ],
                    structuredContent: result,
                    _meta: {
                        ui: { url: `${publicUrl}/ui/bmi-widget` }
                    }
                };

                console.log("RETURNING TO CHATGPT:", JSON.stringify(response, null, 2));

                return response;
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