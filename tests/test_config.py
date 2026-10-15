import copy
import unittest
from pathlib import Path

from dwell_mapper.config import ConfigError, load_store_config, parse_store_config


def valid_config():
    return {
        "store_id": "test-store",
        "frame": {"width": 100, "height": 80},
        "zones": [
            {
                "id": "entrance",
                "name": "Entrance",
                "polygon": [[0, 40], [30, 40], [30, 80], [0, 80]],
            }
        ],
        "analytics": {
            "heatmap_cell_px": 10,
            "bottleneck_occupancy": 3,
            "bottleneck_min_seconds": 4,
            "dead_zone_max_visits": 1,
            "track_ttl_seconds": 2,
        },
    }


class ConfigTests(unittest.TestCase):
    def test_sample_config_is_valid(self):
        path = Path(__file__).resolve().parents[1] / "config/store.sample.json"
        config = load_store_config(str(path))
        self.assertEqual(config.store_id, "demo-store-01")
        self.assertEqual(len(config.zones), 4)
        self.assertEqual(config.zone_at((100, 600)).id, "entrance")

    def test_missing_required_field(self):
        raw = valid_config()
        del raw["frame"]
        with self.assertRaisesRegex(ConfigError, "missing: frame"):
            parse_store_config(raw)

    def test_duplicate_zone_id(self):
        raw = valid_config()
        raw["zones"].append(copy.deepcopy(raw["zones"][0]))
        with self.assertRaisesRegex(ConfigError, "duplicate zone id"):
            parse_store_config(raw)

    def test_polygon_outside_frame(self):
        raw = valid_config()
        raw["zones"][0]["polygon"][1] = [101, 40]
        with self.assertRaisesRegex(ConfigError, "outside"):
            parse_store_config(raw)

    def test_polygon_needs_positive_area(self):
        raw = valid_config()
        raw["zones"][0]["polygon"] = [[0, 0], [1, 1], [2, 2]]
        with self.assertRaisesRegex(ConfigError, "positive area"):
            parse_store_config(raw)

    def test_rejects_boolean_as_number(self):
        raw = valid_config()
        raw["analytics"]["heatmap_cell_px"] = True
        with self.assertRaisesRegex(ConfigError, "must be an integer"):
            parse_store_config(raw)

    def test_rejects_negative_threshold(self):
        raw = valid_config()
        raw["analytics"]["track_ttl_seconds"] = -1
        with self.assertRaisesRegex(ConfigError, ">= 0"):
            parse_store_config(raw)


if __name__ == "__main__":
    unittest.main()
