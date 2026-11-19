"""Forecast windows, provider parsing and shared cache behavior."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

from forecast_fixture import weather_payload

path = Path(__file__).parents[1]/"custom_components/weather_analysis/forecast.py"
spec = importlib.util.spec_from_file_location("weather_forecast",path)
forecast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forecast)


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,11,19,9,30,tzinfo=timezone.utc)
        self.payload = weather_payload(self.now)

    def test_rest_of_today_and_full_tomorrow_in_three_hour_slots(self):
        data = forecast.build_forecast(self.payload,self.now)
        today,tomorrow = data["days"]
        self.assertEqual(today["date"],"2026-11-19")
        self.assertEqual(today["slots"][0]["start"],self.now.timestamp())
        self.assertEqual(today["slots"][0]["end"]-today["slots"][0]["start"],5400)
        self.assertEqual(len(tomorrow["slots"]),8)
        self.assertEqual([datetime.fromtimestamp(slot["start"],ZoneInfo(data["timezone"])).hour for slot in tomorrow["slots"]],list(range(0,24,3)))
        self.assertTrue(all(slot["start"]>=self.now.timestamp() for day in data["days"] for slot in day["slots"]))
        self.assertEqual(data["location"]["postal_code"],"67459")
        self.assertEqual(data["source_url"],"https://open-meteo.com/")

    def test_remaining_hour_rain_and_probability_use_preceding_hour_semantics(self):
        hourly=self.payload["hourly"]
        for index,timestamp in enumerate(hourly["time"]):
            local=datetime.fromtimestamp(timestamp,ZoneInfo("Europe/Berlin"))
            if local.date()==self.now.astimezone(ZoneInfo("Europe/Berlin")).date():
                if local.hour==10:hourly["temperature_2m"][index]=10
                if local.hour==11:hourly["temperature_2m"][index]=12;hourly["precipitation_probability"][index]=30;hourly["weather_code"][index]=95
                if local.hour==12:hourly["precipitation_probability"][index]=90
        slot=forecast.build_forecast(self.payload,self.now)["days"][0]["slots"][0]
        self.assertEqual(slot["temperature"],11)
        self.assertEqual(slot["precipitation"],1.5)
        self.assertEqual(slot["precipitation_probability"],90)
        self.assertEqual(slot["condition"],"Gewitter")
        self.assertTrue(slot["partial"])

    def test_missing_rain_is_unknown_instead_of_zero(self):
        first_end=self.now.timestamp()+1800
        index=self.payload["hourly"]["time"].index(first_end)
        self.payload["hourly"]["precipitation"][index]=None
        self.payload["hourly"]["precipitation_probability"][index]=None
        slot=forecast.build_forecast(self.payload,self.now)["days"][0]["slots"][0]
        self.assertIsNone(slot["precipitation"])
        self.assertIsNone(slot["precipitation_probability"])

    def test_visual_details_keep_units_ranges_and_circular_wind_direction(self):
        hourly=self.payload["hourly"]
        left=hourly["time"].index(self.now.timestamp()-1800)
        hourly["wind_direction_10m"][left:left+2]=[350,10]
        hourly["temperature_2m"][left:left+3]=[10,12,9]
        # A gust before the remaining window must not inflate the period's maximum.
        hourly["wind_gusts_10m"][left]=99
        slot=forecast.build_forecast(self.payload,self.now)["days"][0]["slots"][0]
        self.assertEqual(slot["wind_direction"],0)
        self.assertEqual(slot["wind_gusts"],24)
        self.assertEqual((slot["temperature_min"],slot["temperature_max"]),(9,12))
        self.assertEqual(slot["apparent_temperature"],8)
        self.assertEqual(slot["humidity"],80)
        self.assertEqual(slot["pressure"],1013)
        self.assertEqual(slot["weather_code"],3)

    def test_unknown_or_invalid_visual_details_are_not_invented(self):
        hourly=self.payload["hourly"]
        for key,value in [("relative_humidity_2m",101),("pressure_msl",-1),("wind_direction_10m",500),("wind_gusts_10m",None),("apparent_temperature",None),("temperature_2m",None)]:
            hourly[key]=[value]*len(hourly["time"])
        # Keep tomorrow valid so the core forecast is still useful.
        hourly["temperature_2m"][24:]=[10.]*(len(hourly["time"])-24)
        slot=forecast.build_forecast(self.payload,self.now)["days"][0]["slots"][0]
        for name in ["humidity","pressure","wind_direction","wind_gusts","apparent_temperature","temperature_min","temperature_max"]:
            self.assertIsNone(slot[name])

    def test_dst_uses_local_three_hour_blocks_and_full_days(self):
        for now,hours in [(datetime(2026,3,28,12,tzinfo=timezone.utc),23),(datetime(2026,10,24,12,tzinfo=timezone.utc),25)]:
            slots=forecast.build_forecast(weather_payload(now),now)["days"][1]["slots"]
            self.assertEqual(len(slots),8)
            self.assertEqual(sum(slot["end"]-slot["start"] for slot in slots),hours*3600)

    def test_malformed_or_wrong_units_and_incomplete_ranges_are_rejected(self):
        for change in [lambda data:data["hourly_units"].update(temperature_2m="°F"),lambda data:data["hourly"]["time"].reverse(),lambda data:data["hourly"].update(temperature_2m=[]),lambda data:data["hourly"].update(time=[])]:
            payload=deepcopy(self.payload);change(payload)
            with self.assertRaises(ValueError):forecast.build_forecast(payload,self.now)


class Response:
    def __init__(self,payload):self.payload=payload
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def raise_for_status(self):pass
    async def json(self):return self.payload


class Session:
    def __init__(self,payload):self.payload,self.calls,self.failure=payload,[],None
    def get(self,url,params):
        self.calls.append((url,params))
        if self.failure:raise self.failure
        return Response(self.payload)


class ForecastCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.time=[datetime(2026,11,19,9,30,tzinfo=timezone.utc)]
        self.session=Session(weather_payload(self.time[0]))
        self.client=forecast.ForecastClient(None,self.session,lambda:self.time[0])

    async def test_parallel_cards_share_one_request_and_fixed_location(self):
        values=await asyncio.gather(*(self.client.get() for _ in range(4)))
        self.assertEqual(len(self.session.calls),1)
        self.assertFalse(values[0]["stale"])
        url,params=self.session.calls[0]
        self.assertEqual(url,forecast.API_URL)
        self.assertEqual(params["latitude"],49.3806)
        self.assertEqual(params["longitude"],8.3039)
        self.assertEqual(params["timeformat"],"unixtime")

    async def test_cache_recomputes_remaining_windows_without_new_request(self):
        initial=await self.client.get();self.time[0]+=timedelta(minutes=10)
        later=await self.client.get()
        self.assertEqual(later["days"][0]["slots"][0]["start"],self.time[0].timestamp())
        self.assertEqual(initial["updated_at"],later["updated_at"])
        self.assertEqual(len(self.session.calls),1)

    async def test_failure_returns_recent_stale_forecast_then_expires(self):
        initial=await self.client.get();self.time[0]+=timedelta(minutes=31);self.session.failure=OSError("offline")
        stale=await self.client.get();self.assertTrue(stale["stale"])
        self.assertEqual(stale["updated_at"],initial["updated_at"])
        await self.client.get();self.assertEqual(len(self.session.calls),2)
        self.time[0]+=timedelta(hours=7)
        with self.assertRaises(forecast.ForecastUnavailable):await self.client.get()

    async def test_initial_provider_failure_is_explicit_and_backed_off(self):
        self.session.failure=OSError("offline")
        for _ in range(2):
            with self.assertRaises(forecast.ForecastUnavailable):await self.client.get()
        self.assertEqual(len(self.session.calls),1)

    async def test_forecast_starts_at_the_same_explicit_snapshot_as_measurements(self):
        snapshot=self.time[0].timestamp()-37
        data=await self.client.get(as_of=snapshot)
        self.assertEqual(data["as_of"],snapshot)
        self.assertEqual(data["days"][0]["slots"][0]["start"],snapshot)
        self.time[0]+=timedelta(minutes=5)
        again=await self.client.get(as_of=snapshot)
        self.assertEqual(again["days"][0]["slots"][0]["start"],snapshot)
        self.assertEqual(len(self.session.calls),1)

    async def test_invalid_forecast_snapshot_never_contacts_provider(self):
        for value in (float("nan"),True,-1,self.time[0].timestamp()+3600):
            with self.assertRaises(forecast.ForecastUnavailable):await self.client.get(as_of=value)
        self.assertEqual(self.session.calls,[])

    async def test_cancellation_is_not_swallowed(self):
        self.session.failure=asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):await self.client.get()
