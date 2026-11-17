"""Temperature arithmetic, independent of Home Assistant. All values use Celsius."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from zoneinfo import ZoneInfo

HOUR = 3600
THRESHOLDS = ("frost", "warm", "hot")


def celsius(value, unit="°C"):
    """Reject unknown states and convert physical temperature units."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value):
        return None
    if unit == "°F":
        return (value - 32) * 5 / 9
    if unit == "K":
        return value - 273.15
    return value if unit == "°C" else None


def empty_bucket(start):
    return {"start": start, "end": start + HOUR, "seconds": 0., "weighted": 0.,
            "min": None, "max": None, "min_at": None, "max_at": None,
            "frost": 0., "warm": 0., "hot": 0.}


class Archive:
    """Persist hourly integrals and exact extrema; retain three days of transitions.

    The last known value is held until a state change. Unavailable states and
    integration downtime are gaps, never silently interpolated.
    """

    def __init__(self, data=None):
        data = data or {}
        self.hours = deepcopy(data.get("hours", {}))
        self.recent = deepcopy(data.get("recent", []))
        self.last_time = data.get("last_time")
        self.value = None

    def start(self, now, value):
        if self.last_time is not None and now > self.last_time:
            self.recent.append([self.last_time, None])
        self.last_time = now
        self.value = value
        self.recent.append([now, value])
        self.prune(now)

    def advance(self, now):
        if self.last_time is None or now <= self.last_time:
            return
        cursor = self.last_time
        if self.value is not None:
            while cursor < now:
                start = math.floor(cursor / HOUR) * HOUR
                end = min(start + HOUR, now)
                bucket = self.hours.setdefault(str(start), empty_bucket(start))
                seconds = end - cursor
                bucket["seconds"] += seconds
                bucket["weighted"] += self.value * seconds
                bucket.setdefault("observed_start", cursor)
                bucket["observed_end"] = end
                for kind, condition in (("min", lambda a, b: a < b), ("max", lambda a, b: a > b)):
                    if bucket[kind] is None or condition(self.value, bucket[kind]):
                        bucket[kind] = self.value
                        bucket[kind + "_at"] = cursor
                bucket["frost"] += seconds if self.value < 0 else 0
                bucket["warm"] += seconds if self.value >= 25 else 0
                bucket["hot"] += seconds if self.value >= 30 else 0
                cursor = end
        self.last_time = now
        self.prune(now)

    def change(self, now, value):
        self.advance(now)
        if value != self.value:
            self.value = value
            self.recent.append([now, value])

    def prune(self, now):
        cutoff = now - 3 * 86400
        while len(self.recent) > 1 and self.recent[1][0] < cutoff:
            self.recent.pop(0)

    def value_at(self, when):
        found = None
        for timestamp, value in self.recent:
            if timestamp > when:
                break
            found = value
        return found

    def dump(self):
        return {"hours": self.hours, "recent": self.recent, "last_time": self.last_time}


def merge_hours(stats, archived, start, end):
    """Prefer complete measured hours; use recorder statistics for older gaps.

    HA supplies no coverage information for a long-term statistic. Its mean is
    weighted by the returned interval and marked estimated. Threshold durations
    always come only from the independent archive.
    """
    rows = {}
    for stat in stats:
        mean = stat.get("mean")
        if mean is None or not math.isfinite(mean):
            continue
        ts = float(stat["start"])
        stop = float(stat.get("end", ts + HOUR))
        if ts < start or stop > end:
            continue
        seconds = max(0, min(stop, end) - max(ts, start))
        if not seconds:
            continue
        rows[ts] = {"start": max(ts, start), "end": min(stop, end),
                    "seconds": seconds, "weighted": mean * seconds,
                    "min": stat.get("min", mean), "max": stat.get("max", mean),
                    "min_at": None, "max_at": None, "exact_seconds": 0.,
                    "source": "statistics", **dict.fromkeys(THRESHOLDS, 0.)}
    for data in archived.values():
        ts = data["start"]
        if ts >= end or data["end"] <= start or not data["seconds"]:
            continue
        # Queries align to local days; UTC hour buckets fit ordinary HA time zones.
        # At fractional-offset boundaries use recorder for the clipped hour, rather
        # than falsely distributing measured threshold durations over that hour.
        if data.get("observed_start", ts) < start or data.get("observed_end", data["end"]) > end:
            continue
        old = rows.get(ts)
        if old and data["seconds"] < old["seconds"] - 1:
            old["exact_seconds"] = data["seconds"]
            for key in THRESHOLDS:
                old[key] = data[key]
            # A newly received extreme may not yet be present in HA statistics.
            for key, cmp in (("min", min), ("max", max)):
                if old[key] is None or cmp(old[key], data[key]) == data[key]:
                    old[key], old[key + "_at"] = data[key], data[key + "_at"]
        else:
            rows[ts] = {**deepcopy(data), "start": max(ts, start), "end": min(data["end"], end),
                        "source": "archive", "exact_seconds": data["seconds"]}
    return sorted(rows.values(), key=lambda r: r["start"])


def summarize(rows, start, end, tz_name="Europe/Berlin"):
    tz = ZoneInfo(tz_name)
    seconds = sum(r["seconds"] for r in rows)
    exact = sum(r.get("exact_seconds", 0) for r in rows)
    result = {"mean": sum(r["weighted"] for r in rows) / seconds if seconds else None,
              "min": None, "max": None, "min_at": None, "max_at": None,
              "seconds": seconds, "exact_seconds": exact,
              "coverage": min(1., seconds / (end-start)) if end > start else 0.,
              "duration_coverage": min(1., exact / (end-start)) if end > start else 0.,
              "estimated": any(r["source"] == "statistics" for r in rows),
              **{k + "_hours": sum(r[k] for r in rows) / HOUR for k in THRESHOLDS}}
    for kind, cmp in (("min", min), ("max", max)):
        candidates = [r for r in rows if r.get(kind) is not None]
        if candidates:
            best = cmp(candidates, key=lambda r: r[kind])
            result[kind] = best[kind]
            result[kind + "_at"] = best.get(kind + "_at")
            result[kind + "_period"] = best["start"]
    result["range"] = result["max"] - result["min"] if seconds else None
    days = {}
    for row in rows:
        date = datetime.fromtimestamp(row["start"], tz).date().isoformat()
        day = days.setdefault(date, {"date": date, "seconds": 0., "weighted": 0., "min": None, "max": None})
        day["seconds"] += row["seconds"]
        day["weighted"] += row["weighted"]
        for kind, cmp in (("min", min), ("max", max)):
            if row.get(kind) is not None:
                day[kind] = row[kind] if day[kind] is None else cmp(day[kind], row[kind])
    result.update(frost_days=0, warm_days=0, hot_days=0, complete_days=0)
    for day in days.values():
        day["mean"] = day.pop("weighted") / day["seconds"]
        date = datetime.fromisoformat(day["date"])
        local_start = date.replace(tzinfo=tz)
        local_end = (date + timedelta(days=1)).replace(tzinfo=tz)
        expected = local_end.timestamp() - local_start.timestamp()
        day["complete"] = day["seconds"] >= .95 * expected and local_end.timestamp() <= end
        result["complete_days"] += int(day["complete"])
        # These are observed days, never a claim that missing days were frost-free.
        result["frost_days"] += int(day["min"] is not None and day["min"] < 0)
        result["warm_days"] += int(day["max"] is not None and day["max"] >= 25)
        result["hot_days"] += int(day["max"] is not None and day["max"] >= 30)
    result["days"] = list(days.values())
    return result


def chart_rows(rows, daily, tz_name):
    if not daily:
        return [{"start": r["start"], "end": r["end"], "mean": r["weighted"] / r["seconds"],
                 "min": r["min"], "max": r["max"]} for r in rows if r["seconds"]]
    summary = summarize(rows, rows[0]["start"], rows[-1]["end"], tz_name) if rows else {"days": []}
    return [{"start": datetime.fromisoformat(r["date"]).replace(tzinfo=ZoneInfo(tz_name)).timestamp(),
             "end": min(rows[-1]["end"], (datetime.fromisoformat(r["date"]) + timedelta(days=1)).replace(tzinfo=ZoneInfo(tz_name)).timestamp()),
             "mean": r["mean"], "min": r["min"], "max": r["max"]} for r in summary["days"]]

WIND_UNITS = {"m/s": 3.6, "km/h": 1., "kmh": 1., "kph": 1., "mph": 1.609344,
              "kn": 1.852, "knots": 1.852, "kt": 1.852, "ft/s": 1.09728}


def sensor_kind(entity, attributes):
    """Accept temperature and wind-speed sensors, including unavailable states."""
    if not entity.startswith("sensor."):
        return None
    unit = attributes.get("unit_of_measurement")
    device_class = attributes.get("device_class")
    if unit in ("°C", "°F", "K") and device_class in (None, "temperature"):
        return "temperature"
    if unit == "lx" and device_class in (None, "illuminance"):
        return "illuminance"
    if unit in WIND_UNITS and device_class in (None, "wind_speed", "speed"):
        return "wind"
    return None


def sensor_value(value, unit, kind):
    if kind == "temperature":
        return celsius(value, unit)
    try:
        number = float(value)
        factor = 1. if kind == "illuminance" and unit == "lx" else WIND_UNITS[unit]
    except (ValueError, TypeError, KeyError):
        return None
    return number * factor if math.isfinite(number) and number >= 0 else None


def combine_hours(older, newer):
    """Combine disjoint measured prefixes with the existing live archive."""
    result = deepcopy(older)
    for key, source in newer.items():
        if key not in result:
            result[key] = deepcopy(source)
            continue
        dest = result[key]
        for field in ("seconds", "weighted", *THRESHOLDS):
            dest[field] += source[field]
        dest["observed_start"] = min(dest.get("observed_start", dest["start"]),
                                     source.get("observed_start", source["start"]))
        dest["observed_end"] = max(dest.get("observed_end", dest["end"]),
                                   source.get("observed_end", source["end"]))
        for field, choose in (("min", min), ("max", max)):
            if source[field] is not None and (dest[field] is None or choose(dest[field], source[field]) == source[field]):
                dest[field], dest[field + "_at"] = source[field], source[field + "_at"]
    return result


def history_archive(states, start, end, runs, kind):
    """Integrate recorder states inside recording runs, preserving downtime."""
    result = Archive()
    snapshots = sorted(states, key=lambda state: state.last_updated.timestamp())
    index = 0
    for run_start, run_end in sorted(runs):
        first, last = max(start, run_start), min(end, run_end)
        if first >= last:
            continue
        result.start(first, None)
        while index < len(snapshots) and snapshots[index].last_updated.timestamp() < first:
            index += 1
        while index < len(snapshots):
            state = snapshots[index]
            at = state.last_updated.timestamp()
            if at >= last:
                break
            result.change(at, sensor_value(state.state, state.attributes.get("unit_of_measurement"), kind))
            index += 1
        result.advance(last)
        result.change(last, None)
    return result
