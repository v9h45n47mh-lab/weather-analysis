"""Numerical regression tests; no Home Assistant installation required."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from types import SimpleNamespace

path = Path(__file__).parents[1] / "custom_components/weather_analysis/analytics.py"
spec = importlib.util.spec_from_file_location("analytics", path)
analytics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analytics)
Archive, merge, summarize = analytics.Archive, analytics.merge_hours, analytics.summarize


class AnalyticsTests(unittest.TestCase):
    def test_units_unknown_and_zero(self):
        self.assertEqual(analytics.celsius(0), 0)
        self.assertAlmostEqual(analytics.celsius(32, "°F"), 0)
        self.assertAlmostEqual(analytics.celsius(273.15, "K"), 0)
        for value in ("unknown", "unavailable", "nan", "inf", None):
            self.assertIsNone(analytics.celsius(value))
        self.assertIsNone(analytics.celsius(5, "%"))

    def test_weighted_mean_not_sample_mean(self):
        a = Archive()
        a.start(0, 10)
        a.change(900, 20)
        a.advance(3600)
        s = summarize(merge([], a.hours, 0, 3600), 0, 3600, "UTC")
        self.assertEqual(s["mean"], 17.5)
        self.assertEqual(s["min_at"], 0)
        self.assertEqual(s["max_at"], 900)
        self.assertEqual(s["range"], 10)

    def test_unavailable_and_restart_are_gaps(self):
        a = Archive()
        a.start(0, -2)
        a.change(600, None)
        a.change(1200, 3)
        a.advance(1800)
        b = Archive(a.dump())
        b.start(2400, 3)
        b.advance(3600)
        s = summarize(merge([], b.hours, 0, 3600), 0, 3600, "UTC")
        self.assertEqual(s["seconds"], 2400)
        self.assertAlmostEqual(s["frost_hours"], 1/6)
        self.assertAlmostEqual(s["coverage"], 2/3)
        self.assertIsNone(b.value_at(2100))

    def test_threshold_boundaries(self):
        for value, expected in ((0, (0,0,0)), (-.1, (1,0,0)), (25, (0,1,0)), (30, (0,1,1))):
            a = Archive();a.start(0, value);a.advance(3600)
            s = summarize(merge([], a.hours, 0, 3600), 0, 3600, "UTC")
            self.assertEqual(tuple(s[k+"_hours"] for k in analytics.THRESHOLDS), expected)

    def test_no_double_count_on_repeated_advance(self):
        a = Archive();a.start(0, 5);a.advance(3600);a.advance(3600);a.advance(3500)
        self.assertEqual(sum(r["seconds"] for r in a.hours.values()), 3600)

    def test_current_partial_hour_is_included(self):
        a = Archive();a.start(1800, 8);a.advance(2100)
        s = summarize(merge([], a.hours, 0, 2100), 0, 2100, "UTC")
        self.assertEqual(s["seconds"], 300)
        self.assertEqual(s["mean"], 8)

    def test_archived_hour_beats_stats_without_double_counting(self):
        a = Archive();a.start(0, 10);a.advance(3600)
        rows = merge([{"start":0,"end":3600,"mean":9,"min":8,"max":11}], a.hours, 0, 3600)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "archive")
        self.assertEqual(summarize(rows, 0, 3600, "UTC")["mean"], 10)

    def test_partial_archive_preserves_old_stats_and_only_known_durations(self):
        a = Archive();a.start(1800, -2);a.advance(3600)
        rows = merge([{"start":0,"end":3600,"mean":-1,"min":-1,"max":0}], a.hours, 0, 3600)
        s = summarize(rows, 0, 3600, "UTC")
        self.assertEqual(s["mean"], -1)
        self.assertEqual(s["min"], -2)
        self.assertEqual(s["frost_hours"], .5)
        self.assertEqual(s["duration_coverage"], .5)
        self.assertTrue(s["estimated"])

    def test_old_statistics_do_not_invent_threshold_hours_or_record_times(self):
        rows = merge([{"start":0,"end":3600,"mean":-5,"min":-10,"max":0}], {}, 0, 3600)
        s = summarize(rows, 0, 3600, "UTC")
        self.assertEqual(s["exact_seconds"], 0)
        self.assertIsNone(s["min_at"])
        self.assertEqual(s["frost_hours"], 0)

    def test_no_future_information_from_partial_historical_stats(self):
        rows = merge([{"start":0,"end":3600,"mean":1,"min":0,"max":2}], {}, 0, 1800)
        self.assertEqual(rows, [])

    def test_dst_days_are_complete_at_23_and_25_hours(self):
        tz = ZoneInfo("Europe/Berlin")
        for date, hours in (("2026-03-29",23),("2026-10-25",25)):
            start = datetime.fromisoformat(date).replace(tzinfo=tz)
            end = start + timedelta(days=1)
            first,last=start.timestamp(),end.timestamp()
            a=Archive();a.start(first,10);a.advance(last)
            s=summarize(merge([],a.hours,first,last),first,last,"Europe/Berlin")
            self.assertEqual(s["seconds"], hours*3600)
            self.assertEqual(len(s["days"]),1)
            self.assertTrue(s["days"][0]["complete"])
            self.assertEqual(s["complete_days"],1)

    def test_incomplete_day_is_marked_incomplete(self):
        a=Archive();a.start(0,10);a.advance(3600)
        s=summarize(merge([],a.hours,0,3600),0,3600,"UTC")
        self.assertEqual(s["complete_days"],0)

    def test_empty_data_does_not_become_zero_degrees(self):
        s=summarize([],0,3600,"UTC")
        for key in ("mean","min","max","range"):
            self.assertIsNone(s[key])
        self.assertEqual(s["coverage"],0)

    def test_hourly_bins_do_not_create_daily_gap_bridges(self):
        a=Archive();a.start(0,10);a.change(3600,None);a.change(7200,20);a.advance(10800)
        chart=analytics.chart_rows(merge([],a.hours,0,10800),False,"UTC")
        self.assertEqual([p["start"] for p in chart],[0,7200])


class SensorDiscoveryTests(unittest.TestCase):
    def test_equivalent_weather_units_and_legacy_classes(self):
        for unit,device_class in [("Lux", ""), (" lux ", "brightness"), ("LX", "illuminance"), ("lx", None)]:
            with self.subTest(unit=unit,device_class=device_class):
                self.assertEqual(analytics.sensor_kind("sensor.brightness", {"unit_of_measurement":unit,"device_class":device_class}), "illuminance")
                self.assertEqual(analytics.sensor_value("1234",unit,"illuminance"), 1234)
        for unit,device_class,expected in [("KM/H", "", 5), (" km / h ", "wind", 5), ("mps", "wind_strength", 18), (" M/S ", None, 18)]:
            with self.subTest(unit=unit,device_class=device_class):
                self.assertEqual(analytics.sensor_kind("sensor.anemometer", {"unit_of_measurement":unit,"device_class":device_class}), "wind")
                self.assertEqual(analytics.sensor_value("5",unit,"wind"), expected)

    def test_incompatible_measurements_remain_excluded(self):
        for entity,unit,device_class in [("sensor.light","%","brightness"), ("sensor.direction","°","wind"), ("binary_sensor.wind",None,"wind"), ("sensor.current","m/s","current")]:
            self.assertIsNone(analytics.sensor_kind(entity,{"unit_of_measurement":unit,"device_class":device_class}))
        self.assertIsNone(analytics.sensor_value(5,"m/s","illuminance"))
        self.assertIsNone(analytics.sensor_value(5,"lx","wind"))


class ChartIntervalTests(unittest.TestCase):
    def test_daily_chart_points_have_exact_dst_interval_ends(self):
        tz=ZoneInfo("Europe/Berlin")
        for date,hours in [("2026-03-29",23),("2026-10-25",25)]:
            first=datetime.fromisoformat(date).replace(tzinfo=tz)
            last=first+timedelta(days=1)
            archive=Archive();archive.start(first.timestamp(),10);archive.advance(last.timestamp())
            points=analytics.chart_rows(merge([],archive.hours,first.timestamp(),last.timestamp()),True,"Europe/Berlin")
            self.assertEqual(len(points),1)
            self.assertEqual(points[0]["end"]-points[0]["start"],hours*3600)


class HistoryTests(unittest.TestCase):
    def snapshots(self, rows):
        return [SimpleNamespace(state=value, last_updated=datetime.fromtimestamp(at, ZoneInfo("UTC")),
                attributes={"unit_of_measurement":unit}) for at,value,unit in rows]

    def test_initial_raw_history_provides_weighted_stats_thresholds_and_extreme_times(self):
        rows=self.snapshots([(0,"-2","°C"),(900,"10","°C"),(1800,"unavailable","°C"),(2700,"5","°C")])
        a=analytics.history_archive(rows,0,3600,[(0,3600)],"temperature")
        s=summarize(merge([],a.hours,0,3600),0,3600,"UTC")
        self.assertEqual(s["seconds"],2700)
        self.assertEqual(s["mean"],13/3)
        self.assertEqual(s["frost_hours"],.25)
        self.assertEqual(s["max_at"],900)

    def test_recorder_downtime_is_not_bridged(self):
        rows=self.snapshots([(0,"10","°C"),(2700,"20","°C")])
        a=analytics.history_archive(rows,0,3600,[(0,1800),(2400,3600)],"temperature")
        s=summarize(merge([],a.hours,0,3600),0,3600,"UTC")
        self.assertEqual(s["seconds"],2700)
        self.assertAlmostEqual(s["mean"],40/3)
        self.assertIsNone(a.value_at(2100))
        self.assertIsNone(a.value_at(2500))

    def test_disjoint_history_and_live_partial_hour_are_counted_once(self):
        h=Archive();h.start(0,-2);h.advance(1800)
        live=Archive();live.start(1800,10);live.advance(3600)
        hours=analytics.combine_hours(h.hours,live.hours)
        s=summarize(merge([],hours,0,3600),0,3600,"UTC")
        self.assertEqual(s["seconds"],3600)
        self.assertEqual(s["mean"],4)
        self.assertEqual(s["frost_hours"],.5)

    def test_historical_units_are_converted_per_state(self):
        rows=self.snapshots([(0,"32","°F"),(1800,"10","°C")])
        a=analytics.history_archive(rows,0,3600,[(0,3600)],"temperature")
        self.assertEqual(summarize(merge([],a.hours,0,3600),0,3600,"UTC")["mean"],5)

    def test_wind_speed_units_and_invalid_values(self):
        for value,unit,expected in [(1,"m/s",3.6),(1,"km/h",1),(1,"mph",1.609344),(1,"kn",1.852),(1,"ft/s",1.09728)]:
            self.assertAlmostEqual(analytics.sensor_value(value,unit,"wind"),expected)
        for value in ("unknown","unavailable",-1,"nan","inf"):
            self.assertIsNone(analytics.sensor_value(value,"m/s","wind"))
        self.assertIsNone(analytics.sensor_kind("sensor.direction",{"unit_of_measurement":"°"}))
        self.assertIsNone(analytics.sensor_kind("sensor.other",{"unit_of_measurement":"km/h","device_class":"distance"}))

    def test_missing_start_is_not_filled_backwards(self):
        rows=self.snapshots([(1800,"10","°C")])
        a=analytics.history_archive(rows,0,3600,[(0,3600)],"temperature")
        self.assertEqual(summarize(merge([],a.hours,0,3600),0,3600,"UTC")["seconds"],1800)


if __name__ == "__main__":
    unittest.main()
