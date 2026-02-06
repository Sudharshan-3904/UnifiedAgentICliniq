/**
 * BMI MCP Client - Solid Protocol Implementation
 */

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

const SERVER_URL = window.location.origin;
const SSE_URL = `${SERVER_URL}/sse`;

let postbackUrl = null;
let mcpReady = false;
const pending = new Map();

/**
 * 1. Initialize MCP over SSE
 */
function init() {
    console.log("📡 Connecting to Health Advisor...");
    const es = new EventSource(SSE_URL);

    es.addEventListener("endpoint", async (e) => {
        postbackUrl = new URL(e.data, SERVER_URL).href;
        console.log("🔗 Discovery: Postback URL found.");
        await handshake();
    });

    es.addEventListener("message", (e) => {
        try {
            const res = JSON.parse(e.data);
            if (res.id && pending.has(res.id)) {
                const { resolve, reject } = pending.get(res.id);
                pending.delete(res.id);
                res.error ? reject(res.error) : resolve(res.result);
            }
        } catch (err) { console.debug("Ignored non-json message"); }
    });

    es.onerror = () => console.log("Waiting for server...");
}

/**
 * 2. Mandatory Protocol Handshake
 */
async function handshake() {
    try {
        console.log("🤝 Initializing Protocol...");
        const init = await call("initialize", {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "WebClient", version: "1.0" }
        });

        await notify("notifications/initialized");
        mcpReady = true;
        console.log("✅ Advisor Ready!");
    } catch (err) {
        console.error("Handshake failed:", err);
    }
}

/**
 * 3. JSON-RPC Helpers
 */
async function call(method, params = {}) {
    const id = Math.random().toString(36).substring(7);
    const p = { jsonrpc: "2.0", id, method, params };

    return new Promise(async (resolve, reject) => {
        pending.set(id, { resolve, reject });
        const r = await fetch(postbackUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(p)
        });
        if (!r.ok) {
            pending.delete(id);
            reject(new Error("Network Error"));
        }
    });
}

async function notify(method, params = {}) {
    await fetch(postbackUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: "2.0", method, params })
    });
}

/**
 * 4. UI logic
 */
async function onSend() {
    const text = userInput.value.trim();
    if (!text || !mcpReady) return;

    addMsg('user', text);
    userInput.value = '';
    const botMsg = addMsg('assistant', 'Thinking...');

    try {
        const w = text.match(/(\d+\.?\d*)\s*kg/i);
        const h = text.match(/(\d+\.?\d*)\s*(m|cm)/i);

        if (w && h) {
            let valW = parseFloat(w[1]);
            let valH = parseFloat(h[1]);
            if (h[2].toLowerCase() === 'cm') valH /= 100;

            const res = await call("tools/call", {
                name: "calculate_bmi",
                arguments: { weight: valW, height: valH }
            });
            botMsg.querySelector('.content').innerHTML = res.content[0].text;
        } else {
            botMsg.querySelector('.content').textContent = "Please provide weight (e.g. 70kg) and height (e.g. 1.75m).";
        }
    } catch (e) {
        botMsg.querySelector('.content').textContent = "Protocol Error: " + (e.message || "Failed to communicate.");
    }
}

function addMsg(role, text) {
    const d = document.createElement('div');
    d.className = `message ${role}`;
    d.innerHTML = `<div class="avatar ${role === 'assistant' ? 'bot' : ''}">${role[0].toUpperCase()}</div><div class="content">${text}</div>`;
    chatMessages.appendChild(d);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return d;
}

init();
sendBtn.addEventListener('click', onSend);
userInput.addEventListener('keypress', (e) => e.key === 'Enter' && onSend());
