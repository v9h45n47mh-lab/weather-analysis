"""Location parsing, bounded lookup cache and GPS validation without real user locations."""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch, AsyncMock

root=Path(__file__).parents[1]/"custom_components/weather_analysis"
package=ModuleType("gps_weather_test");package.__path__=[str(root)];sys.modules[package.__name__]=package
spec=importlib.util.spec_from_file_location("gps_weather_test.location",root/"location.py")
location=importlib.util.module_from_spec(spec);sys.modules[spec.name]=location;spec.loader.exec_module(location)


def payload(city="Böhl-Iggelheim",postcode="67459",country="DE"):
    return {"features":[{"properties":{"city":city,"postcode":postcode,"countrycode":country}}]}


class Response:
    def __init__(self,data):self.data=data
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def raise_for_status(self):pass
    async def json(self):return self.data


class Session:
    def __init__(self):self.calls=[];self.failure=None
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if self.failure:raise self.failure
        return Response(payload())


class LocationTests(unittest.TestCase):
    def test_only_german_67459_enables_home_data(self):
        self.assertTrue(location.place(payload(),49.38,8.3)["is_home"])
        for city,postcode,country in [("Hamburg","20095","DE"),("Paris","67459","FR"),("Böhl-Iggelheim","","DE")]:
            result=location.place(payload(city,postcode,country),48,8)
            self.assertFalse(result["is_home"])
        self.assertFalse(location.fallback()["is_home"])
        self.assertFalse(location.fallback()["position_available"])

    def test_missing_place_is_unknown_and_never_home(self):
        for data in ({},{"features":[None]},{"features":[{"properties":None}]}):
            result=location.place(data,40,10)
            self.assertEqual(result["name"],"Aktueller Standort")
            self.assertFalse(result["is_home"])
            self.assertFalse(result["resolved"])

    def test_coordinates_are_finite_and_bounded(self):
        for lat,lon in [(True,8),(None,8),(float("nan"),8),(91,8),(49,181),("49",8)]:
            with self.assertRaises(ValueError):location.coordinates(lat,lon)
        self.assertEqual(location.coordinates(49.380612,8.303912),(49.3806,8.3039))


class LookupTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_cards_share_lookup_and_cache(self):
        session=Session();client=location.LocationClient(None,session)
        values=await asyncio.gather(*(client.get(49.3806,8.3039) for _ in range(5)))
        self.assertEqual(len(session.calls),1)
        self.assertTrue(all(v["is_home"] for v in values))
        self.assertEqual(session.calls[0][1]["params"]["lang"],"de")
        self.assertIn("WeatherAnalysis",session.calls[0][1]["headers"]["User-Agent"])

    async def test_failed_lookup_does_not_guess_home_and_is_backed_off(self):
        session=Session();session.failure=OSError("offline");clock=[100]
        client=location.LocationClient(None,session,lambda:clock[0])
        first=await client.get(49.38,8.3);await client.get(49.38,8.3)
        self.assertFalse(first["is_home"]);self.assertEqual(len(session.calls),1)
        clock[0]+=121;await client.get(49.38,8.3);self.assertEqual(len(session.calls),2)

    async def test_geocoding_is_rate_limited(self):
        session=Session();client=location.LocationClient(None,session,lambda:100)
        with patch.object(location.asyncio,"sleep",new=AsyncMock()) as sleep:
            await client.get(49.38,8.3);await client.get(53.55,10)
        sleep.assert_awaited_once_with(1)

    async def test_cancellation_propagates(self):
        session=Session();session.failure=asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):await location.LocationClient(None,session).get(49,8)
