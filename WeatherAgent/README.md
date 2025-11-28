# LangGraph Weather Agent

Lightweight Weather & Air-Quality assistant that fetches Open-Meteo forecast and air-quality data, enriches it with simple interpretations, and synthesizes user-facing answers via an LLM (Google GenAI preferred). The service exposes a FastAPI endpoint and includes a fallback local responder when a remote LLM SDK is not available.

## Key files

-   `main.py`: application entry — builds the graph of nodes and runs FastAPI/CLI.
-   `requirements.txt`: Python dependencies (install before running).
-   `NOTES.md`: developer notes and design decisions.

## Execution Flow (high-level)

1. Receive request (CLI or POST `/agent`) with `query`, `lat`, `lon`, and optional `include_air_quality`.
2. `LocationNode`: validate and normalize `lat`/`lon`.
3. `FetchWeatherNode`: call Open-Meteo for forecast + current weather; store `weather_raw` and `current_weather`.
4. `FetchAirQualityNode` (optional): call Open-Meteo Air Quality, compute `air_quality_summary`, and interpret pollutant categories and recommendations.
5. `LLMNode`: build a concise prompt (temperature, humidity, precipitation, pollutant readings) and call the configured LLM. Preferred path: `google-genai` SDK. If SDK missing, a deterministic local structured fallback produces a JSON response.
6. `RespondNode`: prefer structured JSON from the LLM (or local fallback), attach lightweight metadata and return to client.

## API

-   POST endpoint -> /agent
    -   Request JSON: `{"query": string, "lat": float, "lon": float, "include_air_quality": bool (optional) }`
    -   Response JSON: structured result tailored to the user's query. When available the response includes `answer`, `confidence`, `recommendations`, optional `air_quality` and a small `weather` snapshot.

Quick start

1. Create a virtual environment and install dependencies:

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Configure env vars (optional):

```pwsh
setx GEMINI_MODEL "gemini-2.5-flash"
# If using google-genai SDK, set GEMINI_API_KEY appropriately per SDK docs
```

3. Run as CLI (quick test):

```pwsh
python main.py "Show me PM2.5 and PM10" 48.8566 2.3522 true
```

4. Run as server:

```pwsh
uvicorn main:app --reload
# then POST to http://127.0.0.1:8000/agent
`{"query": string, "lat": float, "lon": float, "include_air_quality": bool (optional) }`

                                                [OR]

curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"query":"Will it rain this afternoon?","lat":40.7128,"lon":-74.0060,"include_air_quality":true}'
```

Behavioural notes

-   Preferred LLM: `google-genai` SDK. If unavailable the app produces a deterministic local structured response using the fetched data (useful for testing and reliability).
-   Prompts instruct the LLM to return strict JSON only. The server attempts to extract JSON from model output; if that fails it falls back to textual response embedding.
-   Air-quality interpretation is intentionally non-medical — it produces conservative categories and general precautions only.
