import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("BMI Calculator")

TEMPLATE_URI = "ui://dashboard"

widgetHtml = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BMI Calculator</title>
<style>
:root {
  --bg-card: #ffffff;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --border: #e5e7eb;
  --accent: #3b82f6;
  --underweight: #3b82f6;
  --normal: #10b981;
  --overweight: #f59e0b;
  --obese: #ef4444;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-card: #1f2937;
    --text-primary: #f9fafb;
    --text-secondary: #d1d5db;
    --border: #374151;
    --accent: #60a5fa;
  }
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: transparent;
  color: var(--text-primary);
  font-size: 16px;
  line-height: 1.5;
}

.card {
  background: var(--bg-card);
  border-radius: 20px;
  padding: 24px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  margin: 0 auto;
}

.input-group {
  margin-bottom: 20px;
}

.label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.number-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 16px;
}

.select-input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
}

.slider {
  width: 100%;
  -webkit-appearance: none;
  height: 6px;
  border-radius: 3px;
  background: var(--border);
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  transition: background 0.2s;
}

.slider::-webkit-slider-thumb:hover {
  background: #2563eb;
}

.calc-btn {
  width: 100%;
  background: var(--accent);
  color: white;
  border: none;
  padding: 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 24px;
}

.calc-btn:hover {
  background: #2563eb;
  transform: scale(1.02);
}

.results {
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.5s ease;
}

.results.show {
  opacity: 1;
  transform: translateY(0);
}

.bmi-display {
  text-align: center;
  margin-bottom: 16px;
}

.bmi-value {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 4px;
}

.category-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.progress-container {
  margin: 20px 0;
}

.progress-bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: var(--normal);
  transition: width 0.5s ease, background 0.5s ease;
}

.marker {
  position: absolute;
  top: -12px;
  width: 2px;
  height: 12px;
  background: var(--text-secondary);
}

.marker-label {
  position: absolute;
  top: -28px;
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.advice {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin: 16px 0;
  font-size: 14px;
  color: var(--text-primary);
}

.external-btns {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.external-btn {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.external-btn:hover {
  background: var(--border);
}

@media (max-width: 480px) {
  .card {
    padding: 16px;
    max-width: 320px;
  }
  .bmi-value {
    font-size: 36px;
  }
}
</style>
</head>
<body>
<div class="card">
  <h1 style="text-align: center; margin-bottom: 24px; font-size: 24px; font-weight: bold;">BMI Results</h1>
  
  <div id="results" class="results show">
    <div class="bmi-display">
      <div class="bmi-value" id="bmi">--</div>
      <div class="category-badge" id="category-badge">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
        <span id="status">--</span>
      </div>
    </div>
    
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" id="progress-fill"></div>
        <div class="marker" style="left: 18.5%"></div>
        <div class="marker" style="left: 24.9%"></div>
        <div class="marker" style="left: 29.9%"></div>
        <div class="marker-label" style="left: 5%">Under</div>
        <div class="marker-label" style="left: 21%">Normal</div>
        <div class="marker-label" style="left: 27%">Over</div>
        <div class="marker-label" style="left: 32%">Obese</div>
      </div>
    </div>
    
    <div class="advice" id="advice">Enter your details and calculate your BMI.</div>
    
    <div class="external-btns">
      <button class="external-btn" onclick="openExternal('bmi_info')">BMI Info</button>
      <button class="external-btn" onclick="openExternal('wiki')">Wiki</button>
    </div>
  </div>
</div>

<script>
const bmiEl = document.getElementById('bmi');
const statusEl = document.getElementById('status');
const categoryBadge = document.getElementById('category-badge');
const progressFill = document.getElementById('progress-fill');
const adviceEl = document.getElementById('advice');

function openExternal(app) {
  const urls = {
    bmi_info: 'https://www.cdc.gov/healthyweight/assessing/bmi/index.html',
    wiki: 'https://en.wikipedia.org/wiki/Body_mass_index'
  };
  window.open(urls[app], '_blank');
}

function render(data) {
  if (!data) return;
  const output = data.structuredContent || data;
  if (!output.bmi) return;
  
  bmiEl.textContent = output.bmi;
  statusEl.textContent = output.status;
  adviceEl.textContent = output.advice || (output.status === 'Normal weight' ? 'Great job! Maintain your healthy lifestyle.' : 'Consult a doctor for personalized advice.');
  
  let color;
  if (output.status === 'Underweight') color = 'var(--underweight)';
  else if (output.status === 'Normal weight') color = 'var(--normal)';
  else if (output.status === 'Overweight') color = 'var(--overweight)';
  else color = 'var(--obese)';
  
  bmiEl.style.color = color;
  categoryBadge.style.background = color + '20';
  categoryBadge.style.color = color;
  
  const fillPercent = Math.min((output.bmi / 40) * 100, 100);
  progressFill.style.width = fillPercent + '%';
  progressFill.style.background = color;
}

render(window.openai?.toolOutput);

window.addEventListener('message', (event) => {
  if (event.data?.type === 'openai:set_globals') {
      render(event.data.payload?.globals?.toolOutput);
  }
});
</script>
</body>
</html>
""".strip()

@mcp.resource(TEMPLATE_URI, mime_type="text/html")
def bmi_widget() -> str:
    return widgetHtml

@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> dict:
    """Calculate BMI and provide health advice."""
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category, advice = "Underweight", "Consider consulting a healthcare provider."
    elif 18.5 <= bmi < 24.9:
        category, advice = "Normal weight", "Great job! Maintain your healthy lifestyle."
    elif 25 <= bmi < 29.9:
        category, advice = "Overweight", "You might consider a more active lifestyle."
    else:
        category, advice = "Obese", "It's highly recommended to consult a doctor."
    
    return {
        "content": [{"type": "text", "text": f"BMI: {bmi} ({category}). {advice}"}],
        "structuredContent": {
            "bmi": bmi,
            "status": category,
            "advice": advice,
            "heightM": height_m,
            "weightKg": weight_kg
        },
        "_meta": {
            "ui": {"resourceUri": TEMPLATE_URI},
            "openai/outputTemplate": TEMPLATE_URI
        }
    }

if __name__ == "__main__":
    mcp.run(transport='sse')
