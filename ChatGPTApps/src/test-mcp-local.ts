import fetch from "node-fetch";

async function testMCP() {
    console.log("🔍 Testing MCP server directly...\n");

    const response = await fetch("http://localhost:3000/mcp", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            id: 1,
            method: "tools/call",
            params: {
                name: "calculate_bmi",
                arguments: {
                    weight: 75,
                    height: 1.8
                }
            }
        })
    });

    const text = await response.text();
    console.log("Raw response:\n", text);

    let data;
    try {
        // Try parsing as plain JSON first
        data = JSON.parse(text);
    } catch (e) {
        // If it fails, try to extract from SSE format (line starts with 'data: ')
        const lines = text.split('\n');
        const dataLine = lines.find(line => line.startsWith('data: '));
        if (dataLine) {
            data = JSON.parse(dataLine.replace('data: ', '').trim());
        } else {
            console.error("Failed to parse response. Raw text:", text);
            throw new Error("Could not parse response as JSON or SSE data");
        }
    }


    console.log("\nParsed JSON:\n", JSON.stringify(data, null, 2));

}

testMCP();