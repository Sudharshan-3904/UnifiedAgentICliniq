# Weather Agent — Developer Notes

### Purpose

-   Provide a compact reference for the WeatherAgent implementation, decisions, and helpful hints for extending/testing.

### Design overview

-   Graph nodes:
    -   `LocationNode`: validates latitude/longitude.
    -   `FetchWeatherNode`: calls Open-Meteo for hourly forecast + `current_weather`.
    -   `FetchAirQualityNode`: calls Open-Meteo Air Quality (with retries) and computes `air_quality_summary`.
    -   `LLMNode`: constructs a concise prompt from small extracted metrics and requests structured JSON from an LLM. If SDK not available, uses deterministic local fallback to produce structured JSON.
    -   `RespondNode`: normalizes structured output into final response.

### Prompting rules

-   Keep the prompt minimal: pass only concise metrics (temperature, relative humidity, precipitation values, pollutant readings).
-   Instruct the LLM to return JSON only. Schema is intentionally minimal so the model can reliably produce valid JSON:
    -   `answer`, `confidence`, `recommendations`, optional `air_quality`, optional `weather` (temperature/relative_humidity).

### Air-quality interpretation

-   `fetch_air_quality_summary` extracts latest numeric values for pollutants (pm2_5, pm10, ozone, nitrogen_dioxide, sulphur_dioxide, carbon_monoxide).
-   `interpret_air_quality` maps numeric values into coarse categories (Good / Moderate / Unhealthy for Sensitive Groups / Unhealthy / Very Unhealthy / Hazardous) and produces non-medical recommendations.

### Local fallback behavior

-   If `google-genai` is not installed, `LLMNode` uses a local deterministic generator:
    -   For AQ-focused queries the fallback returns a pollutants breakdown and AQ recommendations.
    -   For weather queries the fallback uses precipitation values to produce a simple precipitation answer or summarizes temperature/humidity.

### Error handling & retries

-   Air Quality requests may return 400 for some parameter combinations; code retries with a smaller hourly set and without timezone.
-   LLM responses are parsed for JSON; if parsing fails we attempt to locate the first JSON object substring.

### Testing tips

-   CLI quick test: `python main.py "Show me PM2.5 levels" 48.8566 2.3522 true`
-   Use `include_air_quality=true` to exercise AQ path.
-   To test structured LLM behavior locally without google-genai, run without SDK; the local fallback will return structured JSON.

### Extensibility notes

-   Add Ollama client: implement `call_ollama(prompt, ...)` and call it before the mock fallback.
-   Improve JSON reliability: add JSON schema and use a small repair routine (e.g., run the model again to fix malformed JSON or use regularized postprocessors).
-   Add caching (LRU or Redis) for Open-Meteo calls keyed by `lat,lon,params`.
