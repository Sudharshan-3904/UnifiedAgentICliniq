function renderBMI(data) {
    if (!data) return;

    const { bmi, weightKg, heightM, status } = data;

    document.getElementById("bmi-value").innerText = bmi;
    document.getElementById("bmi-status").innerText = status;

    document.getElementById("details").innerHTML = `
    <p><strong>Weight:</strong> ${weightKg} kg</p>
    <p><strong>Height:</strong> ${heightM} m</p>
  `;

    const bar = document.getElementById("bmi-bar");

    let percent = Math.min((bmi / 40) * 100, 100);
    bar.style.width = percent + "%";

    if (bmi < 18.5) bar.style.background = "#3498db";
    else if (bmi < 25) bar.style.background = "#2ecc71";
    else if (bmi < 30) bar.style.background = "#f1c40f";
    else bar.style.background = "#e74c3c";
}


// Modern MCP automatically injects this:
window.addEventListener("message", (event) => {
    if (event.data?.structuredContent) {
        renderBMI(event.data.structuredContent);
    }
});

// Also handle initial load
if (window.structuredContent) {
    renderBMI(window.structuredContent);
}