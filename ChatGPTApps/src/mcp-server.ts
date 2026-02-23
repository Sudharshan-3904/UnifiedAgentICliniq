import express from "express";
import cors from "cors";
import { randomUUID } from "crypto";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const app = express();
app.use(cors());
app.use(express.json());

// Create MCP server
const server = new Server(
    {
        name: "bmi-calculator",
        version: "1.0.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// 1️⃣ Tell MCP what tools exist
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "calculate_bmi",
                description: "Calculate BMI using weight (kg) and height (meters)",
                inputSchema: {
                    type: "object",
                    properties: {
                        weight: { type: "number" },
                        height: { type: "number" },
                    },
                    required: ["weight", "height"],
                },
            },
        ],
    };
});

// 2️⃣ Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    console.log(`🛠️ Executing tool: ${request.params.name}`, request.params.arguments);
    if (request.params.name !== "calculate_bmi") {
        throw new Error("Unknown tool");
    }

    const { weight, height } = request.params.arguments as {
        weight: number;
        height: number;
    };

    if (height <= 0) {
        throw new Error("Height must be greater than 0");
    }

    const bmi = weight / (height * height);

    let category = "";
    if (bmi < 18.5) category = "Underweight";
    else if (bmi < 25) category = "Normal weight";
    else if (bmi < 30) category = "Overweight";
    else category = "Obese";

    return {
        content: [
            {
                type: "text",
                text: `Here are your BMI results:

• BMI Value: ${bmi.toFixed(2)}
• Category: ${category}`,
            },
        ],
    };
});

// HTTP transport
const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
});

app.post("/mcp", async (req, res) => {
    try {
        await transport.handleRequest(req, res, req.body);
    } catch (error) {
        console.error("❌ Error:", error);
        res.status(500).json({ error: String(error) });
    }
});

server.connect(transport);

app.listen(3000, () => {
    console.log("🚀 MCP Server running at http://localhost:3000/mcp");
});

