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
       Schema=Schema, All=Schema, Coerce=Schema, Range=Schema, Length=Schema)
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
    def __init__(self, admin=False, denied=()):
        self.user = SimpleNamespace(is_admin=admin, permissions=SimpleNamespace(
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
            states=SimpleNamespace(get=self.states.get, async_all=lambda domain:list(self.states.values())),
            config_entries=SimpleNamespace(async_entries=lambda domain:[]),
            bus=SimpleNamespace(async_listen_once=lambda *args:lambda:None),
            recorder=SimpleNamespace(keep_days=10, async_add_executor_job=executor),
            data={backend.DOMAIN:{}, backend.DOMAIN+"_settings":{},
                  backend.DOMAIN+"_store":Store(), backend.DOMAIN+"_lock":asyncio.Lock(),
                  backend.DOMAIN+"_entries":set()})
        self.history_patch = patch.object(backend.Manager, "read_history", return_value=backend.Archive())
        self.history_read = self.history_patch.start()
        self.addCleanup(self.history_patch.stop)
        self.manager = backend.Manager(self.hass, SimpleNamespace(data={"entity_id":"sensor.test"}, entry_id="entry"))
        self.manager.statistics = AsyncMock(return_value=[])
        self.hass.data[backend.DOMAIN]["entry"] = self.manager

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
        self.assertNotIn("entity", result["settings"])
        self.assertNotIn("wind_entity", result["settings"])

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
