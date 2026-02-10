/**
 * MCP Client Implementation for SSE
 */

export interface MCPResponse {
    jsonrpc: "2.0";
    id?: string;
    result?: any;
    error?: any;
}

export interface MCPNotification {
    jsonrpc: "2.0";
    method: string;
    params?: any;
}

export class MCPClient {
    private es: EventSource | null = null;
    private postbackUrl: string | null = null;
    private pending = new Map<string, { resolve: (val: any) => void; reject: (err: any) => void }>();
    private onReadyCallback: (() => void) | null = null;

    public isReady = false;

    private sseUrl: string;
    constructor(sseUrl: string) {
        this.sseUrl = sseUrl;
    }

    connect() {
        return new Promise<void>((resolve, reject) => {
            this.es = new EventSource(this.sseUrl);

            this.es.onerror = (err) => {
                console.error("SSE Connection error:", err);
                reject(err);
            };

            this.es.addEventListener("endpoint", async (e: any) => {
                this.postbackUrl = new URL(e.data, window.location.origin).href;
                console.log("Discovery successful. Postback URL:", this.postbackUrl);

                try {
                    await this.handshake();
                    this.isReady = true;
                    if (this.onReadyCallback) this.onReadyCallback();
                    resolve();
                } catch (err) {
                    reject(err);
                }
            });

            this.es.addEventListener("message", (e: any) => {
                try {
                    const res: MCPResponse = JSON.parse(e.data);
                    if (res.id && this.pending.has(res.id)) {
                        const { resolve, reject } = this.pending.get(res.id)!;
                        this.pending.delete(res.id);
                        if (res.error) {
                            reject(res.error);
                        } else {
                            resolve(res.result);
                        }
                    }
                } catch (err) {
                    // Ignore heartbeats or non-JSON
                }
            });
        });
    }

    onReady(cb: () => void) {
        this.onReadyCallback = cb;
        if (this.isReady) cb();
    }

    private async handshake() {
        console.log("Starting Handshake...");
        await this.call("initialize", {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "Sujit-BMI-TS-Web", version: "3.0" }
        });

        await this.notify("notifications/initialized");
        console.log("Handshake Complete.");
    }

    async call(method: string, params: any = {}) {
        const id = Math.random().toString(36).substring(7);
        const payload = { jsonrpc: "2.0", id, method, params };

        if (!this.postbackUrl) throw new Error("No postback URL");

        return new Promise(async (resolve, reject) => {
            this.pending.set(id, { resolve, reject });

            try {
                const res = await fetch(this.postbackUrl!, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    this.pending.delete(id);
                    throw new Error(`HTTP ${res.status}`);
                }
            } catch (err) {
                this.pending.delete(id);
                reject(err);
            }
        });
    }

    async notify(method: string, params: any = {}) {
        if (!this.postbackUrl) return;
        await fetch(this.postbackUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: "2.0", method, params })
        });
    }

    async callTool(name: string, args: any) {
        const res: any = await this.call("tools/call", {
            name,
            arguments: args
        });
        return res;
    }
}
