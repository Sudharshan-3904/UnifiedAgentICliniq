import { Server } from "npm:@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "npm:@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from "npm:@modelcontextprotocol/sdk/types.js";
import { z } from "npm:zod";
import { makeFileTools } from "./file_tools.ts";

const fileTools = makeFileTools();

const server = new Server(
  {
    name: "deno-js-file-manager-refactored",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "read_file",
        description: "Read the content of a file",
        inputSchema: {
          type: "object",
          properties: {
            path: { type: "string" },
          },
          required: ["path"],
        },
      },
      {
        name: "create_file",
        description: "Create a file with content",
        inputSchema: {
          type: "object",
          properties: {
            path: { type: "string" },
            content: { type: "string" },
          },
          required: ["path", "content"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === "read_file") {
      const schema = z.object({ path: z.string() });
      const { path } = schema.parse(args);
      const content = await fileTools.readFile(path);
      return { content: [{ type: "text", text: content }] };
    }

    if (name === "create_file") {
      const schema = z.object({ path: z.string(), content: z.string() });
      const { path, content } = schema.parse(args);
      const result = await fileTools.createFile(path, content);
      return { content: [{ type: "text", text: result }] };
    }

    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${errorMessage}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
