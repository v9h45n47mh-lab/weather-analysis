"""Weather Analysis: recorder-backed card and persistent temperature integrals."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
from hashlib import sha256
from types import SimpleNamespace
import logging
import math
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.db_schema import RecorderRuns
from homeassistant.components.recorder.util import session_scope
from homeassistant.core import callback
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.recorder import get_instance
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .radar import RadarClient, RadarUnavailable
from .forecast import ForecastClient, ForecastUnavailable
from .location import LocationClient, coordinates, fallback, home_location
from .warnings import WarningsClient, WarningsUnavailable, SOURCE_URL as DWD_SOURCE_URL

from .analytics import (Archive, sensor_kind, sensor_value, combine_hours,
                        history_archive, merge_hours, summarize, resolution_chart)

DOMAIN = "weather_analysis"
VERSION = "1.15.0"
_LOGGER = logging.getLogger(__name__)
SENSOR_FIELDS = {"temperature": ("entities", "entity"), "wind": ("wind_entities", "wind_entity"),
                 "illuminance": ("illuminance_entities", "illuminance_entity")}


def configured_entities(settings, kind):
    """Read sensor lists while retaining v1.3 singular wind/light selections."""
    plural, single = SENSOR_FIELDS[kind]
    values = settings.get(plural, [settings[single]] if settings.get(single) else [])
    return list(dict.fromkeys(values))


async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN + "_entries"] = set()
    hass.data[DOMAIN + "_lock"] = asyncio.Lock()
    settings_store = Store(hass, 1, DOMAIN + ".cards")
    hass.data[DOMAIN + "_settings"] = await settings_store.async_load() or {}
    hass.data[DOMAIN + "_store"] = settings_store
    network_store=Store(hass,1,DOMAIN+".network")
    hass.data[DOMAIN+"_network"] = await network_store.async_load() or {"home_ssids":[]}
    hass.data[DOMAIN+"_network_store"] = network_store
    hass.data[DOMAIN+"_network_lock"] = asyncio.Lock()
    await hass.http.async_register_static_paths([
        StaticPathConfig("/weather-analysis", str(Path(__file__).parent / "frontend"), False)
    ])
    frontend.add_extra_js_url(hass, f"/weather-analysis/weather-analysis-card.js?v={VERSION}")
    for command in (ws_sensors, ws_analyse, ws_save_card, ws_import_history, ws_dashboard, ws_forecast, ws_location, ws_save_network, ws_network, ws_warnings, ws_radar, ws_radar_image):
        websocket_api.async_register_command(hass, command)
    return True


async def ensure_manager(hass, entity, kind=None):
    """Create each selected sensor once; preserve the original v1.0 archive key."""
    async with hass.data[DOMAIN + "_lock"]:
        manager = next((m for m in hass.data[DOMAIN].values() if m.entity == entity), None)
        if manager is not None:
            return manager
        legacy = next((e for e in hass.config_entries.async_entries(DOMAIN)
                       if e.data.get("entity_id") == entity), None)
        entry = legacy or SimpleNamespace(data={"entity_id": entity},
            entry_id="sensor_" + sha256(entity.encode()).hexdigest()[:24])
        manager = Manager(hass, entry, kind)
        await manager.load()
        hass.data[DOMAIN][entry.entry_id] = manager
        return manager


async def async_setup_entry(hass, entry):
    hass.data[DOMAIN + "_entries"].add(entry.entry_id)
    if not entry.data.get("entity_id") and getattr(entry, "title", None) in ("Temperaturanalyse", "Wetteranalyse"):
        hass.config_entries.async_update_entry(entry, title="Weather Analysis")
    if entry.data.get("entity_id"):
        await ensure_manager(hass, entry.data["entity_id"], "temperature")
    for settings in hass.data[DOMAIN + "_settings"].values():
        for kind in SENSOR_FIELDS:
            for entity in configured_entities(settings, kind):
                await ensure_manager(hass, entity, kind)
    entry.runtime_data = hass.data[DOMAIN]
    return True


async def async_unload_entry(hass, entry):
    hass.data[DOMAIN + "_entries"].discard(entry.entry_id)
    if not hass.data[DOMAIN + "_entries"]:
        for manager in list(hass.data[DOMAIN].values()):
            for unsubscribe in manager.unsubscribers:
                unsubscribe()
            await manager.stop()
        hass.data[DOMAIN].clear()
    return True


def may_read(connection, entity):
    return connection.user.permissions.check_entity(entity, POLICY_READ)


class Manager:
    def __init__(self, hass, entry, kind=None):
        self.hass = hass
        self.entity = entry.data["entity_id"]
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        state = hass.states.get(self.entity)
        self.kind = kind or (sensor_kind(self.entity, state.attributes) if state else None) or "temperature"
        self.history = Archive()
        self.history_imported = False
        self.archive = Archive()
        self.cache = {}
        self.semaphore = asyncio.Semaphore(2)

    def state_value(self):
        state = self.hass.states.get(self.entity)
        return sensor_value(state.state, state.attributes.get("unit_of_measurement"), self.kind) if state else None

    async def load(self):
        stored = await self.store.async_load() or {}
        self.archive = Archive(stored)
        self.history = Archive(stored.get("history"))
        self.history_imported = stored.get("history_imported", False) and stored.get("history_resolution") == 900
        self.archive.start(dt_util.utcnow().timestamp(), self.state_value())
        self.unsubscribers = [
            async_track_state_change_event(self.hass, [self.entity], self.state_changed),
            async_track_time_interval(self.hass, self.pulse, timedelta(minutes=1)),
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop),
        ]
        await self.import_history()
        self.store.async_delay_save(self.dump, 10)

    @callback
    def state_changed(self, event):
        state = event.data.get("new_state")
        value = sensor_value(state.state, state.attributes.get("unit_of_measurement"), self.kind) if state else None
        self.archive.change(event.time_fired.timestamp(), value)
        self.cache.clear()
        self.store.async_delay_save(self.dump, 10)

    async def pulse(self, now=None):
        self.archive.advance(dt_util.utcnow().timestamp())
        self.store.async_delay_save(self.dump, 10)

    async def stop(self, event=None):
        self.archive.advance(dt_util.utcnow().timestamp())
        await self.store.async_save(self.dump())

    def dump(self):
        return {**self.archive.dump(), "history": self.history.dump(),
                "history_imported": self.history_imported, "history_resolution": 900, "kind": self.kind}

    def read_history(self, first, last):
        """Read retained raw states and recording intervals in the recorder executor."""
        if first >= last:
            return Archive()
        start = datetime.fromtimestamp(first, dt_util.UTC)
        end = datetime.fromtimestamp(last, dt_util.UTC)
        rows = get_significant_states(self.hass, start, end, [self.entity],
            include_start_time_state=True, significant_changes_only=False,
            minimal_response=False, no_attributes=False).get(self.entity, [])
        with session_scope(hass=self.hass, read_only=True) as session:
            runs = session.query(RecorderRuns).filter(RecorderRuns.start < end).filter(
                RecorderRuns.end.is_(None) | (RecorderRuns.end > start)).all()
            intervals = [(r.start.timestamp(), r.end.timestamp() if r.end else last) for r in runs]
        return history_archive(rows, first, last, intervals, self.kind)

    async def import_history(self, force=False):
        if self.history_imported and not force:
            return True
        recorder = get_instance(self.hass)
        now = dt_util.utcnow().timestamp()
        first = getattr(getattr(recorder, "states_manager", None), "oldest_ts", None)
        first = max(0., first - 1.) if first is not None else now - getattr(recorder, "keep_days", 10) * 86400
        now = dt_util.utcnow().timestamp()
        hour_end = min((row.get("observed_start",row["start"]) for row in self.archive.hours.values()),default=now)
        quarter_end = min((row.get("observed_start",row["start"]) for row in self.archive.quarters.values()),default=now)
        try:
            imported = await recorder.async_add_executor_job(self.read_history, first, hour_end)
            detail = imported if quarter_end == hour_end else await recorder.async_add_executor_job(self.read_history, first, quarter_end)
            for field, source in (("hours",imported.hours),("quarters",detail.quarters)):
                for key, bucket in getattr(self.history,field).items():
                    if key not in source or source[key]["seconds"] < bucket["seconds"]:
                        source[key] = bucket
                setattr(imported,field,source)
            self.history = imported
        except Exception:
            _LOGGER.warning("Retained history import failed for %s; retrying on next analysis", self.entity, exc_info=True)
            return False
        self.history_imported = True
        self.store.async_delay_save(self.dump, 10)
        return True

    async def statistics(self, start, end, period="hour"):
        key = (start, end, period)
        now = dt_util.utcnow().timestamp()
        cached = self.cache.get(key)
        if cached and now - cached[0] < 60:
            return cached[1]
        result = await get_instance(self.hass).async_add_executor_job(
            partial(statistics_during_period, self.hass,
                    datetime.fromtimestamp(start, dt_util.UTC),
                    datetime.fromtimestamp(end, dt_util.UTC), {self.entity}, period,
                    ({"temperature": "°C"} if self.kind == "temperature" else {"speed": "km/h"} if self.kind == "wind" else None), {"mean", "min", "max"}))
        rows = result.get(self.entity, [])
        if len(self.cache) > 16:
            self.cache.clear()
        self.cache[key] = (now, rows)
        return rows

    async def analyse(self, msg, *, include_hourly=False):
        tz_name = self.hass.config.time_zone
        tz = ZoneInfo(tz_name)
        start_local = datetime.fromisoformat(msg["start_date"]).replace(tzinfo=tz)
        last_local = datetime.fromisoformat(msg["end_date"]).replace(tzinfo=tz)
        # Date-only strings avoid browser/HA timezone differences and DST errors.
        if len(msg["start_date"]) != 10 or len(msg["end_date"]) != 10 or start_local.date() > last_local.date():
            raise ValueError("Bitte gültige Kalendertage auswählen.")
        requested_end = (last_local + timedelta(days=1)).timestamp()
        interval = msg.get("chart_interval", 3600 if (last_local-start_local).days <= 3 else 86400)
        if interval not in (900,3600,10800,21600,86400):
            raise ValueError("Bitte eine gültige Chartauflösung auswählen.")
        start = start_local.timestamp()
        now = dt_util.utcnow().timestamp()
        window = msg.get("window")
        if window is not None:
            if window not in ("day","week"):
                raise ValueError("Bitte eine gültige aktuelle Sicht auswählen.")
            as_of = msg.get("as_of",now)
            if not isinstance(as_of,(int,float)) or not math.isfinite(as_of) or as_of < 0 or as_of > now+300:
                raise ValueError("Bitte einen gültigen Zeitpunkt auswählen.")
            reference = min(as_of,now)
            local = datetime.fromtimestamp(reference,tz)
            if window == "day":
                midnight = local.replace(hour=0,minute=0,second=0,microsecond=0)
                start = midnight.timestamp()
                requested_end = (midnight+timedelta(days=1)).timestamp()
            else:
                requested_end = math.floor(reference/60)*60+60
                start = (local.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=7)).timestamp()
            start_local = datetime.fromtimestamp(start,tz)
        end = min(now, requested_end, reference if window else now)
        if start >= end or requested_end <= start or requested_end-start > 367*86400 or (last_local.date()-datetime.fromisoformat(msg["start_date"]).date()).days > 365:
            raise ValueError("Der Zeitraum muss in der Vergangenheit beginnen und darf höchstens ein Jahr umfassen.")
        await self.import_history()
        self.archive.advance(now)
        archive_hours = combine_hours(self.history.hours, self.archive.hours)
        def measured(field,first,last):
            return combine_hours(self.history.buckets_between(field,first,last),self.archive.buckets_between(field,first,last))
        if window:
            prior_start = start-(requested_end-start)
        else:
            prior_start = (start_local - (last_local + timedelta(days=1) - start_local)).timestamp()
        prior_end = prior_start + (end-start)
        year_start_local = start_local.replace(year=start_local.year - 1, day=min(start_local.day, 28)) if start_local.month == 2 and start_local.day == 29 else start_local.replace(year=start_local.year - 1)
        year_start = year_start_local.timestamp()
        async with self.semaphore:
            stats, prior, year, records = await asyncio.gather(
                self.statistics(start, end), self.statistics(prior_start, prior_end),
                self.statistics(year_start, year_start + end - start),
                self.statistics(0, now, "year"))
        rows = merge_hours(stats, measured("hours",start,end), start, end)
        summary = summarize(rows, start, end, tz_name)
        quarters = merge_hours([], measured("quarters",start,end),start,end) if interval == 900 else []
        chart = resolution_chart(rows,quarters,interval,tz_name)
        comparisons = {}
        for label, data, first, last in (("previous", prior, prior_start, prior_end),
                                         ("year", year, year_start, year_start + end - start)):
            other = summarize(merge_hours(data, measured("hours",first,last), first, last), first, last, tz_name)
            comparisons[label] = {"mean": other["mean"], "coverage": other["coverage"],
                                  "delta": summary["mean"] - other["mean"] if summary["mean"] is not None and other["mean"] is not None else None}
        state = self.hass.states.get(self.entity)
        current = self.state_value()
        yesterday = datetime.fromtimestamp(now, tz) - timedelta(days=1)
        trend = {}
        for label, target in (("hour", now-3600), ("three_hours", now-10800), ("yesterday", yesterday.timestamp())):
            old = self.archive.value_at(target)
            if old is None:
                old = self.history.value_at(target)
            trend[label] = current-old if current is not None and old is not None else None
        # Yearly recorder summaries preserve values, but do not reveal record dates.
        record = {}
        for kind, choose in (("min", min), ("max", max)):
            candidates = [{"value": r[kind], "at": None} for r in records if r.get(kind) is not None]
            candidates.extend({"value": r[kind], "at": r[kind + "_at"]} for r in archive_hours.values() if r.get(kind) is not None)
            if candidates:
                extreme = choose(candidates, key=lambda r: r["value"])
                record[kind] = next((r for r in candidates if r["value"] == extreme["value"] and r["at"] is not None), extreme)
            else:
                record[kind] = None
        return {"version": VERSION, "kind": self.kind, "unit": {"temperature": "°C", "wind": "km/h", "illuminance": "lx"}[self.kind], "entity_id": self.entity, "name": state.name if state else self.entity,
                "timezone": tz_name, "current": current,
                "last_updated": state.last_updated.timestamp() if state else None,
                "start": start, "end": end, "display_end": requested_end, "window": window, "partial": end < requested_end,
                "summary": summary, "chart": chart, "chart_interval": interval,
                **({"hourly_chart":resolution_chart(rows,[],3600,tz_name)} if include_hourly else {}),
                "chart_daily": interval == 86400, "chart_fallback": any(point["resolution"] > interval for point in chart),
                "comparisons": comparisons, "trends": trend, "records": record,
                "archive_since": min((r.get("observed_start", r["start"]) for r in archive_hours.values()), default=now)}


@websocket_api.websocket_command({vol.Required("type"): "weather_analysis/sensors", vol.Optional("card_id", default="default"): str})
@websocket_api.async_response
async def ws_sensors(hass, connection, msg):
    groups = {"temperature": [], "wind": [], "illuminance": []}
    for state in hass.states.async_all("sensor"):
        kind = sensor_kind(state.entity_id, state.attributes)
        if kind and may_read(connection, state.entity_id):
            groups[kind].append({"entity_id": state.entity_id, "name": state.name})
    for group in groups.values():
        group.sort(key=lambda item: (item["name"].casefold(), item["entity_id"]))
    settings = deepcopy(hass.data[DOMAIN + "_settings"].get(msg["card_id"], {}))
    if settings:
        allowed = set()
        for kind, (plural, single) in SENSOR_FIELDS.items():
            entities = [entity for entity in configured_entities(settings, kind) if may_read(connection, entity)]
            settings[plural] = entities
            allowed.update(entities)
            if settings.get(single) not in entities:
                settings.pop(single, None)
            if entities and not settings.get(single):
                settings[single] = entities[0]
        if "sensor_names" in settings:
            settings["sensor_names"] = {entity: name for entity, name in settings["sensor_names"].items() if entity in allowed}
    connection.send_result(msg["id"], {"sensors": groups["temperature"], "wind_sensors": groups["wind"], "illuminance_sensors": groups["illuminance"], "version": VERSION,
        "timezone": hass.config.time_zone, "admin": connection.user.is_admin, "settings": settings, "wifi_sensors": wifi_sensors(hass,connection), "home_ssids":hass.data.get(DOMAIN+"_network",{}).get("home_ssids",[]),"home_wifi":on_home_wifi(hass,connection)})


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/save_card",
    vol.Required("card_id"): vol.All(str, vol.Length(min=1, max=100)),
    vol.Optional("entity", default=""): str,
    vol.Optional("entities"): [str],
    vol.Optional("sensor_names", default={}): {str: vol.All(str, vol.Length(max=100))},
    vol.Optional("wind_entities"): [str],
    vol.Optional("wind_entity", default=""): str,
    vol.Optional("illuminance_entities"): [str],
    vol.Optional("illuminance_entity", default=""): str,
    vol.Required("title"): vol.All(str, vol.Length(max=100)),
})
@websocket_api.async_response
async def ws_save_card(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Nur HA-Administratoren dürfen Karteneinstellungen speichern.")
        return
    chosen = {kind: configured_entities(msg, kind) for kind in SENSOR_FIELDS}
    if any(len(entities) > 100 for entities in chosen.values()):
        connection.send_error(msg["id"], "invalid_sensor", "Bitte höchstens 100 Sensoren je Messart auswählen.")
        return
    selected = [(entity, kind) for kind, entities in chosen.items() for entity in entities]
    for entity, kind in selected:
        state = hass.states.get(entity)
        if not may_read(connection, entity) or not state or sensor_kind(entity, state.attributes) != kind:
            connection.send_error(msg["id"], "invalid_sensor", "Bitte einen zugänglichen Sensor mit passender Einheit auswählen.")
            return
    all_entities = {entity for entity, kind in selected}
    sensor_names = {entity: name.strip() for entity, name in msg.get("sensor_names", {}).items()
                    if entity in all_entities and name.strip()}
    settings = {"title": msg["title"], "sensor_names": sensor_names}
    for kind, (plural, single) in SENSOR_FIELDS.items():
        entities = chosen[kind]
        settings[plural] = entities
        settings[single] = msg.get(single) if msg.get(single) in entities else next(iter(entities), "")
    for entity, kind in selected:
        await ensure_manager(hass, entity, kind)
    hass.data[DOMAIN + "_settings"][msg["card_id"]] = settings
    await hass.data[DOMAIN + "_store"].async_save(hass.data[DOMAIN + "_settings"])
    connection.send_result(msg["id"], settings)


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/save_network",
    vol.Required("home_ssids"):[vol.All(str,vol.Length(min=1,max=64))]})
@websocket_api.async_response
async def ws_save_network(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"],"unauthorized","Nur HA-Administratoren dürfen das gemeinsame Heim-WLAN ändern.");return
    ssids=list(dict.fromkeys(value for value in msg["home_ssids"] if value.strip()))
    if len(ssids)>20:
        connection.send_error(msg["id"],"invalid_wifi","Bitte höchstens 20 Heim-WLANs auswählen.");return
    data={"home_ssids":ssids}
    async with hass.data[DOMAIN+"_network_lock"]:
        await hass.data[DOMAIN+"_network_store"].async_save(data)
        hass.data[DOMAIN+"_network"]=data
    connection.send_result(msg["id"],data)


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/analyse",
    vol.Required("entity_id"): str,
    vol.Required("start_date"): str,
    vol.Required("end_date"): str,
    vol.Optional("chart_interval"): vol.All(vol.Coerce(int),vol.Range(min=900,max=86400)),
    vol.Optional("window"): str,
    vol.Optional("as_of"): vol.Coerce(float),
})
@websocket_api.async_response
async def ws_analyse(hass, connection, msg):
    if not may_read(connection, msg["entity_id"]):
        connection.send_error(msg["id"], "unauthorized", "Kein Lesezugriff auf diesen Sensor.")
        return
    manager = next((m for m in hass.data.get(DOMAIN, {}).values() if m.entity == msg["entity_id"]), None)
    if manager is None:
        state = hass.states.get(msg["entity_id"])
        kind = sensor_kind(msg["entity_id"], state.attributes) if state else None
        if not kind:
            connection.send_error(msg["id"], "invalid_sensor", "Bitte einen Temperatur-, Wind- oder Helligkeitssensor auswählen.")
            return
        manager = await ensure_manager(hass, msg["entity_id"], kind)
    try:
        result = await manager.analyse(msg)
    except (ValueError, OverflowError) as err:
        connection.send_error(msg["id"], "invalid_range", str(err))
    except Exception:
        _LOGGER.exception("Temperature analysis failed for %s", manager.entity)
        connection.send_error(msg["id"], "analysis_failed", "Die Historie konnte nicht gelesen werden. Details stehen im HA-Protokoll.")
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/import_history",
    vol.Required("card_id"): vol.All(str, vol.Length(min=1, max=100)),
})
@websocket_api.async_response
async def ws_import_history(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Nur HA-Administratoren dürfen die Historie übernehmen.")
        return
    settings = hass.data[DOMAIN + "_settings"].get(msg["card_id"], {})
    entities = [entity for kind in SENSOR_FIELDS for entity in configured_entities(settings, kind)]
    entities = list(dict.fromkeys(entities))
    if not entities:
        connection.send_error(msg["id"], "no_sensors", "Bitte zuerst Sensoren auswählen und speichern.")
        return
    for entity in entities:
        if not may_read(connection, entity):
            connection.send_error(msg["id"], "unauthorized", "Kein Lesezugriff auf einen der gewählten Sensoren.")
            return
    failed = []
    for entity in entities:
        manager = await ensure_manager(hass, entity)
        if not await manager.import_history(force=True):
            failed.append(entity)
        manager.cache.clear()
    connection.send_result(msg["id"], {"count": len(entities)-len(failed), "failed": failed})


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/dashboard",
    vol.Optional("as_of"): vol.Coerce(float),
    vol.Optional("temperature_entity", default=""): str,
    vol.Optional("wind_entity", default=""): str,
    vol.Optional("illuminance_entity", default=""): str,
})
@websocket_api.async_response
async def ws_dashboard(hass, connection, msg):
    """Today's sensor overview and independent public location forecast."""
    now = dt_util.utcnow().timestamp()
    snapshot = msg.get("as_of",now)
    if not isinstance(snapshot,(int,float)) or isinstance(snapshot,bool) or not math.isfinite(snapshot) or snapshot < 0 or snapshot > now+300:
        connection.send_error(msg["id"],"invalid_range","Bitte einen gültigen Zeitpunkt auswählen.")
        return
    snapshot = min(snapshot,now)
    local = datetime.fromtimestamp(snapshot,ZoneInfo(hass.config.time_zone))
    today = local.date().isoformat()
    sensors, errors, hourly_sensors = {}, {}, {}

    async def reading(kind):
        entity = msg.get(kind+"_entity", "")
        if not entity:
            return
        if not may_read(connection,entity):
            errors[kind] = "Kein Lesezugriff auf diesen Sensor."
            return
        state = hass.states.get(entity)
        manager = next((item for item in hass.data[DOMAIN].values() if item.entity==entity),None)
        if (state is not None and sensor_kind(entity,state.attributes)!=kind) or (state is None and (manager is None or manager.kind!=kind)):
            errors[kind] = "Sensor nicht verfügbar oder unpassende Messart."
            return
        try:
            manager = manager or await ensure_manager(hass,entity,kind)
            data = {"entity_id":entity,"current":manager.state_value(),"unit":{"temperature":"°C","wind":"km/h","illuminance":"lx"}[kind],
                "updated_at":state.last_updated.timestamp() if state is not None else None}
            analysis = await manager.analyse({"start_date":today,"end_date":today,"chart_interval":10800,"window":"day","as_of":snapshot},include_hourly=True)
            data.update({key:analysis["summary"].get(key) for key in ("min","max","min_at","max_at")})
            data["chart"] = analysis["chart"]
            hourly_sensors[kind] = {point["start"]:point for point in analysis["hourly_chart"]}
            sensors[kind] = data
        except Exception:
            _LOGGER.exception("Dashboard reading failed for %s",entity)
            errors[kind] = "Die heutigen Messwerte konnten nicht geladen werden."

    await asyncio.gather(*(reading(kind) for kind in SENSOR_FIELDS))
    intervals = []
    midnight = local.replace(hour=0,minute=0,second=0,microsecond=0)
    for hour in range(0,24,3):
        start = (midnight+timedelta(hours=hour)).timestamp()
        end = min(snapshot,(midnight+timedelta(hours=hour+3)).timestamp())
        if start >= end:
            continue
        points = {kind:next((point for point in data.get("chart",[]) if point["start"]==start),{}) for kind,data in sensors.items()}
        temperature,wind,light = (points.get(kind,{}) for kind in SENSOR_FIELDS)
        intervals.append({"start":start,"end":end,"partial":end<(midnight+timedelta(hours=hour+3)).timestamp(),
            "temperature":temperature.get("mean"),"temperature_min":temperature.get("min"),"temperature_max":temperature.get("max"),
            "wind_speed":wind.get("mean"),"wind_max":wind.get("max"),"illuminance":light.get("mean"),
            "estimated":any(point.get("estimated",False) for point in points.values())})
        hours = []
        for hour_start in range(int(start),math.ceil(end),3600):
            hour_end = min(hour_start+3600,end)
            points = {kind:chart.get(hour_start,{}) for kind,chart in hourly_sensors.items()}
            temperature,wind,light = (points.get(kind,{}) for kind in SENSOR_FIELDS)
            hours.append({"start":hour_start,"end":hour_end,"partial":hour_end<hour_start+3600,
                "temperature":temperature.get("mean"),"temperature_min":temperature.get("min"),"temperature_max":temperature.get("max"),
                "wind_speed":wind.get("mean"),"wind_max":wind.get("max"),"illuminance":light.get("mean"),
                "estimated":any(point.get("estimated",False) for point in points.values())})
        intervals[-1]["hours"] = hours
    connection.send_result(msg["id"],{"version":VERSION,"date":today,"timezone":hass.config.time_zone,"as_of":snapshot,
        "sensors":sensors,"errors":errors,"intervals":intervals})


def user_people(hass, connection):
    user_id = getattr(connection.user,"id",None)
    return [p for p in hass.states.async_all("person") if user_id and p.entity_id.startswith("person.")
        and p.attributes.get("user_id")==user_id and may_read(connection,p.entity_id)]


def user_tracker_ids(hass, connection):
    result=set()
    for person in user_people(hass,connection):
        trackers=person.attributes.get("device_trackers",[])
        values=list(trackers) if isinstance(trackers,list) else []
        values.append(person.attributes.get("source"))
        result.update(value for value in values if isinstance(value,str) and value.startswith("device_tracker.") and may_read(connection,value))
    return result


def wifi_sensors(hass, connection):
    """SSID entities from the same mobile devices as the user's linked trackers."""
    from homeassistant.helpers import entity_registry as er
    registry=er.async_get(hass)
    devices={entry.device_id for entity in user_tracker_ids(hass,connection)
        if (entry:=registry.async_get(entity)) and entry.device_id}
    result=[]
    for entry in registry.entities.values():
        if entry.device_id not in devices or entry.platform!="mobile_app" or not entry.entity_id.startswith("sensor.") or not may_read(connection,entry.entity_id):
            continue
        unique=entry.unique_id
        if unique not in ("ssid","wifi_connection") and not unique.endswith(("_ssid","_wifi_connection")):
            continue
        if (state:=hass.states.get(entry.entity_id)) is not None:
            ssid=state.state
            if ssid.casefold() in ("unknown","unavailable","not connected","nicht verbunden","<unknown ssid>","none",""):
                ssid=None
            result.append({"entity_id":entry.entity_id,"name":state.name,"ssid":ssid})
    return sorted(result,key=lambda item:item["entity_id"])


def on_home_wifi(hass, connection):
    # A router tracker only reports home for its configured home network.
    for entity in user_tracker_ids(hass,connection):
        state=hass.states.get(entity)
        if state and state.state=="home" and state.attributes.get("source_type")=="router":
            return True
    ssids=hass.data.get(DOMAIN+"_network",{}).get("home_ssids",[])
    return bool(ssids) and any(sensor["ssid"] in ssids for sensor in wifi_sensors(hass,connection))


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/network"})
@websocket_api.async_response
async def ws_network(hass, connection, msg):
    """Check home Wi-Fi without reading GPS or contacting a location provider."""
    connection.send_result(msg["id"],{"home_wifi":on_home_wifi(hass,connection),
        "home_ssids":hass.data.get(DOMAIN+"_network",{}).get("home_ssids",[]),
        "wifi_sensors":wifi_sensors(hass,connection)})


def user_position(hass, connection):
    """Read only the logged-in user's linked person and permitted GPS trackers."""
    people = user_people(hass,connection)
    candidates = []
    for person in people:
        ids = person.attributes.get("device_trackers", [])
        ids = list(ids) if isinstance(ids,list) else []
        source = person.attributes.get("source")
        if isinstance(source,str) and source.startswith("device_tracker."):
            ids.append(source)
        for entity in {value for value in ids if isinstance(value,str)}:
            if not isinstance(entity,str) or not entity.startswith("device_tracker.") or not may_read(connection,entity):
                continue
            state = hass.states.get(entity)
            if not state or state.state in ("unknown","unavailable") or state.attributes.get("source_type") != "gps":
                continue
            try:
                lat,lon = coordinates(state.attributes.get("latitude"),state.attributes.get("longitude"))
            except ValueError:
                continue
            candidates.append((state.last_updated.timestamp(),lat,lon))
    if candidates:
        _,lat,lon = max(candidates)
        return lat,lon
    for person in people:
        if person.state in ("unknown","unavailable"):
            continue
        try:
            return coordinates(person.attributes.get("latitude"),person.attributes.get("longitude"))
        except ValueError:
            pass
    return None


async def resolve_place(hass, latitude, longitude):
    client = hass.data.setdefault(DOMAIN+"_location",LocationClient(hass))
    return await client.get(latitude,longitude)


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/location",
    vol.Optional("latitude"):vol.Coerce(float),vol.Optional("longitude"):vol.Coerce(float)})
@websocket_api.async_response
async def ws_location(hass, connection, msg):
    try:
        location=await resolve_user_location(hass,connection,msg)
    except ValueError as error:
        connection.send_error(msg["id"],"invalid_location",str(error));return
    error = None
    if not location["position_available"] and location.get("via")!="home_wifi":
        error="Kein GPS-Standort verfügbar. Angezeigt wird die Vorhersage für Böhl-Iggelheim."
    elif not location["resolved"]:
        error="Der Ortsname ist derzeit nicht verfügbar. Die Vorhersage nutzt weiterhin deinen GPS-Standort."
    connection.send_result(msg["id"],{"location":location,"location_error":error})


async def resolve_user_location(hass,connection,msg):
    if on_home_wifi(hass,connection):return home_location()
    point=coordinates(msg.get("latitude"),msg.get("longitude")) if "latitude" in msg or "longitude" in msg else user_position(hass,connection)
    return await resolve_place(hass,*point) if point else fallback()


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/radar",
    vol.Optional("latitude"):vol.Coerce(float),vol.Optional("longitude"):vol.Coerce(float),
    vol.Optional("zoom",default=1):vol.All(vol.Coerce(int),vol.Range(min=0,max=3))})
@websocket_api.async_response
async def ws_radar(hass,connection,msg):
    try:
        location=await resolve_user_location(hass,connection,msg)
        client=hass.data.setdefault(DOMAIN+"_radar",RadarClient(hass))
        result=await client.get(connection.user.id,location["latitude"],location["longitude"],msg.get("zoom",1))
        connection.send_result(msg["id"],{"radar":result,"radar_error":None,"location":location,"credits":{"dwd":"https://www.dwd.de/","bkg":"https://www.bkg.bund.de","license":"https://www.govdata.de/dl-de/by-2-0","sources":"https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_topplusopen.html"}})
    except ValueError as error:connection.send_error(msg["id"],"invalid_location",str(error))
    except RadarUnavailable as error:connection.send_result(msg["id"],{"radar":None,"radar_error":str(error),"location":location})


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/radar_image",vol.Required("token"):str,
    vol.Required("kind"):vol.In(("frame","base","legend")),vol.Optional("index",default=0):vol.All(vol.Coerce(int),vol.Range(min=0,max=40))})
@websocket_api.async_response
async def ws_radar_image(hass,connection,msg):
    try:
        client=hass.data.setdefault(DOMAIN+"_radar",RadarClient(hass))
        image=await client.image(connection.user.id,msg["token"],msg["kind"],msg.get("index",0))
        connection.send_result(msg["id"],{"image":image})
    except (ValueError,RadarUnavailable) as error:connection.send_error(msg["id"],"radar_unavailable",str(error))


@websocket_api.websocket_command({vol.Required("type"):"weather_analysis/warnings",
    vol.Optional("latitude"):vol.Coerce(float),vol.Optional("longitude"):vol.Coerce(float)})
@websocket_api.async_response
async def ws_warnings(hass,connection,msg):
    try:
        location=await resolve_user_location(hass,connection,msg)
    except ValueError as error:
        connection.send_error(msg["id"],"invalid_location",str(error));return
    client=hass.data.setdefault(DOMAIN+"_warnings",WarningsClient(hass))
    try:
        result=await client.get(location["latitude"],location["longitude"],location.get("country_code",""))
        connection.send_result(msg["id"],{"warnings":result,"warnings_error":None,"location":location,"source_url":DWD_SOURCE_URL})
    except WarningsUnavailable as error:
        connection.send_result(msg["id"],{"warnings":None,"warnings_error":str(error),"location":location,"source_url":DWD_SOURCE_URL})


@websocket_api.websocket_command({vol.Required("type"): "weather_analysis/forecast",vol.Optional("as_of"):vol.Coerce(float),
    vol.Optional("latitude"):vol.Coerce(float),vol.Optional("longitude"):vol.Coerce(float)})
@websocket_api.async_response
async def ws_forecast(hass, connection, msg):
    location = None
    if "latitude" in msg or "longitude" in msg:
        try:
            lat,lon = coordinates(msg.get("latitude"),msg.get("longitude"))
        except ValueError as error:
            connection.send_error(msg["id"],"invalid_location",str(error));return
        location = await resolve_place(hass,lat,lon)
        pool = hass.data.setdefault(DOMAIN+"_forecast_locations",OrderedDict())
        key = (round(lat,3),round(lon,3),location.get("country_code"),location.get("postal_code"))
        if key not in pool:
            pool[key] = ForecastClient(hass,location=location)
        client = pool[key]
        pool.move_to_end(key)
        while len(pool)>64:
            pool.popitem(last=False)
    else:
        client = hass.data.setdefault(DOMAIN+"_forecast",ForecastClient(hass))
    try:
        prediction,error = await client.get(as_of=msg.get("as_of")),None
        if location:
            prediction = {**prediction,"location":location}
    except ForecastUnavailable as exception:
        prediction,error = None,str(exception)
    connection.send_result(msg["id"],{"forecast":prediction,"forecast_error":error})
