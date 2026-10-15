import json
import tempfile
import unittest
from pathlib import Path

from dwell_mapper.cli import analyze
from dwell_mapper.synthetic import generate_demo


class DemoTests(unittest.TestCase):
    def test_demo_produces_expected_business_events_and_exports(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            tracks = Path(directory) / "tracks.jsonl"
            output = Path(directory) / "report"
            generate_demo(str(tracks))
            report = analyze(
                str(project / "config/store.sample.json"),
                str(tracks),
                str(output),
            )
            persisted = json.loads((output / "report.json").read_text())
            self.assertTrue((output / "zone_metrics.csv").is_file())
            self.assertTrue((output / "heatmap.csv").is_file())

        alerts = {(item["type"], item["zone_id"]) for item in report["alerts"]}
        self.assertIn(("bottleneck", "checkout"), alerts)
        self.assertIn(("dead_zone", "promo"), alerts)
        self.assertEqual(report, persisted)
        self.assertEqual(report["zones"]["checkout"]["visits"], 4)
        self.assertEqual(report["transitions"][0]["count"], 4)
        self.assertFalse(report["privacy"]["track_ids_persisted"])


if __name__ == "__main__":
    unittest.main()
