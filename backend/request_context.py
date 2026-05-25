from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from models import RecipeRequest

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    95: "thunderstorm",
}


def meal_period(hour: int) -> str:
    if 5 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 15:
        return "lunch"
    if 15 <= hour < 18:
        return "snack"
    if 18 <= hour < 22:
        return "dinner"
    return "late night"


def weather_style(condition: str | None, temperature_f: float | None, meal: str) -> str:
    parts: list[str] = [f"{meal}-appropriate"]
    if temperature_f is not None:
        if temperature_f >= 85:
            parts.append("lighter and refreshing")
        elif temperature_f <= 55:
            parts.append("warm and comforting")

    condition_text = (condition or "").lower()
    if "rain" in condition_text or "drizzle" in condition_text or "showers" in condition_text:
        parts.append("cozy for wet weather")
    if "clear" in condition_text and temperature_f is not None and temperature_f >= 75:
        parts.append("bright and fresh")

    return ", ".join(parts)


async def _fetch_weather(location_name: str) -> dict[str, Any]:
    clean_location = location_name.split(",")[0].strip()
    async with httpx.AsyncClient(timeout=5) as client:
        geocode_response = await client.get(GEOCODING_URL, params={"name": clean_location, "count": 1, "language": "en"})
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()
        results = geocode_data.get("results") or []
        if not results:
            return {"available": False, "location_name": location_name, "error": "Location not found."}

        place = results[0]
        forecast_response = await client.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,precipitation,weather_code",
                "temperature_unit": "fahrenheit",
            },
        )
        forecast_response.raise_for_status()
        current = forecast_response.json().get("current", {})
        weather_code = current.get("weather_code")

        return {
            "available": True,
            "requested_location": location_name,
            "resolved_location": ", ".join(
                part for part in [place.get("name"), place.get("admin1"), place.get("country_code")] if part
            ),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
            "temperature_f": current.get("temperature_2m"),
            "precipitation": current.get("precipitation"),
            "weather_code": weather_code,
            "condition": WEATHER_CODES.get(weather_code, "unknown"),
        }


async def build_request_context(request: RecipeRequest) -> dict[str, Any]:
    now = datetime.now().astimezone()
    meal = meal_period(now.hour)
    context: dict[str, Any] = {
        "time": {
            "iso": now.isoformat(),
            "date": now.strftime("%B %d, %Y"),
            "weekday": now.strftime("%A"),
            "time": now.strftime("%I:%M %p"),
            "hour": now.hour,
            "timezone": now.tzname(),
            "meal_period": meal,
        },
        "weather": {
            "available": False,
            "requested_location": request.location_name,
            "error": None,
        },
        "recommendation_style": f"{meal}-appropriate",
    }

    location_name = (request.location_name or "").strip()
    if location_name:
        try:
            context["weather"] = await _fetch_weather(location_name)
        except Exception as exc:
            context["weather"] = {
                "available": False,
                "requested_location": location_name,
                "error": str(exc),
            }

    weather = context["weather"]
    context["recommendation_style"] = weather_style(weather.get("condition"), weather.get("temperature_f"), meal)
    return context


def context_summary(context: dict[str, Any]) -> str:
    time_context = context["time"]
    weather = context["weather"]
    parts = [
        f"{time_context['weekday']}, {time_context['date']} at {time_context['time']} {time_context['timezone']}",
        f"meal period: {time_context['meal_period']}",
        f"style: {context['recommendation_style']}",
    ]
    if weather.get("available"):
        parts.append(
            "weather: "
            f"{weather.get('temperature_f')}F and {weather.get('condition')} "
            f"in {weather.get('resolved_location')}"
        )
    elif weather.get("requested_location"):
        parts.append(f"weather unavailable for {weather.get('requested_location')}")
    return "; ".join(parts)
