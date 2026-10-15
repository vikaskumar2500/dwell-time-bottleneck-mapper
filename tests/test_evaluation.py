import json
import tempfile
import unittest
from pathlib import Path

from dwell_mapper.evaluation import EvaluationError, evaluate_files, evaluate_report


def fixture(visits=2, dwell=4.0, transition_count=1, alerts=None):
    return {
        "zones": {"aisle": {"visits": visits, "mean_dwell_seconds": dwell}},
        "transitions": [{"from": "entry", "to": "aisle", "count": transition_count}],
        "alerts": alerts if alerts is not None else [{"type": "dead_zone", "zone_id": "aisle"}],
    }


class EvaluationTests(unittest.TestCase):
    def test_perfect_report_has_zero_error_and_perfect_alert_scores(self):
        metrics = evaluate_report(fixture(), fixture())
        self.assertEqual(metrics["visit_count_mae"], 0.0)
        self.assertEqual(metrics["mean_dwell_mae_seconds"], 0.0)
        self.assertEqual(metrics["transition_count_mae"], 0.0)
        self.assertEqual(metrics["alert_f1"], 1.0)

    def test_imperfect_report_calculates_errors_and_alert_scores(self):
        predicted = fixture(visits=4, dwell=7.0, transition_count=3, alerts=[])
        metrics = evaluate_report(predicted, fixture())
        self.assertEqual(metrics["visit_count_mae"], 2.0)
        self.assertEqual(metrics["mean_dwell_mae_seconds"], 3.0)
        self.assertEqual(metrics["transition_count_mae"], 2.0)
        self.assertEqual(metrics["alert_f1"], 0.0)

    def test_file_evaluation_persists_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, truth, output = root / "report.json", root / "truth.json", root / "metrics.json"
            report.write_text(json.dumps(fixture()), encoding="utf-8")
            truth.write_text(json.dumps(fixture()), encoding="utf-8")
            metrics = evaluate_files(str(report), str(truth), str(output))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), metrics)

    def test_zone_mismatch_is_rejected(self):
        invalid = fixture()
        invalid["zones"] = {"other": {"visits": 1, "mean_dwell_seconds": 1}}
        with self.assertRaisesRegex(EvaluationError, "same zone IDs"):
            evaluate_report(invalid, fixture())


if __name__ == "__main__":
    unittest.main()
