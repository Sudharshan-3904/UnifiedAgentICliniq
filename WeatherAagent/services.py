"""Service layer for the Weather AQI agent.

This file extracts responsibilities: network/weather fetching and LLM calls
so that the agent logic depends on small focused abstractions (SRP, DI).
"""
import os
import json
import requests
import google.generativeai as genai
from typing import Any, Dict

WEATHER_KEY = os.getenv("WEATHERAPI_KEY")
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")

if not WEATHER_KEY:
    raise Exception("WEATHERAPI_KEY is missing")
if not GEMINI_KEY:
    raise Exception("GOOGLE_API_KEY is missing")

genai.configure(api_key=GEMINI_KEY)


class WeatherService:
    def fetch_weather(self, location: str) -> Dict[str, Any]:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q={location}&aqi=yes"
        resp = requests.get(url, timeout=5).json()
        return {
            "location": location,
            "temp_c": resp["current"]["temp_c"],
            "condition": resp["current"]["condition"]["text"],
            "humidity": resp["current"]["humidity"],
            "wind_kph": resp["current"]["wind_kph"],
            "aqi_pm25": resp["current"]["air_quality"]["pm2_5"],
        }


class LLMAdapter:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(model_name)

    def run(self, prompt: str) -> str:
        result = self.model.generate_content(prompt)
        return result.text


def make_services():
    return WeatherService(), LLMAdapter()
