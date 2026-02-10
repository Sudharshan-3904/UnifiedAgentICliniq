/**
 * Sujit BMI - MCP Client Implementation
 */

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusBadge = document.getElementById('mcp-status');
const protocolLogs = document.getElementById('protocol-logs');

const SERVER_URL = window.location.origin;
const SSE_URL = `${SERVER_URL}/sse`;

let postbackUrl = null;
let mcpReady = false;
const pending = new Map();

/**
 * Log protocol events to the sidebar
 */
function log(msg) {
    const p = document.createElement('p');
    p.textContent = `> ${msg}`;
    protocolLogs.appendChild(p);
    protocolLogs.scrollTop = protocolLogs.scrollHeight;
    console.log(`[MCP] ${msg}`);
}

/**
 * 1. Initialize MCP over SSE
 */
function init() {
    log("Connecting to Health Advisor...");
    const es = new EventSource(SSE_URL);

    es.onerror = (err) => {
        log("Connection error. Retrying...");
        statusBadge.classList.remove('connected');
    };

    // The SDK sends the endpoint URL via an 'endpoint' event
    es.addEventListener("endpoint", async (e) => {
        postbackUrl = new URL(e.data, SERVER_URL).href;
        log("Discovery successful.");
        await handshake();
    });

    // Handle generic messages
    es.addEventListener("message", (e) => {
        try {
            const res = JSON.parse(e.data);
            if (res.id && pending.has(res.id)) {
                const { resolve, reject } = pending.get(res.id);
                pending.delete(res.id);
                if (res.error) {
                    reject(res.error);
                } else {
                    resolve(res.result);
                }
            }
        } catch (err) {
            // Ignore non-json or heartbeats
        }
    });
}

/**
 * 2. Mandated Handshake
 */
async function handshake() {
    try {
        log("Starting Handshake...");
        const result = await call("initialize", {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "Sujit-BMI-Web", version: "2.0" }
        });

        await notify("notifications/initialized");
        mcpReady = true;
        statusBadge.classList.add('connected');
        statusBadge.querySelector('.status-text').textContent = "Connected";
        log("Handshake Complete.");
    } catch (err) {
        log(`Handshake failed: ${err.message}`);
    }
}

/**
 * 3. Messaging Helpers
 */
async function call(method, params = {}) {
    const id = Math.random().toString(36).substring(7);
    const payload = { jsonrpc: "2.0", id, method, params };

    return new Promise(async (resolve, reject) => {
        pending.set(id, { resolve, reject });

        try {
            const res = await fetch(postbackUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                pending.delete(id);
                throw new Error(`HTTP ${res.status}`);
            }
        } catch (err) {
            pending.delete(id);
            reject(err);
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
 * 4. UI Actions
 */
async function handleSubmission() {
    const text = userInput.value.trim();
    if (!text || !mcpReady) return;

    addMessage('user', text);
    userInput.value = '';
    const botMsg = addMessage('assistant', '<div class="typing-indicator"><span></span><span></span><span></span></div>');

    try {
        // Regex to extract height and weight
        const weightMatch = text.match(/(\d+\.?\d*)\s*kg/i);
        const heightMatch = text.match(/(\d+\.?\d*)\s*(m|cm)/i);

        if (weightMatch && heightMatch) {
            let weight = parseFloat(weightMatch[1]);
            let height = parseFloat(heightMatch[1]);
            if (heightMatch[2].toLowerCase() === 'cm') height /= 100;

            const res = await call("tools/call", {
                name: "calculate_bmi",
                arguments: { weight, height }
            });

            botMsg.querySelector('.content').innerHTML = res.content[0].text;
            // Re-run lucide if any icons are present in the response (though unlikely for BMI)
            if (window.lucide) lucide.createIcons();
        } else {
            botMsg.querySelector('.content').textContent = "I need both your height (e.g. 1.75m) and weight (e.g. 70kg) to calculate your BMI.";
        }
    } catch (err) {
        botMsg.querySelector('.content').textContent = `Protocol Error: ${err.message || 'Check logs'}`;
    }
}

function addMessage(role, html) {
    const div = document.createElement('div');
    div.className = `message ${role} animate-in`;

    const avatarIcon = role === 'assistant' ? 'sparkles' : 'user';
    div.innerHTML = `
        <div class="avatar"><i data-lucide="${avatarIcon}"></i></div>
        <div class="content">${html}</div>
    `;

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (window.lucide) lucide.createIcons();
    return div;
}

// Start
init();

sendBtn.addEventListener('click', handleSubmission);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSubmission();
});
