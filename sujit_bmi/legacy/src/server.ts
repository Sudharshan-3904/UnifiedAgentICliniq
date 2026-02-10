import express from "express";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { calculateBMICore, renderWidget } from "./logic.js";
import path from "path";
import { fileURLToPath } from "url";
import cors from "cors";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = 8000;

app.use(cors());
app.use(express.json());

// Initialize MCP Server
const server = new Server(
    {
        name: "BMI Advisor MCP",
        version: "1.0.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// Define Tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "calculate_bmi",
                description: "Calculate BMI and return a health widget.",
                inputSchema: {
                    type: "object",
                    properties: {
                        height: { type: "number", description: "Height in meters" },
                        weight: { type: "number", description: "Weight in kilograms" },
                    },
                    required: ["height", "weight"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name === "calculate_bmi") {
        const { height, weight } = request.params.arguments as { height: number; weight: number };
        try {
            const result = calculateBMICore(height, weight);
            const html = renderWidget(result);
            return {
                content: [{ type: "text", text: html }],
            };
        } catch (error: any) {
            return {
                content: [{ type: "text", text: `<div style='color:red;'>Error: ${error.message}</div>` }],
                isError: true,
            };
        }
    }
    throw new Error("Tool not found");
});

// SSE Transport Handling
let activeTransport: SSEServerTransport | null = null;

app.get("/sse", async (req, res) => {
    console.log("[*] New SSE connection established");
    activeTransport = new SSEServerTransport("/message", res);
    await server.connect(activeTransport);

    res.on("close", () => {
        console.log("[*] SSE connection closed");
    });
});

app.post("/message", async (req, res) => {
    console.log("[*] Received message from client");
    if (activeTransport) {
        await activeTransport.handlePostMessage(req, res);
    } else {
        res.status(400).send("No active transport");
    }
});

// Serve Frontend
const publicPath = path.join(__dirname, "../public");
app.use(express.static(publicPath));

app.listen(port, () => {
    console.log(`[*] Starting MCP Server on http://127.0.0.1:${port}`);
    console.log(`[*] Serving frontend from ${publicPath}`);
});
