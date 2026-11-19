"""Coordinate validation and cached place/postcode lookup. No location persistence."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
import time

from .forecast import LOCATION, number

GEOCODING_URL = "https://photon.komoot.io/reverse"
GEOCODING_SOURCE = "Photon · OpenStreetMap"
GEOCODING_CREDIT = "https://www.openstreetmap.org/copyright"


def coordinates(latitude, longitude):
    lat, lon = number(latitude), number(longitude)
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Bitte gültige GPS-Koordinaten verwenden.")
    return round(lat, 4), round(lon, 4)


def place(payload, latitude, longitude):
    features = payload.get("features", [])
    props = features[0].get("properties", {}) if isinstance(features, list) and features and isinstance(features[0],dict) else {}
    if not isinstance(props,dict):
        props = {}
    name = next((props.get(k) for k in ("city", "town", "village", "locality", "county", "state", "country") if isinstance(props.get(k), str) and props[k].strip()), None)
    if not name and props.get("osm_value") in ("city", "town", "village", "hamlet"):
        name = props.get("name")
    postcode = str(props.get("postcode") or "").strip()[:24]
    country = str(props.get("countrycode") or "").lower()[:2]
    home = country == "de" and postcode == "67459"
    return {"latitude": latitude, "longitude": longitude,
        "name": LOCATION["name"] if home else str(name or "Aktueller Standort")[:160],
        "postal_code": postcode, "country_code": country, "is_home": home,
        "position_available": True, "resolved": bool(name or home),
        "key": f"{latitude:.4f},{longitude:.4f}",
        "source": GEOCODING_SOURCE, "source_url": GEOCODING_CREDIT}


def fallback():
    return {**LOCATION, "country_code": "de", "is_home": False, "position_available": False,
        "resolved": True, "key": "fallback-67459"}


def home_location():
    return {**fallback(),"is_home":True,"key":"home-wifi-67459","via":"home_wifi"}


class LocationClient:
    """Bounded RAM cache, shared lock and retry delay for the reverse lookup."""
    def __init__(self, hass, session=None, clock=time.monotonic):
        self.hass, self.session, self.clock = hass, session, clock
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()
        self.last_request = None

    async def get(self, latitude, longitude):
        latitude, longitude = coordinates(latitude, longitude)
        key = (latitude, longitude)
        async with self.lock:
            now = self.clock()
            if key in self.cache:
                until, result = self.cache[key]
                self.cache.move_to_end(key)
                if now < until:
                    return dict(result)
            if self.last_request is not None:
                delay = 1 - (now - self.last_request)
                if delay > 0:
                    await asyncio.sleep(delay)
            result = place({}, latitude, longitude)
            try:
                if self.session is None:
                    from homeassistant.helpers.aiohttp_client import async_get_clientsession
                    self.session = async_get_clientsession(self.hass)
                self.last_request = self.clock()
                async with asyncio.timeout(8):
                    async with self.session.get(GEOCODING_URL,
                            params={"lat": latitude, "lon": longitude, "limit": 1, "lang": "de", "radius": 5},
                            headers={"User-Agent": "WeatherAnalysis (+https://github.com/v9h45n47mh-lab/weather-analysis)"}) as response:
                        response.raise_for_status()
                        result = place(await response.json(), latitude, longitude)
            except Exception:
                # No coordinates, request URLs or person names in logs.
                pass
            self.cache[key] = (self.clock() + (43200 if result["resolved"] else 120), result)
            self.cache.move_to_end(key)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return dict(result)
