"""Numerical regression tests; no Home Assistant installation required."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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
            self.assertEqual(s["heating_degree_days"],10)

    def test_incomplete_day_has_no_heating_degree_days(self):
        a=Archive();a.start(0,10);a.advance(3600)
        s=summarize(merge([],a.hours,0,3600),0,3600,"UTC")
        self.assertEqual(s["heating_degree_days"],0)

    def test_empty_data_does_not_become_zero_degrees(self):
        s=summarize([],0,3600,"UTC")
        for key in ("mean","min","max","range"):
            self.assertIsNone(s[key])
        self.assertEqual(s["coverage"],0)

    def test_hourly_bins_do_not_create_daily_gap_bridges(self):
        a=Archive();a.start(0,10);a.change(3600,None);a.change(7200,20);a.advance(10800)
        chart=analytics.chart_rows(merge([],a.hours,0,10800),False,"UTC")
        self.assertEqual([p["start"] for p in chart],[0,7200])


if __name__ == "__main__":
    unittest.main()
