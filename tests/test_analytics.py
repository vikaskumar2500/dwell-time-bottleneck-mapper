import unittest

from dwell_mapper.analytics import AnalyticsError, TrafficAnalyzer
from dwell_mapper.config import parse_store_config
from dwell_mapper.models import Observation


def analytics_config(bottleneck_seconds=3, dead_zone_max_visits=0, track_ttl_seconds=10):
    return parse_store_config({
        "store_id": "analytics-test",
        "frame": {"width": 100, "height": 100},
        "zones": [
            {"id": "a", "name": "A", "polygon": [[0, 0], [49, 0], [49, 99], [0, 99]]},
            {"id": "b", "name": "B", "polygon": [[50, 0], [99, 0], [99, 99], [50, 99]]},
        ],
        "analytics": {
            "heatmap_cell_px": 10,
            "bottleneck_occupancy": 2,
            "bottleneck_min_seconds": bottleneck_seconds,
            "dead_zone_max_visits": dead_zone_max_visits,
            "track_ttl_seconds": track_ttl_seconds,
        },
    })


def obs(track_id, x, y=10):
    return Observation(track_id, x, y)


class AnalyticsTests(unittest.TestCase):
    def test_dwell_occupancy_heat_and_transition(self):
        analyzer = TrafficAnalyzer(analytics_config())
        analyzer.update(0, [obs("1", 10)])
        analyzer.update(2, [obs("1", 10)])
        analyzer.update(5, [obs("1", 60)])
        analyzer.update(8, [obs("1", 60)])
        analyzer.finalize()

        report = analyzer.report()
        self.assertEqual(report["zones"]["a"]["mean_dwell_seconds"], 5)
        self.assertEqual(report["zones"]["b"]["mean_dwell_seconds"], 3)
        self.assertEqual(report["zones"]["a"]["occupancy_seconds"], 5)
        self.assertEqual(report["zones"]["b"]["occupancy_seconds"], 3)
        self.assertEqual(report["transitions"], [{"from": "a", "to": "b", "count": 1}])
        self.assertEqual(analyzer.heatmap[1][1], 5)
        self.assertEqual(analyzer.heatmap[1][6], 3)

    def test_exit_and_reentry_create_two_visits(self):
        analyzer = TrafficAnalyzer(analytics_config())
        analyzer.update(0, [obs("1", 10)])
        analyzer.update(1, [obs("1", 49.5)])
        analyzer.update(2, [obs("1", 10)])
        analyzer.update(4, [obs("1", 10)])
        analyzer.finalize()
        metrics = analyzer.report()["zones"]["a"]
        self.assertEqual(metrics["visits"], 2)
        self.assertEqual(metrics["total_dwell_seconds"], 3)

    def test_expiry_closes_visit_at_last_seen(self):
        analyzer = TrafficAnalyzer(analytics_config(track_ttl_seconds=2))
        analyzer.update(0, [obs("1", 10)])
        analyzer.update(1, [obs("1", 10)])
        analyzer.update(2, [])
        analyzer.update(4, [])
        self.assertEqual(analyzer.report()["zones"]["a"]["total_dwell_seconds"], 1)

    def test_bottleneck_requires_continuous_duration(self):
        analyzer = TrafficAnalyzer(analytics_config(bottleneck_seconds=3))
        pair = [obs("1", 10), obs("2", 20)]
        analyzer.update(0, pair)
        analyzer.update(2, pair)
        analyzer.update(3, [obs("1", 10)])
        analyzer.update(4, [obs("1", 10)])
        analyzer.update(5, pair)
        analyzer.update(8, pair)
        report = analyzer.report()
        alerts = {(item["type"], item["zone_id"]) for item in report["alerts"]}
        self.assertIn(("bottleneck", "a"), alerts)
        self.assertEqual(report["zones"]["a"]["bottleneck_seconds"], 6)
        self.assertEqual(report["zones"]["a"]["longest_bottleneck_seconds"], 3)

    def test_unused_zone_is_dead_zone(self):
        analyzer = TrafficAnalyzer(analytics_config())
        analyzer.update(0, [obs("1", 10)])
        analyzer.update(1, [obs("1", 10)])
        alerts = {(item["type"], item["zone_id"]) for item in analyzer.report()["alerts"]}
        self.assertIn(("dead_zone", "b"), alerts)

    def test_rejects_invalid_stream_records(self):
        analyzer = TrafficAnalyzer(analytics_config())
        analyzer.update(2, [])
        with self.assertRaisesRegex(AnalyticsError, "non-decreasing"):
            analyzer.update(1, [])

        duplicate = TrafficAnalyzer(analytics_config())
        with self.assertRaisesRegex(AnalyticsError, "only once"):
            duplicate.update(0, [obs("1", 10), obs("1", 20)])


if __name__ == "__main__":
    unittest.main()
