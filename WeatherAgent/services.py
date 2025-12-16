"""Small service abstractions for WeatherAgent (SRP + DI).
"""
import requests
from typing import Dict, Any, Optional

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
OPEN_AIR_BASE = "https://air-quality-api.open-meteo.com/v1/air-quality"


class OpenMeteoClient:
    def fetch_open_meteo(self, lat: float, lon: float, hourly_vars: Optional[list] = None, timezone: str = "auto") -> Dict[str, Any]:
        if hourly_vars is None:
            hourly_vars = ["temperature_2m", "precipitation", "windspeed_10m", "relativehumidity_2m", "weathercode"]
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(hourly_vars),
            "timezone": timezone,
            "current_weather": "true"
        }
        resp = requests.get(OPEN_METEO_BASE, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()


class AirQualityClient:
    def fetch_air_quality(self, lat: float, lon: float, hourly_vars: Optional[list] = None, timezone: str = "auto") -> Dict[str, Any]:
        if hourly_vars is None:
            hourly_vars = ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone"]
        params = {"latitude": lat, "longitude": lon, "hourly": ",".join(hourly_vars), "timezone": timezone}
        resp = requests.get(OPEN_AIR_BASE, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()


def make_clients():
    return OpenMeteoClient(), AirQualityClient()
