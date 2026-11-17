"""Weather Analysis: recorder-backed card and persistent temperature integrals."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import logging
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
from homeassistant.core import callback
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.recorder import get_instance
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .analytics import Archive, celsius, merge_hours, summarize, chart_rows

DOMAIN = "weather_analysis"
VERSION = "1.0.0"
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    settings_store = Store(hass, 1, DOMAIN + ".cards")
    hass.data[DOMAIN + "_settings"] = await settings_store.async_load() or {}
    hass.data[DOMAIN + "_store"] = settings_store
    await hass.http.async_register_static_paths([
        StaticPathConfig("/weather-analysis", str(Path(__file__).parent / "frontend"), False)
    ])
    frontend.add_extra_js_url(hass, f"/weather-analysis/weather-analysis-card.js?v={VERSION}")
    for command in (ws_sensors, ws_analyse, ws_save_card):
        websocket_api.async_register_command(hass, command)
    return True


async def async_setup_entry(hass, entry):
    manager = Manager(hass, entry)
    await manager.load()
    hass.data[DOMAIN][entry.entry_id] = manager
    entry.runtime_data = manager
    entry.async_on_unload(async_track_state_change_event(hass, [manager.entity], manager.state_changed))
    entry.async_on_unload(async_track_time_interval(hass, manager.pulse, timedelta(minutes=1)))
    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, manager.stop))
    return True


async def async_unload_entry(hass, entry):
    manager = hass.data[DOMAIN].pop(entry.entry_id)
    await manager.stop()
    return True


def may_read(connection, entity):
    return connection.user.permissions.check_entity(entity, POLICY_READ)


class Manager:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entity = entry.data["entity_id"]
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.archive = Archive()
        self.cache = {}
        self.semaphore = asyncio.Semaphore(2)

    def state_value(self):
        state = self.hass.states.get(self.entity)
        return celsius(state.state, state.attributes.get("unit_of_measurement")) if state else None

    async def load(self):
        self.archive = Archive(await self.store.async_load())
        self.archive.start(dt_util.utcnow().timestamp(), self.state_value())
        self.store.async_delay_save(self.archive.dump, 10)

    @callback
    def state_changed(self, event):
        state = event.data.get("new_state")
        value = celsius(state.state, state.attributes.get("unit_of_measurement")) if state else None
        self.archive.change(event.time_fired.timestamp(), value)
        self.cache.clear()
        self.store.async_delay_save(self.archive.dump, 10)

    async def pulse(self, now=None):
        self.archive.advance(dt_util.utcnow().timestamp())
        self.store.async_delay_save(self.archive.dump, 10)

    async def stop(self, event=None):
        self.archive.advance(dt_util.utcnow().timestamp())
        await self.store.async_save(self.archive.dump())

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
                    {"temperature": "°C"}, {"mean", "min", "max"}))
        rows = result.get(self.entity, [])
        if len(self.cache) > 16:
            self.cache.clear()
        self.cache[key] = (now, rows)
        return rows

    async def analyse(self, msg):
        tz_name = self.hass.config.time_zone
        tz = ZoneInfo(tz_name)
        start_local = datetime.fromisoformat(msg["start_date"]).replace(tzinfo=tz)
        last_local = datetime.fromisoformat(msg["end_date"]).replace(tzinfo=tz)
        # Date-only strings avoid browser/HA timezone differences and DST errors.
        if len(msg["start_date"]) != 10 or len(msg["end_date"]) != 10:
            raise ValueError("Bitte gültige Kalendertage auswählen.")
        requested_end = (last_local + timedelta(days=1)).timestamp()
        start = start_local.timestamp()
        now = dt_util.utcnow().timestamp()
        end = min(now, requested_end)
        if start >= end or requested_end <= start or (last_local.date()-start_local.date()).days > 365:
            raise ValueError("Der Zeitraum muss in der Vergangenheit beginnen und darf höchstens ein Jahr umfassen.")
        base, limit = msg["heating_base"], msg["heating_limit"]
        if base < limit:
            raise ValueError("Die Raumtemperatur muss mindestens der Heizgrenze entsprechen.")
        self.archive.advance(now)
        archive_hours = deepcopy(self.archive.hours)
        prior_start = (start_local - (last_local + timedelta(days=1) - start_local)).timestamp()
        prior_end = prior_start + (end - start)
        year_start_local = start_local.replace(year=start_local.year - 1, day=min(start_local.day, 28)) if start_local.month == 2 and start_local.day == 29 else start_local.replace(year=start_local.year - 1)
        year_start = year_start_local.timestamp()
        async with self.semaphore:
            stats, prior, year, records = await asyncio.gather(
                self.statistics(start, end), self.statistics(prior_start, prior_end),
                self.statistics(year_start, year_start + end - start),
                self.statistics(0, now, "year"))
        rows = merge_hours(stats, archive_hours, start, end)
        summary = summarize(rows, start, end, tz_name, base, limit)
        comparisons = {}
        for label, data, first, last in (("previous", prior, prior_start, prior_end),
                                         ("year", year, year_start, year_start + end - start)):
            other = summarize(merge_hours(data, archive_hours, first, last), first, last, tz_name, base, limit)
            comparisons[label] = {"mean": other["mean"], "coverage": other["coverage"],
                                  "delta": summary["mean"] - other["mean"] if summary["mean"] is not None and other["mean"] is not None else None}
        state = self.hass.states.get(self.entity)
        current = self.state_value()
        yesterday = datetime.fromtimestamp(now, tz) - timedelta(days=1)
        trend = {}
        for label, target in (("hour", now-3600), ("three_hours", now-10800), ("yesterday", yesterday.timestamp())):
            old = self.archive.value_at(target)
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
        return {"version": VERSION, "entity_id": self.entity, "name": state.name if state else self.entity,
                "timezone": tz_name, "current": current,
                "last_updated": state.last_updated.timestamp() if state else None,
                "start": start, "end": end, "partial": end < requested_end,
                "summary": summary, "chart": chart_rows(rows, end-start > 3*86400, tz_name),
                "chart_daily": end-start > 3*86400,
                "comparisons": comparisons, "trends": trend, "records": record,
                "archive_since": min((r.get("observed_start", r["start"]) for r in archive_hours.values()), default=now)}


@websocket_api.websocket_command({vol.Required("type"): "weather_analysis/sensors", vol.Optional("card_id", default="default"): str})
@websocket_api.async_response
async def ws_sensors(hass, connection, msg):
    result = []
    for manager in hass.data.get(DOMAIN, {}).values():
        if may_read(connection, manager.entity):
            state = hass.states.get(manager.entity)
            result.append({"entity_id": manager.entity, "name": state.name if state else manager.entity})
    settings = hass.data[DOMAIN + "_settings"].get(msg["card_id"], {})
    if settings.get("entity") and not may_read(connection, settings["entity"]):
        settings = {}
    connection.send_result(msg["id"], {"sensors": result, "version": VERSION,
        "timezone": hass.config.time_zone, "admin": connection.user.is_admin, "settings": settings})


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/save_card", vol.Required("card_id"): vol.All(str, vol.Length(min=1, max=100)),
    vol.Required("entity"): str, vol.Required("title"): vol.All(str, vol.Length(max=100)),
    vol.Required("heating_base"): vol.All(vol.Coerce(float), vol.Range(min=0, max=40)),
    vol.Required("heating_limit"): vol.All(vol.Coerce(float), vol.Range(min=-20, max=30)),
})
@websocket_api.async_response
async def ws_save_card(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "Nur HA-Administratoren dürfen Karteneinstellungen speichern.")
        return
    if not any(m.entity == msg["entity"] for m in hass.data[DOMAIN].values()) or not may_read(connection, msg["entity"]):
        connection.send_error(msg["id"], "invalid_sensor", "Bitte einen eingerichteten Temperatursensor wählen.")
        return
    if msg["heating_base"] < msg["heating_limit"]:
        connection.send_error(msg["id"], "invalid_settings", "Die Raumtemperatur muss mindestens der Heizgrenze entsprechen.")
        return
    settings = {key: msg[key] for key in ("entity", "title", "heating_base", "heating_limit")}
    hass.data[DOMAIN + "_settings"][msg["card_id"]] = settings
    await hass.data[DOMAIN + "_store"].async_save(hass.data[DOMAIN + "_settings"])
    connection.send_result(msg["id"], settings)


@websocket_api.websocket_command({
    vol.Required("type"): "weather_analysis/analyse",
    vol.Required("entity_id"): str,
    vol.Required("start_date"): str,
    vol.Required("end_date"): str,
    vol.Optional("heating_base", default=20.): vol.All(vol.Coerce(float), vol.Range(min=0, max=40)),
    vol.Optional("heating_limit", default=15.): vol.All(vol.Coerce(float), vol.Range(min=-20, max=30)),
})
@websocket_api.async_response
async def ws_analyse(hass, connection, msg):
    if not may_read(connection, msg["entity_id"]):
        connection.send_error(msg["id"], "unauthorized", "Kein Lesezugriff auf diesen Sensor.")
        return
    manager = next((m for m in hass.data.get(DOMAIN, {}).values() if m.entity == msg["entity_id"]), None)
    if manager is None:
        connection.send_error(msg["id"], "not_configured", "Bitte den Sensor zuerst als Weather-Analysis-Integration hinzufügen.")
        return
    try:
        result = await manager.analyse(msg)
    except (ValueError, OverflowError) as err:
        connection.send_error(msg["id"], "invalid_range", str(err))
    except Exception:
        _LOGGER.exception("Temperature analysis failed for %s", manager.entity)
        connection.send_error(msg["id"], "analysis_failed", "Die Historie konnte nicht gelesen werden. Details stehen im HA-Protokoll.")
    else:
        connection.send_result(msg["id"], result)
