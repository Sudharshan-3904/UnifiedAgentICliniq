#!/usr/bin/env -S deno run --allow-read --allow-write --allow-run

/**
 * MCP Server for JavaScript Script Management with Deno
 * Provides tools for creating, reading, and executing JavaScript files
 */

import { Server } from "npm:@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "npm:@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "npm:@modelcontextprotocol/sdk/types.js";
import {
  join,
  resolve,
  dirname,
} from "https://deno.land/std@0.208.0/path/mod.ts";
import { existsSync } from "https://deno.land/std@0.208.0/fs/mod.ts";

// Configuration
const SCRIPTS_DIR = Deno.env.get("SCRIPTS_DIR") || "./scripts";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTENSIONS = [".js", ".ts"];

// Error types
class ScriptError extends Error {
  constructor(message: string, public code: string) {
    super(message);
    this.name = "ScriptError";
  }
}

// Logger utility
class Logger {
  private static log(level: string, message: string, data?: unknown) {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      ...(data && { data }),
    };
    console.error(JSON.stringify(logEntry));
  }

  static info(message: string, data?: unknown) {
    this.log("INFO", message, data);
  }

  static error(message: string, error?: unknown) {
    this.log("ERROR", message, {
      error:
        error instanceof Error
          ? {
              message: error.message,
              stack: error.stack,
              name: error.name,
            }
          : error,
    });
  }

  static warn(message: string, data?: unknown) {
    this.log("WARN", message, data);
  }
}

// Script Manager Class
class ScriptManager {
  private scriptsDir: string;

  constructor(scriptsDir: string) {
    this.scriptsDir = resolve(scriptsDir);
    this.ensureScriptsDirectory();
  }

  private ensureScriptsDirectory(): void {
    try {
      if (!existsSync(this.scriptsDir)) {
        Deno.mkdirSync(this.scriptsDir, { recursive: true });
        Logger.info("Created scripts directory", { path: this.scriptsDir });
      }
    } catch (error) {
      Logger.error("Failed to create scripts directory", error);
      throw new ScriptError(
        "Failed to initialize scripts directory",
        "INIT_ERROR"
      );
    }
  }

  private validateFilename(filename: string): void {
    if (
      !filename ||
      filename.includes("..") ||
      filename.includes("/") ||
      filename.includes("\\")
    ) {
      throw new ScriptError("Invalid filename", "INVALID_FILENAME");
    }

    const ext = filename.substring(filename.lastIndexOf("."));
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      throw new ScriptError(
        `File extension must be one of: ${ALLOWED_EXTENSIONS.join(", ")}`,
        "INVALID_EXTENSION"
      );
    }
  }

  private getScriptPath(filename: string): string {
    this.validateFilename(filename);
    return join(this.scriptsDir, filename);
  }

  async createScript(
    filename: string,
    content: string
  ): Promise<{ success: boolean; path: string; message: string }> {
    try {
      const scriptPath = this.getScriptPath(filename);

      if (existsSync(scriptPath)) {
        throw new ScriptError("File already exists", "FILE_EXISTS");
      }

      if (content.length > MAX_FILE_SIZE) {
        throw new ScriptError(
          `File size exceeds maximum of ${MAX_FILE_SIZE} bytes`,
          "FILE_TOO_LARGE"
        );
      }

      await Deno.writeTextFile(scriptPath, content);
      Logger.info("Script created successfully", {
        filename,
        path: scriptPath,
      });

      return {
        success: true,
        path: scriptPath,
        message: `Script '${filename}' created successfully`,
      };
    } catch (error) {
      Logger.error("Failed to create script", error);
      if (error instanceof ScriptError) throw error;
      throw new ScriptError("Failed to create script file", "CREATE_ERROR");
    }
  }

  async readScript(
    filename: string
  ): Promise<{ success: boolean; content: string; path: string }> {
    try {
      const scriptPath = this.getScriptPath(filename);

      if (!existsSync(scriptPath)) {
        throw new ScriptError("File not found", "FILE_NOT_FOUND");
      }

      const stat = await Deno.stat(scriptPath);
      if (stat.size > MAX_FILE_SIZE) {
        throw new ScriptError(
          `File size exceeds maximum of ${MAX_FILE_SIZE} bytes`,
          "FILE_TOO_LARGE"
        );
      }

      const content = await Deno.readTextFile(scriptPath);
      Logger.info("Script read successfully", { filename, path: scriptPath });

      return {
        success: true,
        content,
        path: scriptPath,
      };
    } catch (error) {
      Logger.error("Failed to read script", error);
      if (error instanceof ScriptError) throw error;
      throw new ScriptError("Failed to read script file", "READ_ERROR");
    }
  }

  async executeScript(
    filename: string,
    args: string[] = [],
    timeout: number = 30000
  ): Promise<{
    success: boolean;
    stdout: string;
    stderr: string;
    exitCode: number;
  }> {
    try {
      const scriptPath = this.getScriptPath(filename);

      if (!existsSync(scriptPath)) {
        throw new ScriptError("File not found", "FILE_NOT_FOUND");
      }

      Logger.info("Executing script", { filename, args, timeout });

      const command = new Deno.Command(
        "C:/Users/jaswi/.deno/bin/deno.exe", // <--- replace with your actual Deno path
        {
          args: [
            "run",
            "--allow-read",
            "--allow-write",
            "--allow-env",
            "--allow-run",
            "--allow-net",
            scriptPath,
            ...args,
          ],
          stdout: "piped",
          stderr: "piped",
        }
      );

      const process = command.spawn();

      // Timeout handling
      const timeoutId = setTimeout(() => {
        process.kill("SIGTERM");
        Logger.warn("Script execution timed out", { filename, timeout });
      }, timeout);

      const { code, stdout, stderr } = await process.output();
      clearTimeout(timeoutId);

      const stdoutText = new TextDecoder().decode(stdout);
      const stderrText = new TextDecoder().decode(stderr);

      Logger.info("Script execution completed", {
        filename,
        exitCode: code,
        stdoutLength: stdoutText.length,
        stderrLength: stderrText.length,
      });

      return {
        success: code === 0,
        stdout: stdoutText,
        stderr: stderrText,
        exitCode: code,
      };
    } catch (error) {
      Logger.error("Failed to execute script", error);
      if (error instanceof ScriptError) throw error;
      throw new ScriptError("Failed to execute script", "EXECUTE_ERROR");
    }
  }

  async listScripts(): Promise<{
    success: boolean;
    scripts: Array<{ name: string; size: number; modified: Date }>;
  }> {
    try {
      const scripts: Array<{ name: string; size: number; modified: Date }> = [];

      for await (const entry of Deno.readDir(this.scriptsDir)) {
        if (entry.isFile) {
          const ext = entry.name.substring(entry.name.lastIndexOf("."));
          if (ALLOWED_EXTENSIONS.includes(ext)) {
            const stat = await Deno.stat(join(this.scriptsDir, entry.name));
            scripts.push({
              name: entry.name,
              size: stat.size,
              modified: stat.mtime || new Date(),
            });
          }
        }
      }

      Logger.info("Listed scripts", { count: scripts.length });
      return { success: true, scripts };
    } catch (error) {
      Logger.error("Failed to list scripts", error);
      throw new ScriptError("Failed to list scripts", "LIST_ERROR");
    }
  }

  async deleteScript(
    filename: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      const scriptPath = this.getScriptPath(filename);

      if (!existsSync(scriptPath)) {
        throw new ScriptError("File not found", "FILE_NOT_FOUND");
      }

      await Deno.remove(scriptPath);
      Logger.info("Script deleted successfully", {
        filename,
        path: scriptPath,
      });

      return {
        success: true,
        message: `Script '${filename}' deleted successfully`,
      };
    } catch (error) {
      Logger.error("Failed to delete script", error);
      if (error instanceof ScriptError) throw error;
      throw new ScriptError("Failed to delete script file", "DELETE_ERROR");
    }
  }
}

// MCP Server Setup
class ScriptMCPServer {
  private server: Server;
  private scriptManager: ScriptManager;

  constructor() {
    this.server = new Server(
      {
        name: "deno-script-manager",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.scriptManager = new ScriptManager(SCRIPTS_DIR);
    this.setupHandlers();
    Logger.info("MCP Server initialized", { scriptsDir: SCRIPTS_DIR });
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "create_script",
          description: "Create a new JavaScript/TypeScript file",
          inputSchema: {
            type: "object",
            properties: {
              filename: {
                type: "string",
                description: "Name of the script file (must end in .js or .ts)",
              },
              content: {
                type: "string",
                description: "Content of the script file",
              },
            },
            required: ["filename", "content"],
          },
        },
        {
          name: "read_script",
          description: "Read the contents of a script file",
          inputSchema: {
            type: "object",
            properties: {
              filename: {
                type: "string",
                description: "Name of the script file to read",
              },
            },
            required: ["filename"],
          },
        },
        {
          name: "execute_script",
          description: "Execute a script file with Deno",
          inputSchema: {
            type: "object",
            properties: {
              filename: {
                type: "string",
                description: "Name of the script file to execute",
              },
              args: {
                type: "array",
                items: { type: "string" },
                description: "Command-line arguments to pass to the script",
                default: [],
              },
              timeout: {
                type: "number",
                description:
                  "Execution timeout in milliseconds (default: 30000)",
                default: 30000,
              },
            },
            required: ["filename"],
          },
        },
        {
          name: "list_scripts",
          description: "List all available script files",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "delete_script",
          description: "Delete a script file",
          inputSchema: {
            type: "object",
            properties: {
              filename: {
                type: "string",
                description: "Name of the script file to delete",
              },
            },
            required: ["filename"],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;

        switch (name) {
          case "create_script": {
            const result = await this.scriptManager.createScript(
              args.filename as string,
              args.content as string
            );
            return {
              content: [
                { type: "text", text: JSON.stringify(result, null, 2) },
              ],
            };
          }

          case "read_script": {
            const result = await this.scriptManager.readScript(
              args.filename as string
            );
            return {
              content: [
                { type: "text", text: JSON.stringify(result, null, 2) },
              ],
            };
          }

          case "execute_script": {
            const result = await this.scriptManager.executeScript(
              args.filename as string,
              (args.args as string[]) || [],
              (args.timeout as number) || 30000
            );
            return {
              content: [
                { type: "text", text: JSON.stringify(result, null, 2) },
              ],
            };
          }

          case "list_scripts": {
            const result = await this.scriptManager.listScripts();
            return {
              content: [
                { type: "text", text: JSON.stringify(result, null, 2) },
              ],
            };
          }

          case "delete_script": {
            const result = await this.scriptManager.deleteScript(
              args.filename as string
            );
            return {
              content: [
                { type: "text", text: JSON.stringify(result, null, 2) },
              ],
            };
          }

          default:
            throw new ScriptError(`Unknown tool: ${name}`, "UNKNOWN_TOOL");
        }
      } catch (error) {
        Logger.error("Tool execution failed", error);

        const errorResponse = {
          success: false,
          error: {
            message: error instanceof Error ? error.message : "Unknown error",
            code: error instanceof ScriptError ? error.code : "INTERNAL_ERROR",
          },
        };

        return {
          content: [
            { type: "text", text: JSON.stringify(errorResponse, null, 2) },
          ],
          isError: true,
        };
      }
    });
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    Logger.info("MCP Server running on stdio");
  }
}

// Main execution
if (import.meta.main) {
  const server = new ScriptMCPServer();
  server.run().catch((error) => {
    Logger.error("Fatal server error", error);
    Deno.exit(1);
  });
}
