"""Refactored WeatherAgent runner that composes service clients (SRP/DI).
"""
from WeatherAgent.services import make_clients


def run_demo(lat, lon):
    om_client, aq_client = make_clients()
    weather = om_client.fetch_open_meteo(lat, lon)
    aq = aq_client.fetch_air_quality(lat, lon)
    return {"weather": weather.get("current_weather"), "air_quality_sample": aq.get("summary") if isinstance(aq, dict) else aq}


if __name__ == '__main__':
    print(run_demo(37.7749, -122.4194))
