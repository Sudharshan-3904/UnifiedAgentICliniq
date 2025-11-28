import os
import sys
import json
import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# FastAPI
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import requests

# LangGraph (optional)
try:
    from langgraph import Graph, Node
    LANGGRAPH_AVAILABLE = True
except Exception:
    Graph = None
    Node = object
    LANGGRAPH_AVAILABLE = False

LOG = logging.getLogger("weather_agent")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

# Gemini config
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# Note: REST fallback removed. The preferred integration is the google-genai Python SDK.
# Prefer google-genai client if installed
TRY_GOOGLE_GENAI = True
try:
    import google.genai as genai  # package name `google-genai` -> import google.genai
    HAS_GOOGLE_GENAI = True
except Exception:
    HAS_GOOGLE_GENAI = False

# Open-Meteo base
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
# added: Open-Meteo Air Quality endpoint
OPEN_AIR_BASE = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Set defaults
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

# -------------------------
# Helper: call Open-Meteo
# -------------------------
def fetch_open_meteo(lat: float, lon: float, hourly_vars: Optional[list] = None, timezone: str = "auto") -> Dict[str, Any]:
    """
    Fetch forecast from Open-Meteo.
    By default we request: temperature_2m, precipitation, windspeed_10m
    """
    if hourly_vars is None:
        hourly_vars = ["temperature_2m", "precipitation", "windspeed_10m", "relativehumidity_2m", "weathercode"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(hourly_vars),
        "timezone": timezone,
        # request current_weather for simple immediate reading:
        "current_weather": "true"
    }
    resp = requests.get(OPEN_METEO_BASE, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

# -------------------------
# Helper: call Air Quality API
# -------------------------
def fetch_air_quality(lat: float, lon: float, hourly_vars: Optional[list] = None, timezone: str = "auto") -> Dict[str, Any]:
    """
    Fetch air quality from Open-Meteo Air Quality API robustly.

    - Use exact hourly variable names as in docs (note: 'sulphur_dioxide' not 'sulfur_dioxide')
    - Try a sequence of requests if the API rejects too-large hourly lists.
    - Return the raw JSON on success; on failure return {'error': '...'}.
    """
    # correct default hourly variables (note 'sulphur_dioxide' spelling)
    if hourly_vars is None:
        hourly_vars = ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone"]

    base_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(hourly_vars),
        "timezone": timezone
    }

    # some helpful back-off strategies: full list -> drop timezone -> request small subset
    attempts = [
        base_params,
        {k: v for k, v in base_params.items() if k != "timezone"},
        {"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10"},
    ]

    last_exc = None
    for params in attempts:
        try:
            resp = requests.get(OPEN_AIR_BASE, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as he:
            last_exc = he
            status = None
            try:
                status = he.response.status_code
            except Exception:
                pass
            LOG.warning("Air quality fetch attempt failed (status=%s) params=%s", status, params)
            # on 400/422 -> try the next attempt
            continue
        except Exception as e:
            last_exc = e
            LOG.warning("Air quality fetch attempt exception: %s params=%s", e, params)
            continue

    # all attempts failed: return error object
    err_msg = str(last_exc) if last_exc is not None else "unknown error"
    LOG.warning("Air quality fetch failed after retries: %s", err_msg)
    return {"error": f"air_quality_fetch_failed: {err_msg}"}


def _latest_scalar_from_hourly(hourly: Dict[str, Any], key: str) -> Optional[float]:
    """
    Given the 'hourly' mapping from Open-Meteo, extract the most recent non-null scalar
    value for `key`. Returns None when not available.
    """
    if not hourly or key not in hourly:
        return None
    vals = hourly.get(key)
    if not isinstance(vals, list):
        # sometimes value may already be scalar
        try:
            return float(vals)
        except Exception:
            return None
    # find last non-null value
    for v in reversed(vals):
        if v is None:
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None


def fetch_air_quality_summary(lat: float, lon: float) -> Dict[str, Any]:
    """
    High-level helper: fetch raw air-quality data then extract a compact 'summary' dict
    mapping pollutant -> latest numeric value (or None).
    """
    raw = fetch_air_quality(lat, lon)
    if not isinstance(raw, dict) or raw.get("error"):
        return {"error": raw.get("error") if isinstance(raw, dict) else "fetch_failed", "raw": raw}

    hourly = raw.get("hourly", {})
    # list of pollutant keys we care about (must match docs exactly)
    pollutant_keys = ["pm2_5", "pm10", "ozone", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide"]
    summary = {}
    for pk in pollutant_keys:
        summary[pk] = _latest_scalar_from_hourly(hourly, pk)

    # include raw units if present
    units = (raw.get("hourly_units") or {})
    return {"summary": summary, "units": {k: units.get(k) for k in summary.keys() if k in units}, "raw": raw}

def interpret_air_quality(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Same interpreter as before but expects `summary` to be the dict produced by fetch_air_quality_summary(),
    i.e. {'summary': {'pm2_5': val, ...}, 'units': {...}, 'raw': ...}
    """
    # accept either the 'summary' object directly or wrapped container
    if summary is None:
        return {"overall": "unknown", "pollutants": {}, "recommendations": []}

    # if caller passed the container produced by fetch_air_quality_summary
    if "summary" in summary and isinstance(summary["summary"], dict):
        sdict = summary["summary"]
    elif isinstance(summary, dict):
        sdict = summary
    else:
        sdict = {}

    # reuse thresholds; convert to floats or None
    def to_float(v):
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    pm25 = to_float(sdict.get("pm2_5"))
    pm10 = to_float(sdict.get("pm10"))
    ozone = to_float(sdict.get("ozone"))
    no2 = to_float(sdict.get("nitrogen_dioxide"))
    so2 = to_float(sdict.get("sulphur_dioxide"))
    co = to_float(sdict.get("carbon_monoxide"))

    # same category functions (kept conservative)
    def cat_pm25(v):
        if v is None: return None
        if v <= 12: return "Good"
        if v <= 35.4: return "Moderate"
        if v <= 55.4: return "Unhealthy for Sensitive Groups"
        if v <= 150.4: return "Unhealthy"
        if v <= 250.4: return "Very Unhealthy"
        return "Hazardous"

    def cat_pm10(v):
        if v is None: return None
        if v <= 54: return "Good"
        if v <= 154: return "Moderate"
        if v <= 254: return "Unhealthy for Sensitive Groups"
        if v <= 354: return "Unhealthy"
        if v <= 424: return "Very Unhealthy"
        return "Hazardous"

    def cat_generic(v):
        if v is None: return None
        if v <= 50: return "Good"
        if v <= 100: return "Moderate"
        if v <= 200: return "Unhealthy for Sensitive Groups"
        return "Unhealthy"

    pollutants = {
        "pm2_5": {"value": pm25, "category": cat_pm25(pm25)},
        "pm10": {"value": pm10, "category": cat_pm10(pm10)},
        "ozone": {"value": ozone, "category": (lambda x: "Good" if x is None else ("Good" if x<=50 else ("Moderate" if x<=100 else ("Unhealthy" if x>100 else None))))(ozone)},
        "nitrogen_dioxide": {"value": no2, "category": cat_generic(no2)},
        "sulphur_dioxide": {"value": so2, "category": cat_generic(so2)},
        "carbon_monoxide": {"value": co, "category": cat_generic(co)},
    }

    # derive overall severity by picking the worst category
    severity_rank = {"Good": 0, "Moderate": 1, "Unhealthy for Sensitive Groups": 2, "Unhealthy": 3, "Very Unhealthy": 4, "Hazardous": 5}
    max_sev = 0
    for v in pollutants.values():
        cat = v.get("category")
        if cat in severity_rank:
            max_sev = max(max_sev, severity_rank[cat])
    inv_rank = {v: k for k, v in severity_rank.items()}
    overall = inv_rank.get(max_sev, "unknown")

    # simple, non-medical recommendations
    recs = []
    if overall in ("Unhealthy", "Very Unhealthy", "Hazardous"):
        recs = [
            "Avoid prolonged outdoor exertion; stay indoors if possible.",
            "Use an N95/FFP2 respirator if you must go outside.",
            "Keep windows closed and run air filtration if available.",
            "People with respiratory or cardiovascular conditions should follow their care plans and seek medical advice if unwell."
        ]
    elif overall == "Unhealthy for Sensitive Groups":
        recs = [
            "Reduce prolonged or heavy outdoor exertion if you are in a sensitive group.",
            "Consider wearing a mask outdoors if pollution is localized."
        ]
    elif overall == "Moderate":
        recs = ["Some individuals may be sensitive — consider reducing intense outdoor activity."]
    else:
        recs = ["Air quality looks acceptable for general outdoor activities."]

    return {"overall": overall, "pollutants": pollutants, "recommendations": recs}

# -------------------------
# Helper: call Gemini
# -------------------------
def call_gemini_via_google_genai(prompt: str, model: str = GEMINI_MODEL, max_tokens: int = 512) -> str:
    """
    Use google-genai python client (preferred).
    Requires google-genai installed and authenticated as per Google docs/quickstart.
    """
    if not HAS_GOOGLE_GENAI:
        raise RuntimeError("google-genai client not available")
    # quick usage based on google-genai docs
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))  # uses default env auth (GOOGLE_API_KEY etc) per SDK setup
        response = client.generate_text(model=model, prompt=prompt, max_output_tokens=max_tokens)
        # SDK return structure may vary; convert to text
        return response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        raise RuntimeError(f"google-genai call failed: {e}")

def call_gemini_via_rest(prompt: str, model: str = GEMINI_MODEL, max_tokens: int = 512) -> str:
    """
    Generic REST fallback. You must set GEMINI_REST_URL and GEMINI_API_KEY.
    This function assumes a simple API that accepts JSON {"model":..., "prompt":...}
    and returns {"output": "..."}. If your provider uses a different shape, adapt accordingly.
    """
    # REST fallback removed from this build. If you need a REST-based Gemini provider,
    # implement a custom call function here matching your provider's API shape.
    raise RuntimeError("REST fallback removed: google-genai SDK is the supported path in this build.")

def call_gemini(prompt: str, model: str = GEMINI_MODEL, max_tokens: int = 512) -> str:
    """
    Unified call: try google-genai client first, else REST fallback.
    """
    if HAS_GOOGLE_GENAI:
        try:
            return call_gemini_via_google_genai(prompt, model=model, max_tokens=max_tokens)
        except Exception as e:
            LOG.warning("google-genai call failed: %s", e)
            # fall through to lightweight fallback below

    # Lightweight local fallback when google-genai SDK is not available or failed.
    # This avoids hard crashes in environments without the SDK. For production,
    # install and configure the `google-genai` package or replace this function
    # with an implementation that calls your chosen LLM provider.
    LOG.warning("google-genai not available or failed; using local mock LLM fallback.")
    try:
        # produce a concise mock reply based on the prompt (first 600 chars)
        snippet = prompt.replace("\n", " ")[:600]
        return f"[LLM RESPONSE] Based on provided data: {snippet}"
    except Exception:
        return "[LLM RESPONSE] (failed to generate mock reply)"

# -------------------------
# LangGraph Nodes
# -------------------------
# Provide a small Node base if langgraph not installed
if Node is object:
    class NodeBase:
        def run(self, state: Dict[str, Any]) -> None:
            raise NotImplementedError
else:
    NodeBase = Node

class LocationNode(NodeBase):
    """Ensure we have lat/lon. If missing, expect the frontend to provide them."""
    def run(self, state: Dict[str, Any]) -> None:
        lat = state.get("lat")
        lon = state.get("lon")
        if lat is None or lon is None:
            # no server-side fallback for IP geolocation implemented (frontend should provide).
            # we raise so upper layer can return instructive error to client
            state["error"] = "missing_location"
            state["error_message"] = "Latitude/longitude not provided. Please allow browser to share location or pass lat/lon."
            return
        try:
            state["lat"] = float(lat)
            state["lon"] = float(lon)
        except Exception:
            state["error"] = "invalid_location"
            state["error_message"] = "Latitude/longitude could not be parsed to float."

class FetchWeatherNode(NodeBase):
    """Call Open-Meteo and attach result to state['weather']"""
    def run(self, state: Dict[str, Any]) -> None:
        if state.get("error"):
            return
        lat = state.get("lat"); lon = state.get("lon")
        try:
            data = fetch_open_meteo(lat, lon)
            state["weather_raw"] = data
            # also pull current_weather if available
            state["current_weather"] = data.get("current_weather")
        except Exception as e:
            state["error"] = "weather_fetch_failed"
            state["error_message"] = f"Open-Meteo request failed: {e}"

class FetchAirQualityNode(NodeBase):
    """Optional: call air-quality API and attach result to state['air_quality_raw']"""
    def run(self, state: Dict[str, Any]) -> None:
        if state.get("error"):
            return
        # Only fetch if requested
        if not state.get("include_air_quality"):
            return
        lat = state.get("lat"); lon = state.get("lon")
        try:
            aq = fetch_air_quality(lat, lon)
            state["air_quality_raw"] = aq
            # include a simple summary (latest values if hourly present)
            hourly = aq.get("hourly", {})
            if hourly:
                # take last timestamp index if present
                times = hourly.get("time", [])
                idx = len(times)-1 if times else 0
                summary = {}
                for k, vals in hourly.items():
                    if k == "time": 
                        continue
                    try:
                        summary[k] = vals[idx] if isinstance(vals, list) and idx < len(vals) else vals
                    except Exception:
                        summary[k] = None
                state["air_quality_summary"] = summary
                # interpret summary to categories and recommendations
                try:
                    interp = interpret_air_quality(summary)
                    state["air_quality_interpretation"] = interp
                except Exception as e:
                    LOG.debug("Air quality interpretation failed: %s", e)
        except Exception as e:
            LOG.warning("Air quality node failed: %s", e)
            state["air_quality_raw"] = {"error": str(e)}

class LLMNode(NodeBase):
    """Format prompt from user query + weather + air-quality and call Gemini. Save reply in state['llm_reply']"""
    def build_prompt(self, query: str, lat: float, lon: float, weather: Dict[str, Any], air_quality: Dict[str, Any]) -> str:
        # Keep prompt specific: include brief current weather summary and ask model to answer query.
        current = weather.get("current_weather") or {}
        hourly = weather.get("hourly", {})
        summary_lines = []
        if current:
            cw_temp = current.get("temperature")
            cw_wind = current.get("windspeed")
            cw_time = current.get("time")
            summary_lines.append(f"Current weather at {lat:.4f},{lon:.4f} (time {cw_time}): temperature {cw_temp} °C, windspeed {cw_wind} m/s.")
        # include humidity if available in hourly
        if isinstance(hourly, dict) and "relativehumidity_2m" in hourly:
            rh = _latest_scalar_from_hourly(hourly, "relativehumidity_2m")
            if rh is not None:
                summary_lines.append(f"Recent relative humidity: {rh}%")
        hour_keys = list(hourly.keys()) if isinstance(hourly, dict) else []
        if hour_keys:
            summary_lines.append(f"Hourly variables available: {', '.join(hour_keys[:6])} (truncated).")
        # include air quality summary if present
        if air_quality:
            if air_quality.get("error"):
                summary_lines.append("Air-quality data: unavailable.")
            else:
                aq_summary = air_quality.get("summary") or air_quality.get("air_quality_summary") or {}
                if isinstance(aq_summary, dict) and aq_summary:
                    aq_parts = []
                    for k, v in aq_summary.items():
                        aq_parts.append(f"{k}={v}")
                    summary_lines.append("Air quality (recent): " + ", ".join(aq_parts))
                else:
                    aq_hourly = air_quality.get("hourly", {})
                    if aq_hourly:
                        summary_lines.append(f"Air-quality variables available: {', '.join(list(aq_hourly.keys())[:6])} (truncated).")
        abstract = "\\n".join(summary_lines)
        # Instruct model to return strict JSON only with the requested fields.
        prompt = (
            f"You are a concise weather & air-quality assistant. Use ONLY the small summary data provided (temperature, humidity, precipitation, and pollutant readings) to answer the user question.\n\n"
            f"User question: {query}\n\n"
            f"Concise data summary:\n{abstract}\n\n"
            "Return a JSON object only (no surrounding text) with this minimal schema tailored to the user's query. Only include fields that are relevant to the user's request:\n"
            "{\n"
            "  \"answer\": string,            // concise natural-language reply\n"
            "  \"confidence\": number,        // 0-100 confidence\n"
            "  \"recommendations\": [string], // short non-medical precautions or actions\n"
            "  \"air_quality\": {             // include only when relevant or requested\n"
            "      \"overall\": string,\n"
            "      \"pollutants\": object    // pollutant -> {value, category}\n"
            "  },\n"
            "  \"weather\": {                 // include only small selected fields if helpful\n"
            "      \"temperature_c\": number,\n"
            "      \"relative_humidity\": number\n"
            "  }\n"
            "}\n\n"
            "Ignore large raw JSON blobs and do not invent additional numeric fields. If data is insufficient, respond concisely stating that and give general, non-medical advice when appropriate.\n"
        )
        return prompt

    def run(self, state: Dict[str, Any]) -> None:
        if state.get("error"):
            return
        query = state.get("query", "").strip()
        lat = state.get("lat"); lon = state.get("lon")
        weather = state.get("weather_raw", {})
        airq = state.get("air_quality_raw", {}) if state.get("include_air_quality") else {}
        if not query:
            state["error"] = "missing_query"
            state["error_message"] = "No query provided."
            return
        prompt = self.build_prompt(query, lat, lon, weather, airq)

        # Detect if the user's query is specifically about air quality / pollutants
        q_lower = (query or "").lower()
        aq_keywords = ["pm2.5", "pm2_5", "pm25", "pm10", "air quality", "aqi", "pollutant", "pollutants"]
        is_aq_query = any(k in q_lower for k in aq_keywords)

        # If google-genai is not available, synthesize a structured response locally (deterministic fallback).
        if not HAS_GOOGLE_GENAI:
            try:
                # Build compact weather snapshot
                current = state.get("current_weather") or {}
                temp = current.get("temperature") if current else None
                rh = None
                if isinstance(state.get("weather_raw", {}), dict):
                    rh = _latest_scalar_from_hourly(state["weather_raw"].get("hourly", {}), "relativehumidity_2m")
                # Use AQ interpretation if available
                aq_interp = state.get("air_quality_interpretation")
                if not aq_interp and state.get("air_quality_summary"):
                    try:
                        aq_interp = interpret_air_quality({"summary": state.get("air_quality_summary")})
                    except Exception:
                        aq_interp = None

                # If AQ-focused query -> return AQ-only structured response
                if is_aq_query:
                    pollutants = (aq_interp.get("pollutants") if isinstance(aq_interp, dict) else {})
                    if pollutants:
                        lines = []
                        for k, info in pollutants.items():
                            val = info.get("value")
                            cat = info.get("category")
                            lines.append(f"{k}: {val} ({cat})")
                        answer = " ; ".join(lines)
                    else:
                        answer = "Air-quality data unavailable for this location."
                    structured = {
                        "answer": answer,
                        "confidence": 60,
                        "recommendations": aq_interp.get("recommendations", []) if isinstance(aq_interp, dict) else [],
                        "air_quality": {
                            "overall": aq_interp.get("overall", "unknown") if isinstance(aq_interp, dict) else "unknown",
                            "pollutants": pollutants
                        },
                        "weather": {
                            "temperature_c": temp,
                            "relative_humidity": rh
                        }
                    }
                    state["response_structured"] = structured
                    state["llm_reply"] = "[local-fallback] AQ structured response generated"
                    return

                # Non-AQ query fallback: focus on temp/humidity/precip if relevant to the question
                precip_vals = []
                hw = state.get("weather_raw", {}).get("hourly", {}) if isinstance(state.get("weather_raw", {}), dict) else {}
                if isinstance(hw, dict) and "precipitation" in hw:
                    try:
                        precip_vals = [float(x) for x in hw.get("precipitation", []) if x is not None]
                    except Exception:
                        precip_vals = []
                # Simple heuristic: is there meaningful precipitation in next 24 entries?
                will_precip = any(v > 0.1 for v in (precip_vals[:24] if precip_vals else []))
                answer = ""
                if "rain" in q_lower or "precip" in q_lower:
                    answer = "Likely precipitation detected in forecast." if will_precip else "No significant precipitation detected in the immediate forecast."
                else:
                    # general descriptive answer using temp/humidity
                    if temp is not None and rh is not None:
                        answer = f"Temperature ~{temp} °C, relative humidity ~{rh}%."
                    elif temp is not None:
                        answer = f"Temperature ~{temp} °C."
                    else:
                        answer = "Insufficient weather data to answer precisely."

                recs = []
                if aq_interp and isinstance(aq_interp, dict):
                    for r in aq_interp.get("recommendations", []):
                        if r not in recs:
                            recs.append(r)

                structured = {
                    "answer": answer,
                    "confidence": 60 if not will_precip else 75,
                    "recommendations": recs,
                    "air_quality": {
                        "overall": aq_interp.get("overall", "unknown") if isinstance(aq_interp, dict) else "unknown",
                        "pollutants": aq_interp.get("pollutants", {}) if isinstance(aq_interp, dict) else {}
                    },
                    "weather": {
                        "temperature_c": temp,
                        "relative_humidity": rh
                    }
                }
                state["response_structured"] = structured
                state["llm_reply"] = "[local-fallback] structured response generated"
                return
            except Exception as e:
                LOG.exception("Local structured fallback failed: %s", e)
                # fallback to normal mock text reply below

        # otherwise, call configured LLM (google-genai preferred, else mock text)
        try:
            reply = call_gemini(prompt, model=GEMINI_MODEL, max_tokens=512)
            # normalize to string
            text = reply if isinstance(reply, str) else str(reply)
            state["llm_reply"] = text
            # attempt to extract JSON from the model output
            parsed = None
            try:
                parsed = json.loads(text)
            except Exception:
                # try to find JSON substring
                s = text
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        parsed = json.loads(s[start:end+1])
                    except Exception:
                        parsed = None
            if isinstance(parsed, dict):
                state["response_structured"] = parsed
        except Exception as e:
            state["error"] = "llm_failed"
            state["error_message"] = f"Gemini call failed: {e}"

class RespondNode(NodeBase):
    """Prepare final response JSON for client"""
    def run(self, state: Dict[str, Any]) -> None:
        if state.get("error"):
            return
        # Prefer structured JSON output from the LLM (response_structured)
        structured = state.get("response_structured")
        if isinstance(structured, dict):
            out = structured.copy()
            out.setdefault("meta", {})
            out["meta"]["source"] = "open-meteo"
            out["meta"]["llm_model"] = GEMINI_MODEL
            # Ensure weather.current contains only small selected fields
            w = out.setdefault("weather", {})
            # Normalize weather.current fields from available state
            temp = w.get("temperature_c") if w.get("temperature_c") is not None else _latest_scalar_from_hourly(state.get("weather_raw", {}).get("hourly", {}), "temperature_2m") or (state.get("current_weather") or {}).get("temperature")
            rh = w.get("relative_humidity") if w.get("relative_humidity") is not None else _latest_scalar_from_hourly(state.get("weather_raw", {}).get("hourly", {}), "relativehumidity_2m")
            out["weather"] = {"temperature_c": temp, "relative_humidity": rh}
            if state.get("include_air_quality"):
                out.setdefault("air_quality", {})
                out["air_quality"]["interpretation"] = state.get("air_quality_interpretation")
            state["response"] = out
            return

        # Fallback: textual reply with summarized metadata
        resp = {
            "answer": state.get("llm_reply"),
            "weather": {
                "current": state.get("current_weather"),
                "hourly_keys": list(state.get("weather_raw", {}).get("hourly", {}).keys())
            },
            "meta": {"source": "open-meteo", "llm_model": GEMINI_MODEL}
        }
        if state.get("include_air_quality"):
            aq_raw = state.get("air_quality_raw", {})
            resp["air_quality"] = {
                "summary": state.get("air_quality_summary") or aq_raw.get("summary"),
                "hourly_keys": list(aq_raw.get("hourly", {}).keys()) if isinstance(aq_raw.get("hourly"), dict) else [],
                "interpretation": state.get("air_quality_interpretation")
            }
        state["response"] = resp

# -------------------------
# Build Graph
# -------------------------
def build_graph():
    if LANGGRAPH_AVAILABLE and Graph is not None:
        g = Graph()
        g.add_node("loc", LocationNode())
        g.add_node("fetch", FetchWeatherNode())
        g.add_node("aq", FetchAirQualityNode())
        g.add_node("llm", LLMNode())
        g.add_node("respond", RespondNode())
        try:
            g.add_edge("loc", "fetch")
            g.add_edge("fetch", "aq")
            g.add_edge("aq", "llm")
            g.add_edge("llm", "respond")
        except Exception:
            LOG.debug("Graph.add_edge not supported; will execute nodes sequentially.")
        return g
    else:
        # fallback sequential runner
        class FallbackGraph:
            def __init__(self):
                self.nodes = {"loc": LocationNode(), "fetch": FetchWeatherNode(), "aq": FetchAirQualityNode(), "llm": LLMNode(), "respond": RespondNode()}
            def run(self, state):
                for name in ("loc","fetch","aq","llm","respond"):
                    node = self.nodes[name]
                    node.run(state)
            def get_node(self, name):
                return self.nodes.get(name)
        LOG.warning("LangGraph not available; using fallback sequence.")
        return FallbackGraph()

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="LangGraph Weather Agent (Open-Meteo + Gemini)")
graph = build_graph()

class AgentRequest(BaseModel):
    query: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    include_air_quality: Optional[bool] = False

@app.post("/agent")
async def agent_endpoint(req: AgentRequest):
    state = {"query": req.query, "lat": req.lat, "lon": req.lon, "include_air_quality": bool(req.include_air_quality)}
    # run graph
    try:
        if hasattr(graph, "run"):
            graph.run(state)
        elif hasattr(graph, "execute"):
            graph.execute(state)
        else:
            # fallback manual
            for n in ("loc","fetch","aq","llm","respond"):
                node = graph.get_node(n)
                if node:
                    node.run(state)
    except Exception as e:
        LOG.exception("Graph execution error")
        raise HTTPException(status_code=500, detail=str(e))

    if state.get("error"):
        raise HTTPException(status_code=400, detail=state.get("error_message"))

    return state.get("response", {})

# -------------------------
# CLI (quick test)
# -------------------------
def main():
    if len(sys.argv) > 1:
        # simple CLI usage: python main.py "What will the weather be like today?" 12.34 56.78 [include_air_quality]
        query = sys.argv[1]
        lat = float(sys.argv[2]) if len(sys.argv) > 2 else None
        lon = float(sys.argv[3]) if len(sys.argv) > 3 else None
        include_aq = False
        if len(sys.argv) > 4:
            include_aq = str(sys.argv[4]).lower() in ("1","true","yes","aq","air")
        state = {"query": query, "lat": lat, "lon": lon, "include_air_quality": include_aq}
        graph.run(state)
        print(json.dumps(state.get("response"), indent=2))
    else:
        print(f"Starting FastAPI server on {HOST}:{PORT}")
        uvicorn.run("main:app", host=HOST, port=PORT, reload=False)

if __name__ == "__main__":
    main()
