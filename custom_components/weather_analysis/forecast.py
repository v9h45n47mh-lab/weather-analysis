"""Open-Meteo forecast for 67459, grouped into local three-hour windows."""
from __future__ import annotations

import asyncio
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
import logging
import math
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)
LOCATION = {"postal_code": "67459", "name": "Böhl-Iggelheim", "latitude": 49.3806, "longitude": 8.3039}
TIMEZONE = "Europe/Berlin"
API_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE_URL = "https://open-meteo.com/"
VARIABLES = ("temperature_2m", "weather_code", "is_day", "wind_speed_10m", "precipitation_probability", "precipitation",
    "apparent_temperature", "relative_humidity_2m", "pressure_msl", "wind_direction_10m", "wind_gusts_10m")
CONDITIONS = {
    0: ("Klar", "sunny", 0), 1: ("Überwiegend klar", "partly-cloudy", 1),
    2: ("Wolkig", "partly-cloudy", 2), 3: ("Bedeckt", "cloudy", 3),
    45: ("Nebel", "fog", 4), 48: ("Reifnebel", "fog", 5),
    51: ("Leichter Nieselregen", "rainy", 6), 53: ("Nieselregen", "rainy", 7), 55: ("Starker Nieselregen", "rainy", 8),
    56: ("Gefrierender Nieselregen", "snowy-rainy", 20), 57: ("Starker gefrierender Nieselregen", "snowy-rainy", 21),
    61: ("Leichter Regen", "rainy", 9), 63: ("Regen", "rainy", 10), 65: ("Starker Regen", "pouring", 13),
    66: ("Gefrierender Regen", "snowy-rainy", 22), 67: ("Starker gefrierender Regen", "snowy-rainy", 23),
    71: ("Leichter Schneefall", "snowy", 14), 73: ("Schneefall", "snowy", 15), 75: ("Starker Schneefall", "snowy-heavy", 17),
    77: ("Schneegriesel", "snowy", 14), 80: ("Leichte Regenschauer", "rainy", 9),
    81: ("Regenschauer", "rainy", 11), 82: ("Heftige Regenschauer", "pouring", 18),
    85: ("Schneeschauer", "snowy", 16), 86: ("Starke Schneeschauer", "snowy-heavy", 19),
    95: ("Gewitter", "lightning-rainy", 24), 96: ("Gewitter mit Hagel", "hail", 25), 99: ("Starkes Gewitter mit Hagel", "hail", 26),
}


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def build_forecast(payload, now):
    """Hourly precipitation/probability refer to the preceding hour.

    Temperature is interpolated at the start of a window. Rain is accumulated,
    probability, gusts and wind use their hourly maxima. Gusts, like rain,
    describe the preceding hour. Other details describe the window start.
    Temperature ranges include both window boundaries and hourly instants.
    The first remaining window
    starts now; fractional-hour rain is apportioned by its remaining duration.
    """
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times or len(times) > 1000 or any(number(t) is None for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Invalid forecast timestamps")
    for name in VARIABLES:
        if not isinstance(hourly.get(name), list) or len(hourly[name]) != len(times):
            raise ValueError("Incomplete forecast variables")
    units = payload.get("hourly_units", {})
    if any(units.get(key) != value for key, value in {"temperature_2m": "°C", "wind_speed_10m": "km/h", "precipitation": "mm",
            "apparent_temperature": "°C", "relative_humidity_2m": "%", "pressure_msl": "hPa", "wind_direction_10m": "°", "wind_gusts_10m": "km/h"}.items()):
        raise ValueError("Unexpected forecast units")
    tz = ZoneInfo(TIMEZONE)
    local = now.astimezone(tz)
    now_ts = now.timestamp()
    required_end = (local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=2)).timestamp()
    if times[0] > now_ts or times[-1] < required_end:
        raise ValueError("Incomplete forecast range")

    def at(name, timestamp):
        i = bisect_left(times, timestamp)
        if i < len(times) and times[i] == timestamp:
            return number(hourly[name][i])
        if i == 0 or i == len(times) or times[i] - times[i-1] > 7200:
            return None
        left, right = number(hourly[name][i-1]), number(hourly[name][i])
        if left is None or right is None:
            return None
        fraction = (timestamp-times[i-1]) / (times[i]-times[i-1])
        if name == "wind_direction_10m":
            if not 0 <= left <= 360 or not 0 <= right <= 360:
                return None
            return (left + ((right-left+180) % 360-180) * fraction) % 360
        return left + (right-left) * fraction

    def window(start,end,begin):
        instants = [i for i, timestamp in enumerate(times) if start <= timestamp < end]
        nearest = min(bisect_left(times, start), len(times)-1)
        codes = [hourly["weather_code"][i] for i in instants] or [hourly["weather_code"][nearest]]
        known = [int(code) for code in codes if number(code) is not None and int(code) in CONDITIONS]
        code = max(known, key=lambda value: CONDITIONS[value][2]) if known else None
        condition, icon, _ = CONDITIONS.get(code, ("Keine Wetterangabe", "cloudy", 0))
        if code in (0, 1, 2) and hourly["is_day"][nearest] == 0:
            icon = "night" if code == 0 else "night-partly-cloudy"
        rain, probabilities, gusts, covered, probability_covered, gust_covered = [], [], [], 0., 0., 0.
        for i, timestamp in enumerate(times):
            overlap = max(0, min(end, timestamp) - max(start, timestamp-3600))
            if not overlap:
                continue
            amount = number(hourly["precipitation"][i])
            probability = number(hourly["precipitation_probability"][i])
            gust = number(hourly["wind_gusts_10m"][i])
            if amount is not None and amount >= 0:
                rain.append(amount * overlap / 3600)
                covered += overlap
            if probability is not None and 0 <= probability <= 100:
                probabilities.append(probability)
                probability_covered += overlap
            if gust is not None and gust >= 0:
                gusts.append(gust)
                gust_covered += overlap
        winds = [number(hourly["wind_speed_10m"][i]) for i in instants] + [at("wind_speed_10m", start)]
        temperatures = [number(hourly["temperature_2m"][i]) for i in instants] + [at("temperature_2m", start),at("temperature_2m", end)]
        complete_temperatures = all(value is not None for value in temperatures) and not any(
            right-left > 7200 for left,right in zip(times,times[1:]) if left < end and right > start)
        humidity, direction, pressure = at("relative_humidity_2m", start), at("wind_direction_10m", start), at("pressure_msl", start)
        return {"period_start":begin,"start": start, "end": end, "partial": start > begin,
            "temperature": at("temperature_2m", start), "condition": condition, "icon": "mdi:weather-"+icon,
            "weather_code": code, "is_day": hourly["is_day"][nearest] != 0,
            "temperature_min": min(temperatures) if complete_temperatures else None,
            "temperature_max": max(temperatures) if complete_temperatures else None,
            "apparent_temperature": at("apparent_temperature",start),
            "humidity": humidity if humidity is not None and 0 <= humidity <= 100 else None,
            "pressure": pressure if pressure is not None and pressure > 0 else None,
            "wind_direction": direction if direction is not None and 0 <= direction <= 360 else None,
            "wind_gusts": max(gusts,default=None) if gust_covered >= end-start-1 else None,
            "precipitation": sum(rain) if rain and covered >= end-start-1 else None,
            "precipitation_probability": max(probabilities, default=None) if probability_covered >= end-start-1 else None,
            "wind_speed": max((wind for wind in winds if wind is not None and wind >= 0), default=None)}

    days = []
    for offset in (0,1):
        midnight = local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=offset)
        slots = []
        for hour in range(0,24,3):
            begin = (midnight+timedelta(hours=hour)).timestamp()
            end = (midnight+timedelta(hours=hour+3)).timestamp()
            if end <= now_ts:
                continue
            start = max(begin,now_ts)
            slot = window(start,end,begin)
            edges = [start]+[timestamp for timestamp in range(int(begin),int(end),3600) if start<timestamp]+[end]
            slot["hours"] = [window(left,right,begin+math.floor((left-begin)/3600)*3600) for left,right in zip(edges,edges[1:])]
            slots.append(slot)
        days.append({"date":midnight.date().isoformat(),"label":"Heute · Resttag" if offset==0 else "Morgen","slots":slots})
    if not days[1]["slots"] or not any(slot["temperature"] is not None for slot in days[1]["slots"]):
        raise ValueError("No forecast for tomorrow")
    return {"location": LOCATION, "timezone": TIMEZONE, "source": "Open-Meteo", "source_url": SOURCE_URL, "days": days}


class ForecastUnavailable(RuntimeError):
    pass


class ForecastClient:
    """Share one cached provider request across all cards and users."""
    def __init__(self, hass, session=None, clock=None):
        self.hass, self.session = hass, session
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.raw, self.updated, self.attempt = None, None, None
        self.lock = asyncio.Lock()

    async def _download(self):
        if self.session is None:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            self.session = async_get_clientsession(self.hass)
        params = {"latitude": LOCATION["latitude"], "longitude": LOCATION["longitude"], "hourly": ",".join(VARIABLES),
            "timezone": TIMEZONE, "timeformat": "unixtime", "forecast_days": 3,
            "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm"}
        async with asyncio.timeout(12):
            async with self.session.get(API_URL, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def get(self, as_of=None):
        async with self.lock:
            now = self.clock()
            reference = now
            if as_of is not None:
                timestamp = number(as_of)
                if timestamp is None or timestamp < 0 or timestamp > now.timestamp()+300:
                    raise ForecastUnavailable("Ungültiger Vorhersagezeitpunkt.")
                reference = datetime.fromtimestamp(min(timestamp,now.timestamp()),timezone.utc)
            stale = False
            required_end = (now.astimezone(ZoneInfo(TIMEZONE)).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=2)).timestamp()
            range_missing = self.raw is None or self.raw["hourly"]["time"][-1] < required_end
            if self.updated is None or (now-self.updated).total_seconds() >= 1800 or range_missing:
                if self.attempt is None or (now-self.attempt).total_seconds() >= 300:
                    self.attempt = now
                    try:
                        raw = await self._download()
                        build_forecast(raw, now)
                        self.raw, self.updated = raw, now
                        range_missing = False
                    except Exception as error:
                        _LOGGER.warning("Weather forecast unavailable: %s", type(error).__name__)
                stale = self.updated is None or (now-self.updated).total_seconds() >= 1800 or range_missing
            if self.raw is None or self.updated is None or (now-self.updated).total_seconds() > 21600:
                raise ForecastUnavailable("Die Wettervorhersage ist derzeit nicht erreichbar.")
            try:
                result = build_forecast(self.raw, reference)
            except ValueError as error:
                raise ForecastUnavailable("Die Wettervorhersage ist derzeit nicht verfügbar.") from error
            return {**result, "as_of":reference.timestamp(), "updated_at": self.updated.timestamp(), "stale": stale}
