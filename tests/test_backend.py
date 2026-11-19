"""Exercise selection, isolation, retained history and permissions with HA host mocks."""
import asyncio
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch


def module(name, **attrs):
    obj = ModuleType(name)
    obj.__dict__.update(attrs)
    sys.modules[name] = obj
    return obj


class Schema:
    def __init__(self, *args, **kwargs): pass
    def __call__(self, value): return value


class Store:
    def __init__(self, hass=None, version=None, key=None):
        self.value = None
        self.key = key
    async def async_load(self): return self.value
    async def async_save(self, data): self.value = data
    def async_delay_save(self, *args): pass


module("probatio", Required=lambda x, **kw:x, Optional=lambda x, **kw:x,
       Schema=Schema, All=Schema, Coerce=Schema, Range=Schema, Length=Schema, In=Schema)
module("homeassistant")
module("homeassistant.auth"); module("homeassistant.auth.permissions")
module("homeassistant.auth.permissions.const", POLICY_READ="read")
websocket = module("homeassistant.components.websocket_api",
    websocket_command=lambda *args:lambda f:f, async_response=lambda f:f,
    async_register_command=lambda *args:None)
frontend = module("homeassistant.components.frontend", add_extra_js_url=lambda *args:None)
module("homeassistant.components", websocket_api=websocket, frontend=frontend)
module("homeassistant.components.http", StaticPathConfig=lambda *args:args)
module("homeassistant.components.recorder")
module("homeassistant.components.recorder.statistics", statistics_during_period=lambda *args:{})
module("homeassistant.components.recorder.history", get_significant_states=lambda *args, **kwargs:{})
module("homeassistant.components.recorder.db_schema", RecorderRuns=object)
module("homeassistant.components.recorder.util", session_scope=lambda *args, **kwargs:None)
module("homeassistant.core", callback=lambda f:f)
module("homeassistant.const", EVENT_HOMEASSISTANT_STOP="stop")
module("homeassistant.helpers")
module("homeassistant.helpers.entity_registry",async_get=lambda hass:hass.registry)
module("homeassistant.helpers.event", async_track_state_change_event=lambda *args:lambda:None,
       async_track_time_interval=lambda *args:lambda:None)
module("homeassistant.helpers.recorder", get_instance=lambda hass:hass.recorder)
module("homeassistant.helpers.storage", Store=Store)
now = datetime(2026, 11, 17, 12, 30, tzinfo=timezone.utc)
dt = module("homeassistant.util.dt", utcnow=lambda:now, UTC=timezone.utc)
module("homeassistant.util", dt=dt)
path = Path(__file__).parents[1] / "custom_components/weather_analysis/__init__.py"
spec = importlib.util.spec_from_file_location("weather_analysis", path,
    submodule_search_locations=[str(path.parent)])
backend = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)


def state(entity, value, unit, kind):
    return SimpleNamespace(entity_id=entity, name=entity, state=value,
        attributes={"unit_of_measurement":unit, "device_class":kind}, last_updated=now)


class Connection:
    def __init__(self, admin=False, denied=(), user_id="test-user"):
        self.user = SimpleNamespace(id=user_id,is_admin=admin, permissions=SimpleNamespace(
            check_entity=lambda entity, policy:entity not in denied))
        self.results = []
        self.errors = []
    def send_result(self, *args): self.results.append(args)
    def send_error(self, *args): self.errors.append(args)


class BackendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.states = {
            "sensor.test":state("sensor.test", "50", "°F", "temperature"),
            "sensor.second":state("sensor.second", "5", "°C", "temperature"),
            "sensor.wind":state("sensor.wind", "5", "m/s", "wind_speed"),
            "sensor.lux":state("sensor.lux", "1234", "lx", "illuminance"),
            "sensor.humidity":state("sensor.humidity", "65", "%", "humidity")}
        async def executor(func, *args): return func(*args)
        self.hass = SimpleNamespace(
            config=SimpleNamespace(time_zone="Europe/Berlin"),
            registry=SimpleNamespace(entities={}),
            states=SimpleNamespace(get=self.states.get, async_all=lambda domain:list(self.states.values())),
            config_entries=SimpleNamespace(async_entries=lambda domain:[]),
            bus=SimpleNamespace(async_listen_once=lambda *args:lambda:None),
            recorder=SimpleNamespace(keep_days=10, async_add_executor_job=executor),
            data={backend.DOMAIN:{}, backend.DOMAIN+"_settings":{},
                  backend.DOMAIN+"_store":Store(), backend.DOMAIN+"_lock":asyncio.Lock(),
                  backend.DOMAIN+"_network":{"home_ssids":[]},backend.DOMAIN+"_network_store":Store(),backend.DOMAIN+"_network_lock":asyncio.Lock(),
                  backend.DOMAIN+"_entries":set()})
        self.hass.registry.async_get=self.hass.registry.entities.get
        self.history_patch = patch.object(backend.Manager, "read_history", return_value=backend.Archive())
        self.history_read = self.history_patch.start()
        self.addCleanup(self.history_patch.stop)
        self.manager = backend.Manager(self.hass, SimpleNamespace(data={"entity_id":"sensor.test"}, entry_id="entry"))
        self.manager.statistics = AsyncMock(return_value=[])
        self.hass.data[backend.DOMAIN]["entry"] = self.manager

    def add_position(self, user_id="test-user", person="person.test", tracker="device_tracker.phone", latitude=49.3806, longitude=8.3039):
        self.states[person] = SimpleNamespace(entity_id=person,state="home",attributes={
            "user_id":user_id,"device_trackers":[tracker],"source":tracker},last_updated=now)
        self.states[tracker] = SimpleNamespace(entity_id=tracker,state="home",attributes={
            "source_type":"gps","latitude":latitude,"longitude":longitude},last_updated=now)

    def add_wifi_registry(self, user_id="test-user", person="person.test", tracker="device_tracker.phone", ssid_entity="sensor.phone_ssid", device="phone", ssid="Home WiFi", unique="webhook_ssid"):
        self.add_position(user_id,person,tracker,53.55,10.0)
        self.states[ssid_entity]=SimpleNamespace(entity_id=ssid_entity,name=ssid_entity,state=ssid,last_updated=now,attributes={})
        for entity,uid in [(tracker,"tracker-id"),(ssid_entity,unique)]:
            self.hass.registry.entities[entity]=SimpleNamespace(entity_id=entity,device_id=device,unique_id=uid,platform="mobile_app")

    async def test_radar_ws_reuses_home_location_and_authenticated_owner(self):
        self.add_wifi_registry()
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        provider=SimpleNamespace(get=AsyncMock(return_value={"status":"ok","token":"opaque"}),image=AsyncMock(return_value="data:image/png;base64,AAAA"))
        self.hass.data[backend.DOMAIN+"_radar"]=provider
        conn=Connection()
        await backend.ws_radar(self.hass,conn,{"id":1,"latitude":53.55,"longitude":10,"zoom":2})
        provider.get.assert_awaited_with("test-user",49.3806,8.3039,2,1)
        self.assertEqual(conn.results[-1][1]["location"]["via"],"home_wifi")
        await backend.ws_radar_image(self.hass,conn,{"id":2,"token":"opaque","kind":"frame","index":3})
        provider.image.assert_awaited_with("test-user","opaque","frame",3,background=False)
        provider.image.side_effect=backend.RadarUnavailable("Bild fehlt")
        await backend.ws_radar_image(self.hass,conn,{"id":3,"token":"opaque","kind":"frame","index":3})
        self.assertEqual(conn.errors[-1][1],"radar_unavailable")

    async def test_radar_does_not_block_on_reverse_geocoding(self):
        self.add_position("test-user","person.test","device_tracker.phone",53.55,10)
        provider=SimpleNamespace(get=AsyncMock(return_value={"status":"loading","basemap":{}}))
        self.hass.data[backend.DOMAIN+"_radar"]=provider
        conn=Connection()
        with patch.object(backend,"resolve_place",new_callable=AsyncMock) as resolve:
            await backend.ws_radar(self.hass,conn,{"id":1})
            resolve.assert_not_awaited()
        provider.get.assert_awaited_with("test-user",53.55,10.0,2,1)
        self.assertEqual(conn.results[-1][1]["location"]["name"],"Aktueller Standort")

    async def test_dwd_warnings_use_current_location_and_handle_outage(self):
        self.add_wifi_registry()
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        provider=SimpleNamespace(get=AsyncMock(return_value={"status":"ok","alerts":[]}))
        self.hass.data[backend.DOMAIN+"_warnings"]=provider
        conn=Connection()
        with patch.object(backend,"resolve_place",new_callable=AsyncMock) as resolve:
            await backend.ws_warnings(self.hass,conn,{"id":1,"latitude":53.55,"longitude":10})
            self.assertEqual(conn.results[-1][1]["location"]["via"],"home_wifi")
            provider.get.assert_awaited_with(49.3806,8.3039,"de")
            resolve.assert_not_awaited()
        provider.get.side_effect=backend.WarningsUnavailable("DWD offline")
        await backend.ws_warnings(self.hass,conn,{"id":2})
        self.assertIsNone(conn.results[-1][1]["warnings"])
        self.assertEqual(conn.results[-1][1]["warnings_error"],"DWD offline")
        self.assertIn("dwd.de",conn.results[-1][1]["source_url"])

    async def test_home_wifi_check_never_reads_gps_or_geocodes(self):
        self.add_wifi_registry()
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        with patch.object(backend,"user_position",side_effect=AssertionError("GPS must not be read")),patch.object(backend,"resolve_place",new_callable=AsyncMock) as geocode:
            conn=Connection()
            await backend.ws_network(self.hass,conn,{"id":1})
            self.assertTrue(conn.results[-1][1]["home_wifi"])
            await backend.ws_location(self.hass,conn,{"id":2})
            self.assertEqual(conn.results[-1][1]["location"]["via"],"home_wifi")
            geocode.assert_not_awaited()
        await backend.ws_sensors(self.hass,conn,{"id":3,"card_id":"any-card"})
        self.assertTrue(conn.results[-1][1]["home_wifi"])

    async def test_network_check_is_user_scoped_and_foreign_wifi_is_not_home(self):
        self.add_wifi_registry()
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        conn=Connection(user_id="other")
        await backend.ws_network(self.hass,conn,{"id":1})
        self.assertFalse(conn.results[-1][1]["home_wifi"])
        self.assertEqual(conn.results[-1][1]["wifi_sensors"],[])
        self.states["sensor.phone_ssid"].state="Hotel WiFi"
        conn=Connection()
        await backend.ws_network(self.hass,conn,{"id":2})
        self.assertFalse(conn.results[-1][1]["home_wifi"])

    async def test_home_router_presence_overrides_away_gps_and_needs_no_geocoder(self):
        self.add_position(latitude=53.55,longitude=10.0)
        self.states["person.test"].attributes["device_trackers"].append("device_tracker.router_phone")
        self.states["device_tracker.router_phone"]=SimpleNamespace(entity_id="device_tracker.router_phone",state="home",attributes={"source_type":"router"},last_updated=now)
        with patch.object(backend,"resolve_place",new_callable=AsyncMock) as resolve:
            conn=Connection()
            await backend.ws_location(self.hass,conn,{"id":1,"latitude":35.68,"longitude":139.69})
            self.assertTrue(conn.results[-1][1]["location"]["is_home"])
            self.assertEqual(conn.results[-1][1]["location"]["via"],"home_wifi")
            self.assertEqual(conn.results[-1][1]["location"]["name"],"Böhl-Iggelheim")
            resolve.assert_not_awaited()
        self.assertFalse(backend.on_home_wifi(self.hass,Connection(denied={"device_tracker.router_phone"})))
        self.assertFalse(backend.on_home_wifi(self.hass,Connection(user_id="other")))
        self.states["device_tracker.router_phone"].state="not_home"
        self.assertFalse(backend.on_home_wifi(self.hass,Connection()))
        self.assertEqual(backend.user_position(self.hass,Connection()),(53.55,10.0))

    async def test_ssid_is_matched_to_owned_device_and_explicit_home_network(self):
        self.add_wifi_registry()
        self.add_wifi_registry("other","person.other","device_tracker.other","sensor.other_ssid","other-phone",ssid="Home WiFi")
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        self.assertEqual([x["entity_id"] for x in backend.wifi_sensors(self.hass,Connection())],["sensor.phone_ssid"])
        self.assertTrue(backend.on_home_wifi(self.hass,Connection()))
        self.assertTrue(backend.on_home_wifi(self.hass,Connection(user_id="other")))
        self.assertFalse(backend.on_home_wifi(self.hass,Connection(denied={"sensor.phone_ssid"})))
        self.assertFalse(backend.on_home_wifi(self.hass,Connection(denied={"device_tracker.phone"})))
        self.states["sensor.phone_ssid"].state="Hotel WiFi"
        self.assertFalse(backend.on_home_wifi(self.hass,Connection()))
        for value in ("unknown","unavailable","Not Connected","<unknown ssid>"):
            self.states["sensor.phone_ssid"].state=value
            self.assertIsNone(backend.wifi_sensors(self.hass,Connection())[0]["ssid"])
        self.states["sensor.phone_ssid"].state="Home WiFi"
        entry=self.hass.registry.entities["sensor.phone_ssid"]
        entry.unique_id="webhook_wifi_connection"
        self.assertTrue(backend.on_home_wifi(self.hass,Connection()))
        entry.platform="unrelated_integration"
        self.assertFalse(backend.wifi_sensors(self.hass,Connection()))

    async def test_wifi_sensors_discovered_even_when_gps_is_unavailable(self):
        self.add_wifi_registry()
        self.states["device_tracker.phone"].state="unavailable"
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Home WiFi"]}
        self.assertTrue(backend.on_home_wifi(self.hass,Connection()))
        conn=Connection()
        await backend.ws_sensors(self.hass,conn,{"id":1,"card_id":"card"})
        self.assertEqual(conn.results[-1][1]["wifi_sensors"][0]["ssid"],"Home WiFi")
        with patch.object(backend,"resolve_place",new_callable=AsyncMock) as resolve:
            await backend.ws_location(self.hass,conn,{"id":2,"card_id":"card"})
            self.assertTrue(conn.results[-1][1]["location"]["is_home"])
            resolve.assert_not_awaited()

    async def test_home_ssids_are_global_admin_only_persistent_and_bounded(self):
        msg={"id":1,"home_ssids":["Home WiFi","Home WiFi","Home 5G"]}
        conn=Connection()
        await backend.ws_save_network(self.hass,conn,msg)
        self.assertEqual(conn.errors[-1][1],"unauthorized")
        await backend.ws_save_network(self.hass,Connection(admin=True),msg)
        expected=["Home WiFi","Home 5G"]
        self.assertEqual(self.hass.data[backend.DOMAIN+"_network_store"].value,{"home_ssids":expected})
        for card_id in ("card-a","card-b"):
            conn=Connection(user_id="other-user")
            await backend.ws_sensors(self.hass,conn,{"id":1,"card_id":card_id})
            self.assertEqual(conn.results[-1][1]["home_ssids"],expected)
        await backend.ws_save_card(self.hass,Connection(admin=True),{"id":2,"card_id":"other","title":"Test"})
        self.assertEqual(self.hass.data[backend.DOMAIN+"_network"]["home_ssids"],expected)
        self.assertNotIn("home_ssids",self.hass.data[backend.DOMAIN+"_settings"]["other"])
        conn=Connection(admin=True)
        await backend.ws_save_network(self.hass,conn,{"id":3,"home_ssids":[str(i) for i in range(21)]})
        self.assertEqual(conn.errors[-1][1],"invalid_wifi")
        self.assertEqual(self.hass.data[backend.DOMAIN+"_network"]["home_ssids"],expected)
        await backend.ws_save_network(self.hass,conn,{"id":4,"home_ssids":[]})
        self.assertEqual(self.hass.data[backend.DOMAIN+"_network"]["home_ssids"],[])

    async def test_failed_global_network_save_keeps_active_setting(self):
        self.hass.data[backend.DOMAIN+"_network"]={"home_ssids":["Existing"]}
        self.hass.data[backend.DOMAIN+"_network_store"].async_save=AsyncMock(side_effect=OSError("storage unavailable"))
        with self.assertRaises(OSError):
            await backend.ws_save_network(self.hass,Connection(admin=True),{"id":1,"home_ssids":["New"]})
        self.assertEqual(self.hass.data[backend.DOMAIN+"_network"]["home_ssids"],["Existing"])

    async def test_location_only_uses_current_users_permitted_gps(self):
        self.add_position()
        self.add_position("other-user","person.other","device_tracker.other",53.55,10.0)
        self.assertEqual(backend.user_position(self.hass,Connection()),(49.3806,8.3039))
        self.assertEqual(backend.user_position(self.hass,Connection(user_id="other-user")),(53.55,10.0))
        self.assertIsNone(backend.user_position(self.hass,Connection(user_id="unknown-user")))
        self.assertIsNone(backend.user_position(self.hass,Connection(denied={"person.test"})))
        self.assertIsNone(backend.user_position(self.hass,Connection(denied={"device_tracker.phone"})))
        self.assertIsNone(backend.user_position(self.hass,Connection(user_id=None)))

    async def test_location_uses_newest_valid_gps_over_router_source(self):
        self.add_position()
        self.states["person.test"].attributes["device_trackers"].append("device_tracker.new_phone")
        self.states["device_tracker.new_phone"] = SimpleNamespace(entity_id="device_tracker.new_phone",state="not_home",
            attributes={"source_type":"gps","latitude":53.55,"longitude":10.0},last_updated=now+timedelta(minutes=1))
        self.assertEqual(backend.user_position(self.hass,Connection()),(53.55,10.0))
        self.states["device_tracker.new_phone"].attributes["source_type"]="router"
        self.assertEqual(backend.user_position(self.hass,Connection()),(49.3806,8.3039))
        self.states["device_tracker.phone"].state="unavailable"
        self.assertIsNone(backend.user_position(self.hass,Connection()))
        self.states["person.test"].attributes.update(latitude=49.38,longitude=8.3)
        self.assertEqual(backend.user_position(self.hass,Connection()),(49.38,8.3))

    async def test_missing_and_invalid_location_do_not_guess_home_or_contact_geocoder(self):
        with patch.object(backend,"resolve_place",new_callable=AsyncMock) as resolve:
            conn=Connection()
            await backend.ws_location(self.hass,conn,{"id":1})
            self.assertFalse(conn.results[-1][1]["location"]["is_home"])
            self.assertFalse(conn.results[-1][1]["location"]["position_available"])
            self.assertIn("Kein GPS",conn.results[-1][1]["location_error"])
            for command in (backend.ws_location,backend.ws_forecast):
                for point in ({"latitude":91,"longitude":8},{"latitude":49},{"latitude":float("nan"),"longitude":8}):
                    await command(self.hass,conn,{"id":2,**point})
                    self.assertEqual(conn.errors[-1][1],"invalid_location")
            resolve.assert_not_awaited()

    async def test_location_passes_owned_gps_and_explicit_device_coordinates(self):
        self.add_position()
        lookup={"name":"Hamburg","resolved":True,"is_home":False,"position_available":True}
        with patch.object(backend,"resolve_place",new_callable=AsyncMock,return_value=lookup) as resolve:
            conn=Connection()
            await backend.ws_location(self.hass,conn,{"id":1})
            resolve.assert_awaited_with(self.hass,49.3806,8.3039)
            await backend.ws_location(self.hass,conn,{"id":2,"latitude":53.55001,"longitude":10})
            resolve.assert_awaited_with(self.hass,53.55,10.0)
            self.assertEqual(conn.results[-1][1],{"location":lookup,"location_error":None})
            lookup.update(name="Aktueller Standort",resolved=False)
            await backend.ws_location(self.hass,conn,{"id":3})
            self.assertIsNotNone(conn.results[-1][1]["location_error"])
            self.assertFalse(conn.results[-1][1]["location"]["is_home"])

    async def test_forecast_pool_isolates_places_and_updates_returned_place_metadata(self):
        def place(hass,lat,lon):
            return {"latitude":lat,"longitude":lon,"name":str(lat),"country_code":"de","postal_code":"67459" if lat<50 else "20095"}
        clients=[]
        def client(hass,location=None):
            obj=SimpleNamespace(location=location,get=AsyncMock(return_value={"location":location,"days":[]}))
            clients.append(obj)
            return obj
        with patch.object(backend,"resolve_place",new_callable=AsyncMock,side_effect=place),patch.object(backend,"ForecastClient",side_effect=client):
            conn=Connection()
            for latitude in (49.3806,53.55,49.38061):
                await backend.ws_forecast(self.hass,conn,{"id":1,"latitude":latitude,"longitude":8.3})
            self.assertEqual(len(clients),2)
            self.assertEqual(clients[0].get.await_count,2)
            self.assertEqual(clients[1].get.await_count,1)
            self.assertEqual(conn.results[-1][1]["forecast"]["location"]["latitude"],49.3806)

    async def test_query_converts_existing_temperature(self):
        await self.manager.load()
        self.manager.archive.start(now.timestamp()-3600, 10)
        data = await self.manager.analyse({"start_date":"2026-11-17", "end_date":"2026-11-17"})
        self.assertEqual(data["current"], 10)
        self.assertEqual(data["summary"]["mean"], 10)
        self.assertEqual(data["summary"]["exact_seconds"], 3600)
        self.assertEqual(data["unit"], "°C")
        self.assertNotIn("heating_degree_days", data["summary"])

    async def test_wind_converts_to_kmh(self):
        manager = await backend.ensure_manager(self.hass, "sensor.wind", "wind")
        manager.statistics = AsyncMock(return_value=[])
        data = await manager.analyse({"start_date":"2026-11-17", "end_date":"2026-11-17"})
        self.assertEqual(data["current"], 18)
        self.assertEqual(data["kind"], "wind")
        self.assertEqual(data["unit"], "km/h")

    async def test_permission_denied_before_history_query(self):
        conn = Connection(denied={"sensor.test"})
        await backend.ws_analyse(self.hass, conn, {"id":1, "entity_id":"sensor.test"})
        self.assertEqual(conn.errors[0][1], "unauthorized")
        self.manager.statistics.assert_not_awaited()
        self.history_read.assert_not_called()

    async def test_sensor_list_includes_unconfigured_and_filters_types_and_permissions(self):
        self.hass.data[backend.DOMAIN+"_settings"]["card"] = {
            "entities":["sensor.test","sensor.second"], "entity":"sensor.test", "wind_entity":"sensor.wind"}
        conn = Connection(denied={"sensor.test","sensor.wind"})
        await backend.ws_sensors(self.hass, conn, {"id":1,"card_id":"card"})
        result = conn.results[0][1]
        self.assertEqual([s["entity_id"] for s in result["sensors"]], ["sensor.second"])
        self.assertEqual(result["wind_sensors"], [])
        self.assertEqual(result["settings"]["entities"], ["sensor.second"])
        self.assertEqual(result["settings"]["entity"], "sensor.second")
        self.assertNotIn("wind_entity", result["settings"])

    async def test_custom_weather_units_are_discovered_saved_and_converted(self):
        self.states["sensor.illumination"] = state("sensor.illumination", "1234", "Lux", "")
        self.states["sensor.anemometer"] = state("sensor.anemometer", "5", " km / h ", "")
        conn = Connection(admin=True)
        await backend.ws_sensors(self.hass, conn, {"id":1,"card_id":"custom"})
        result = conn.results[-1][1]
        self.assertIn("sensor.illumination", [sensor["entity_id"] for sensor in result["illuminance_sensors"]])
        self.assertIn("sensor.anemometer", [sensor["entity_id"] for sensor in result["wind_sensors"]])
        await backend.ws_save_card(self.hass, conn, {"id":2,"card_id":"custom","title":"Test",
            "wind_entities":["sensor.anemometer"],"illuminance_entities":["sensor.illumination"]})
        self.assertFalse(conn.errors)
        managers = {manager.entity:manager for manager in self.hass.data[backend.DOMAIN].values()}
        self.assertEqual(managers["sensor.illumination"].state_value(),1234)
        self.assertEqual(managers["sensor.anemometer"].state_value(),5)

    async def test_only_admin_can_save_multiple_sensors(self):
        msg = {"id":1,"card_id":"card","entities":["sensor.test","sensor.second"],
               "entity":"sensor.second","wind_entity":"sensor.wind","illuminance_entity":"sensor.lux","title":"Test"}
        conn = Connection()
        await backend.ws_save_card(self.hass, conn, msg)
        self.assertEqual(conn.errors[0][1], "unauthorized")
        await backend.ws_save_card(self.hass, Connection(admin=True), msg)
        saved = self.hass.data[backend.DOMAIN+"_settings"]["card"]
        self.assertEqual(saved["entities"], ["sensor.test","sensor.second"])
        self.assertEqual(saved["wind_entity"], "sensor.wind")
        self.assertEqual(len(self.hass.data[backend.DOMAIN]), 4)

    async def test_sensor_aliases_are_trimmed_scoped_and_persisted_per_card(self):
        msg = {"id":1,"card_id":"card-a","entities":["sensor.test","sensor.second"],
               "entity":"sensor.test","title":"Weather Analysis", "sensor_names":{
                   "sensor.test":"  Terrasse  ", "sensor.second":"", "sensor.humidity":"Hidden"}}
        await backend.ws_save_card(self.hass, Connection(admin=True), msg)
        self.assertEqual(self.hass.data[backend.DOMAIN+"_settings"]["card-a"]["sensor_names"],
                         {"sensor.test":"Terrasse"})
        await backend.ws_save_card(self.hass, Connection(admin=True), {**msg,"card_id":"card-b",
            "sensor_names":{"sensor.test":"Andere Karte"}})
        self.assertEqual(self.hass.data[backend.DOMAIN+"_settings"]["card-a"]["sensor_names"]["sensor.test"], "Terrasse")
        self.assertEqual(self.hass.data[backend.DOMAIN+"_settings"]["card-b"]["sensor_names"]["sensor.test"], "Andere Karte")
        self.assertEqual(self.states["sensor.test"].name,"sensor.test")

    async def test_sensor_aliases_follow_read_permissions(self):
        self.hass.data[backend.DOMAIN+"_settings"]["card"] = {"entities":["sensor.test","sensor.second"],
            "entity":"sensor.test", "sensor_names":{"sensor.test":"Private name","sensor.second":"Visible name"}}
        conn=Connection(denied={"sensor.test"})
        await backend.ws_sensors(self.hass,conn,{"id":1,"card_id":"card"})
        self.assertEqual(conn.results[0][1]["settings"]["sensor_names"],{"sensor.second":"Visible name"})

    def add_secondary_sensors(self):
        self.states["sensor.wind2"] = state("sensor.wind2", "8", "m/s", "wind_speed")
        self.states["sensor.lux2"] = state("sensor.lux2", "2500", "lx", "illuminance")

    async def test_all_sensor_kinds_support_multiple_selections_and_aliases(self):
        self.add_secondary_sensors()
        conn=Connection(admin=True)
        await backend.ws_save_card(self.hass,conn,{"id":1,"card_id":"multi","entities":[],
            "wind_entities":["sensor.wind","sensor.wind2"],"wind_entity":"sensor.wind2",
            "illuminance_entities":["sensor.lux","sensor.lux2"],"title":"Weather Analysis",
            "sensor_names":{"sensor.wind2":"Dach","sensor.lux2":"Garten"}})
        saved=conn.results[0][1]
        self.assertEqual(saved["wind_entities"],["sensor.wind","sensor.wind2"])
        self.assertEqual(saved["wind_entity"],"sensor.wind2")
        self.assertEqual(saved["illuminance_entities"],["sensor.lux","sensor.lux2"])
        self.assertEqual(saved["sensor_names"],{"sensor.wind2":"Dach","sensor.lux2":"Garten"})
        self.assertEqual(len(self.hass.data[backend.DOMAIN]),5)

    async def test_legacy_wind_and_light_selections_are_expanded_on_read(self):
        self.hass.data[backend.DOMAIN+"_settings"]["old"]={"wind_entity":"sensor.wind","illuminance_entity":"sensor.lux"}
        conn=Connection()
        await backend.ws_sensors(self.hass,conn,{"id":1,"card_id":"old"})
        saved=conn.results[0][1]["settings"]
        self.assertEqual(saved["wind_entities"],["sensor.wind"])
        self.assertEqual(saved["illuminance_entities"],["sensor.lux"])

    async def test_empty_new_list_clears_old_singular_selection(self):
        conn=Connection(admin=True)
        await backend.ws_save_card(self.hass,conn,{"id":1,"card_id":"clear","entities":[],
            "wind_entities":[],"wind_entity":"sensor.wind","title":"Weather Analysis",
            "sensor_names":{"sensor.wind":"Hidden"}})
        self.assertEqual(conn.results[0][1]["wind_entities"],[])
        self.assertEqual(conn.results[0][1]["wind_entity"],"")
        self.assertEqual(conn.results[0][1]["sensor_names"],{})

    async def test_lists_reject_wrong_kinds_before_saving(self):
        conn=Connection(admin=True)
        await backend.ws_save_card(self.hass,conn,{"id":1,"card_id":"bad",
            "wind_entities":["sensor.test"],"title":"Weather Analysis"})
        self.assertEqual(conn.errors[0][1],"invalid_sensor")
        self.assertNotIn("bad",self.hass.data[backend.DOMAIN+"_settings"])

    async def test_all_wind_and_light_sensors_restart_without_a_dashboard(self):
        self.add_secondary_sensors()
        self.hass.data[backend.DOMAIN].clear()
        self.hass.data[backend.DOMAIN+"_settings"]["multi"]={"wind_entities":["sensor.wind","sensor.wind2"],
            "illuminance_entities":["sensor.lux","sensor.lux2"]}
        await backend.async_setup_entry(self.hass,SimpleNamespace(entry_id="service",data={}))
        self.assertEqual({m.entity for m in self.hass.data[backend.DOMAIN].values()},
                         {"sensor.wind","sensor.wind2","sensor.lux","sensor.lux2"})

    async def test_history_import_includes_every_selected_sensor_kind(self):
        self.add_secondary_sensors()
        self.hass.data[backend.DOMAIN+"_settings"]["multi"]={"wind_entities":["sensor.wind","sensor.wind2"],
            "illuminance_entities":["sensor.lux","sensor.lux2"]}
        conn=Connection(admin=True)
        await backend.ws_import_history(self.hass,conn,{"id":1,"card_id":"multi"})
        self.assertEqual(conn.results[0][1],{"count":4,"failed":[]})

    async def test_save_rejects_wrong_sensor_kind_without_partial_changes(self):
        conn = Connection(admin=True)
        await backend.ws_save_card(self.hass, conn, {"id":1,"card_id":"card",
            "entities":["sensor.test"],"wind_entity":"sensor.second","title":"Test"})
        self.assertEqual(conn.errors[0][1], "invalid_sensor")
        self.assertEqual(self.hass.data[backend.DOMAIN+"_settings"], {})

    async def test_unconfigured_sensor_is_analyzed_directly(self):
        conn = Connection()
        with patch.object(backend.Manager, "analyse", new=AsyncMock(return_value={"current":5})):
            await backend.ws_analyse(self.hass, conn, {"id":1,"entity_id":"sensor.second"})
        self.assertEqual(conn.results[0][1]["current"], 5)
        self.assertEqual(len(self.hass.data[backend.DOMAIN]), 2)

    async def test_illuminance_sensor_is_independent_and_uses_lux(self):
        manager = await backend.ensure_manager(self.hass, "sensor.lux", "illuminance")
        manager.statistics = AsyncMock(return_value=[])
        data = await manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17"})
        self.assertEqual(data["current"], 1234)
        self.assertEqual(data["unit"], "lx")
        self.assertEqual(data["kind"], "illuminance")

    async def test_history_reimport_keeps_previously_imported_purged_hours(self):
        previous = backend.Archive(); previous.start(0,-2); previous.advance(3600)
        await self.manager.load()
        self.manager.history = previous
        self.history_read.return_value = backend.Archive()
        await self.manager.import_history(force=True)
        self.assertEqual(self.manager.history.hours["0"]["seconds"],3600)

    async def test_import_history_is_admin_only(self):
        conn = Connection()
        await backend.ws_import_history(self.hass, conn, {"id":1,"card_id":"card"})
        self.assertEqual(conn.errors[0][1], "unauthorized")

    async def test_unknown_sensor_is_rejected(self):
        conn = Connection()
        await backend.ws_analyse(self.hass, conn, {"id":1,"entity_id":"sensor.other"})
        self.assertEqual(conn.errors[0][1], "invalid_sensor")

    async def test_parallel_card_queries_share_one_manager(self):
        a, b = await asyncio.gather(backend.ensure_manager(self.hass,"sensor.second"),
                                    backend.ensure_manager(self.hass,"sensor.second"))
        self.assertIs(a, b)
        self.assertEqual(len(self.hass.data[backend.DOMAIN]), 2)

    async def test_initial_history_is_used_and_persisted_without_double_counting(self):
        raw = backend.Archive()
        raw.start(now.timestamp()-7200, -2)
        raw.change(now.timestamp()-3600, 10)
        raw.advance(now.timestamp())
        self.history_read.return_value = raw
        await self.manager.load()
        data = await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17"})
        self.assertEqual(data["summary"]["frost_hours"], 1)
        self.assertEqual(data["summary"]["mean"], 4)
        self.assertEqual(data["trends"]["hour"], 0)
        self.assertTrue(self.manager.dump()["history_imported"])
        await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17"})
        self.assertEqual(self.history_read.call_count, 1)
        self.assertEqual(data["summary"]["exact_seconds"], 7200)

    async def test_requested_chart_resolutions_keep_summary_and_exact_detail(self):
        raw=backend.Archive();first=now.timestamp()-7200;raw.start(first,0);raw.change(first+450,20);raw.advance(now.timestamp())
        self.history_read.return_value=raw
        await self.manager.load()
        expected=None
        for interval in (900,3600,10800,21600):
            data=await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17","chart_interval":interval})
            self.assertEqual(data["chart_interval"],interval)
            self.assertTrue(all(point["resolution"]==interval for point in data["chart"]))
            if expected is None:expected=data["summary"]
            self.assertEqual(data["summary"],expected)
        self.assertEqual(self.manager.dump()["history_resolution"],900)
        self.assertTrue(self.manager.dump()["history"]["quarters"])
        with self.assertRaises(ValueError):
            await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17","chart_interval":1200})

    async def test_upgrade_backfills_quarters_without_overlapping_old_live_hours(self):
        old=backend.Archive();old.start(now.timestamp()-86400,5);old.advance(now.timestamp())
        stored=old.dump();stored.pop("quarters");stored["history"]={"hours":{}};stored["history_imported"]=True
        self.manager.store.value=stored
        detail=backend.Archive();detail.start(now.timestamp()-3600,0);detail.change(now.timestamp()-1800,10);detail.advance(now.timestamp())
        self.history_read.side_effect=lambda first,last:detail if last>now.timestamp()-86400 else backend.Archive()
        await self.manager.load()
        self.assertEqual(self.history_read.call_count,2)
        self.assertEqual(self.manager.history.hours,{})
        data=await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17","chart_interval":900})
        self.assertEqual([p["mean"] for p in data["chart"] if p["resolution"]==900],[0,0,10,10])
        self.assertEqual(data["summary"]["mean"],5)
        self.assertTrue(data["chart_fallback"])
        self.assertLessEqual(data["summary"]["coverage"],1)
        await self.manager.import_history()
        self.assertEqual(self.history_read.call_count,2)

    async def test_sensor_order_is_preserved_for_every_kind(self):
        self.add_secondary_sensors()
        message={"id":1,"card_id":"ordered","title":"Test","entities":["sensor.second","sensor.test"],
                 "wind_entities":["sensor.wind2","sensor.wind"],"illuminance_entities":["sensor.lux2","sensor.lux"]}
        connection=Connection(admin=True)
        await backend.ws_save_card(self.hass,connection,message)
        await backend.ws_sensors(self.hass,connection,{"id":2,"card_id":"ordered"})
        saved=connection.results[-1][1]["settings"]
        for key in ("entities","wind_entities","illuminance_entities"):
            self.assertEqual(saved[key],message[key])

    async def test_current_day_uses_full_today_and_clips_real_values(self):
        reference=datetime(2026,11,18,5,40,25,tzinfo=timezone.utc)
        first=datetime(2026,11,17,23,tzinfo=timezone.utc).timestamp()
        raw=backend.Archive();raw.start(first-3600,100);raw.change(first,0);raw.change(first+3600,10);raw.advance(reference.timestamp())
        self.history_read.return_value=raw
        with patch.object(backend.dt_util,"utcnow",return_value=reference):
            await self.manager.load()
            data=await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-18","chart_interval":900,"window":"day","as_of":reference.timestamp()})
        self.assertEqual(data["start"],first)
        self.assertEqual(data["display_end"],datetime(2026,11,18,23,tzinfo=timezone.utc).timestamp())
        self.assertEqual(data["display_end"]-data["start"],86400)
        self.assertEqual(data["end"],reference.timestamp())
        self.assertAlmostEqual(data["summary"]["mean"],10*(data["end"]-first-3600)/(data["end"]-first))
        self.assertEqual(data["summary"]["max"],10)
        self.assertEqual(data["summary"]["hot_hours"],0)
        self.assertEqual(data["chart"][0]["start"],first)
        self.assertTrue(all(first<=point["start"]<point["end"]<=reference.timestamp() for point in data["chart"]))

    async def test_live_week_contains_today_and_seven_previous_days(self):
        reference=datetime(2026,11,18,5,40,25,tzinfo=timezone.utc)
        with patch.object(backend.dt_util,"utcnow",return_value=reference):
            await self.manager.load()
            data=await self.manager.analyse({"start_date":"2026-11-11","end_date":"2026-11-18","chart_interval":3600,"window":"week","as_of":reference.timestamp()})
        self.assertEqual(data["start"],datetime(2026,11,10,23,tzinfo=timezone.utc).timestamp())
        self.assertEqual(data["display_end"],datetime(2026,11,18,5,41,tzinfo=timezone.utc).timestamp())
        self.assertEqual(data["window"],"week")

    async def test_full_calendar_axes_preserve_today_week_and_month_without_future_values(self):
        reference=datetime(2026,11,18,5,40,25,tzinfo=timezone.utc)
        with patch.object(backend.dt_util,"utcnow",return_value=reference):
            await self.manager.load()
            for first,last,expected in [("2026-11-18","2026-11-18",datetime(2026,11,18,23,tzinfo=timezone.utc)),("2026-11-16","2026-11-22",datetime(2026,11,22,23,tzinfo=timezone.utc)),("2026-11-01","2026-11-30",datetime(2026,11,30,23,tzinfo=timezone.utc))]:
                data=await self.manager.analyse({"start_date":first,"end_date":last,"chart_interval":900})
                self.assertEqual(data["display_end"],expected.timestamp())
                self.assertEqual(data["end"],reference.timestamp())
                self.assertTrue(all(point["end"]<=reference.timestamp() for point in data["chart"]))
                self.assertIsNone(data["window"])

    async def test_current_day_follows_calendar_day_across_dst(self):
        for reference in [datetime(2026,3,29,5,40,25,tzinfo=timezone.utc),datetime(2026,10,25,5,40,25,tzinfo=timezone.utc)]:
            with patch.object(backend.dt_util,"utcnow",return_value=reference):
                await self.manager.load()
                key=reference.date().isoformat()
                data=await self.manager.analyse({"start_date":key,"end_date":key,"chart_interval":900,"window":"day","as_of":reference.timestamp()})
                self.assertEqual(data["display_end"]-data["start"],(23 if reference.month==3 else 25)*3600)

    async def test_invalid_live_window_parameters_are_rejected(self):
        for extra in [{"window":"year"},{"window":"day","as_of":float("nan")},{"window":"day","as_of":now.timestamp()+3600},{"window":"day","as_of":-1}]:
            with self.assertRaises(ValueError):
                await self.manager.analyse({"start_date":"2026-11-17","end_date":"2026-11-17",**extra})

    async def test_dashboard_has_current_values_and_extremes_only_from_today(self):
        today=now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(hours=1)
        raw=backend.Archive();raw.start(today.timestamp()-3600,-99);raw.change(today.timestamp(),0);raw.change(today.timestamp()+3600,10);raw.advance(now.timestamp())
        self.history_read.return_value=raw
        connection=Connection()
        await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","wind_entity":"sensor.wind","illuminance_entity":"sensor.lux"})
        data=connection.results[-1][1]
        self.assertEqual(data["date"],"2026-11-17")
        self.assertEqual(data["sensors"]["temperature"]["current"],10)
        self.assertEqual((data["sensors"]["temperature"]["min"],data["sensors"]["temperature"]["max"]),(0,10))
        self.assertEqual(data["sensors"]["wind"]["current"],18)
        self.assertEqual(data["sensors"]["illuminance"]["current"],1234)
        self.assertEqual(data["errors"],{})
        self.assertNotIn(backend.DOMAIN+"_forecast",self.hass.data)

    async def test_weather_intervals_use_real_three_hour_sensor_integrals(self):
        first=datetime(2026,11,16,23,tzinfo=timezone.utc).timestamp()
        def history(manager,start,end):
            high={"temperature":12,"wind":18,"illuminance":900}[manager.kind]
            raw=backend.Archive();raw.start(first,0);raw.change(first+3600,high);raw.advance(now.timestamp())
            return raw
        self.history_patch.stop()
        with patch.object(backend.Manager,"read_history",autospec=True,side_effect=history):
            connection=Connection()
            await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","wind_entity":"sensor.wind","illuminance_entity":"sensor.lux","as_of":now.timestamp()})
        data=connection.results[-1][1]
        first_slot=data["intervals"][0]
        self.assertEqual((first_slot["start"],first_slot["end"]),(first,first+10800))
        self.assertEqual(first_slot["temperature"],8)
        self.assertEqual((first_slot["temperature_min"],first_slot["temperature_max"]),(0,12))
        self.assertEqual(first_slot["wind_speed"],12)
        self.assertEqual(first_slot["illuminance"],600)
        self.assertEqual(data["intervals"][-1]["end"],now.timestamp())
        self.assertTrue(data["intervals"][-1]["partial"])
        self.assertTrue(all(slot["end"]<=data["as_of"] for slot in data["intervals"]))
        self.assertEqual([hour["temperature"] for hour in first_slot["hours"]],[0,12,12])
        self.assertEqual([hour["wind_speed"] for hour in first_slot["hours"]],[0,18,18])
        self.assertTrue(all(hour["start"]>=slot["start"] and hour["end"]<=slot["end"] and hour["end"]-hour["start"]<=3600 for slot in data["intervals"] for hour in slot["hours"]))

    async def test_weather_hourly_details_preserve_missing_hours_and_snapshot(self):
        first=datetime(2026,11,16,23,tzinfo=timezone.utc).timestamp()
        raw=backend.Archive();raw.start(first,3);raw.change(first+3600,None);raw.change(first+7200,15);raw.advance(now.timestamp())
        self.history_read.return_value=raw
        connection=Connection()
        await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","as_of":now.timestamp()})
        slots=connection.results[-1][1]["intervals"]
        self.assertEqual([hour["temperature"] for hour in slots[0]["hours"]],[3,None,15])
        self.assertEqual(slots[-1]["hours"][-1]["end"],now.timestamp())
        self.assertEqual(self.history_read.call_count,1,"Hourly detail reuses the same history read")

    async def test_weather_hourly_details_cover_dst_days_in_real_hours(self):
        for reference,day_hours in [(datetime(2026,3,29,21,59,59,tzinfo=timezone.utc),23),(datetime(2026,10,25,22,59,59,tzinfo=timezone.utc),25)]:
            self.manager.history_imported=True
            self.manager.history=backend.Archive();self.manager.archive=backend.Archive()
            with patch.object(backend.dt_util,"utcnow",return_value=reference):
                connection=Connection();await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","as_of":reference.timestamp()})
            hours=[hour for slot in connection.results[-1][1]["intervals"] for hour in slot["hours"]]
            self.assertEqual(len(hours),day_hours)
            self.assertTrue(all(0<h["end"]-h["start"]<=3600 for h in hours))
            self.assertTrue(all(a["end"]==b["start"] for a,b in zip(hours,hours[1:])))

    async def test_weather_snapshot_excludes_changes_after_the_requested_boundary(self):
        first=datetime(2026,11,16,23,tzinfo=timezone.utc).timestamp();snapshot=now.timestamp()-60
        raw=backend.Archive();raw.start(first,10);raw.change(snapshot+30,99);raw.advance(now.timestamp())
        self.history_read.return_value=raw
        connection=Connection()
        await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","as_of":snapshot})
        data=connection.results[-1][1]
        self.assertEqual(data["as_of"],snapshot)
        self.assertEqual(data["sensors"]["temperature"]["max"],10)
        self.assertEqual(data["intervals"][-1]["end"],snapshot)
        self.assertEqual(data["intervals"][-1]["temperature"],10)
        self.assertTrue(all(hour["end"]<=snapshot for slot in data["intervals"] for hour in slot["hours"]))

    async def test_weather_rejects_invalid_snapshot_without_querying_history(self):
        for value in (float("nan"),now.timestamp()+3600,-1,True):
            connection=Connection()
            await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test","as_of":value})
            self.assertEqual(connection.errors[-1][1],"invalid_range")
        self.history_read.assert_not_called()

    async def test_dashboard_denied_sensor_never_queries_history(self):
        connection=Connection(denied={"sensor.test"})
        await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.test"})
        data=connection.results[-1][1]
        self.assertEqual(data["sensors"],{})
        self.assertIn("temperature",data["errors"])
        self.history_read.assert_not_called()

    async def test_dashboard_isolates_wrong_kind_and_missing_selections(self):
        connection=Connection()
        await backend.ws_dashboard(self.hass,connection,{"id":1,"temperature_entity":"sensor.wind","wind_entity":"sensor.wind"})
        data=connection.results[-1][1]
        self.assertNotIn("temperature",data["sensors"])
        self.assertIn("temperature",data["errors"])
        self.assertEqual(data["sensors"]["wind"]["current"],18)
        await backend.ws_dashboard(self.hass,connection,{"id":2})
        self.assertEqual(connection.results[-1][1]["sensors"],{})

    async def test_forecast_failure_is_explicit_and_independent_of_dashboard(self):
        self.hass.data[backend.DOMAIN+"_forecast"]=SimpleNamespace(get=AsyncMock(side_effect=backend.ForecastUnavailable("Offline")))
        connection=Connection()
        await backend.ws_forecast(self.hass,connection,{"id":1})
        self.assertIsNone(connection.results[-1][1]["forecast"])
        self.assertEqual(connection.results[-1][1]["forecast_error"],"Offline")
        await backend.ws_dashboard(self.hass,connection,{"id":2,"wind_entity":"sensor.wind"})
        self.assertEqual(connection.results[-1][1]["sensors"]["wind"]["current"],18)

    async def test_invalid_ranges_rejected(self):
        for first, last in [("2025-01-01","2026-11-17"),("2027-01-01","2027-01-01"),("2026-11-17","2026-11-16")]:
            with self.assertRaises(ValueError):
                await self.manager.analyse({"start_date":first,"end_date":last})

    async def test_legacy_archive_key_is_retained(self):
        self.hass.config_entries.async_entries = lambda domain:[
            SimpleNamespace(data={"entity_id":"sensor.second"},entry_id="old-entry")]
        manager = await backend.ensure_manager(self.hass,"sensor.second")
        self.assertEqual(manager.store.key, "weather_analysis.old-entry")

    async def test_saved_card_sensors_restart_without_open_dashboard(self):
        self.hass.data[backend.DOMAIN].clear()
        self.hass.data[backend.DOMAIN+"_settings"]["card"] = {
            "entities":["sensor.test","sensor.second"],"wind_entity":"sensor.wind"}
        entry = SimpleNamespace(entry_id="service",data={})
        await backend.async_setup_entry(self.hass, entry)
        self.assertEqual(len(self.hass.data[backend.DOMAIN]), 3)
        await backend.async_unload_entry(self.hass, entry)
        self.assertEqual(self.hass.data[backend.DOMAIN], {})

    async def test_state_event_uses_own_snapshot(self):
        await self.manager.load()
        self.manager.state_changed(SimpleNamespace(time_fired=now,
            data={"new_state":state("sensor.test","0","°C","temperature")}))
        self.assertEqual(self.manager.archive.value, 0)


if __name__ == "__main__":
    unittest.main()
