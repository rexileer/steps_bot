from __future__ import annotations

from typing import Optional
import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def get_current_temp_c(lat: float, lon: float) -> Optional[int]:
    """
    Возвращает только текущую температуру в °C по координатам (Open-Meteo, без ключа).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

        cw = data.get("current_weather") or {}
        temp = cw.get("temperature")
        if temp is None:
            return None
        return int(round(float(temp)))
    except (httpx.HTTPError, ValueError, KeyError):
        return None
