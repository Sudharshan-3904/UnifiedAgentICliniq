/**
 * BMI ChatGPT UI Logic
 * Implements the MCP Apps bridge communication protocol.
 */

const UI = {
  loading: document.getElementById("loading-view"),
  loadingText: document.querySelector("#loading-view p"),
  result: document.getElementById("result-view"),
  bmi: document.getElementById("bmi-display"),
  category: document.getElementById("category-display"),
  advice: document.getElementById("advice-display"),
  input: document.getElementById("user-input"),
  btn: document.getElementById("send-btn"),
};

/**
 * Local AI Interaction
 */
UI.btn.addEventListener("click", () => sendToLocalAI());
UI.input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendToLocalAI();
});

async function sendToLocalAI() {
  const prompt = UI.input.value.trim();
  if (!prompt) return;

  // UI Feedback
  UI.result.classList.add("hidden");
  UI.loading.classList.remove("hidden");
  UI.loading.style.opacity = "1";
  UI.input.value = "";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const result = await response.json();
    if (result && result.bmi) {
      updateUI(result);
    } else {
      UI.loadingText.textContent = "AI didn't provide a BMI result. Try again.";
    }
  } catch (err) {
    console.error("Local AI Error:", err);
    UI.loadingText.textContent = "Error connecting to backend.";
  }
}

/**
 * Handle incoming messages from the ChatGPT host (window.parent)
 */
window.addEventListener(
  "message",
  (event) => {
    // SECURITY: In production, you should verify event.origin if known
    // For local testing, we allow messages from the same window/origin
    const message = event.data;

    // Check for JSON-RPC 2.0 compliance
    if (!message || message.jsonrpc !== "2.0") return;

    console.log("📬 Received MCP Message:", message.method, message.params);

    switch (message.method) {
      case "ui/notifications/tool-input":
        // ChatGPT is currently running the tool
        UI.loadingText.textContent = "Calculating your health metrics...";
        break;

      case "ui/notifications/tool-result":
        // ChatGPT has received the tool output
        const data = message.params?.structuredContent;
        if (data) {
          updateUI(data);
        }
        break;

      case "ui/initialize":
        // Optional: Host is ready
        console.log("🚀 MCP Bridge Initialized");
        break;
    }
  },
  { passive: true },
);

/**
 * Update the DOM with the received data
 */
function updateUI(data) {
  if (!data.bmi) return;

  // Hide loading with a smooth transition
  UI.loading.style.opacity = "0";
  setTimeout(() => {
    UI.loading.classList.add("hidden");
    UI.result.classList.remove("hidden");
    UI.result.classList.add("fade-in");

    // Populate data
    UI.bmi.textContent = data.bmi;
    UI.category.textContent = data.category;
    UI.advice.textContent = data.advice;

    updateCategoryColor(data.category);
  }, 300);
}

function updateCategoryColor(category) {
  const badge = document.querySelector(".bmi-badge");
  badge.style.background =
    "conic-gradient(from 0deg, var(--primary) 0%, #c084fc 100%)"; // Reset

  if (category.includes("Obese")) {
    badge.style.boxShadow = "0 0 30px rgba(239, 68, 68, 0.4)";
  } else if (category.includes("Overweight")) {
    badge.style.boxShadow = "0 0 30px rgba(245, 158, 11, 0.4)";
  } else if (category.includes("Normal")) {
    badge.style.boxShadow = "0 0 30px rgba(34, 197, 94, 0.4)";
  } else if (category.includes("Underweight")) {
    badge.style.boxShadow = "0 0 30px rgba(59, 130, 246, 0.4)";
  }
}

// Initial check for debugging/mocking
console.log("BMI UI Initialized. Awaiting tool-result notification...");
