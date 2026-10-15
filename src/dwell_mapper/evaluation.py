import json
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, Mapping, Set, Tuple


class EvaluationError(ValueError):
    """Raised when an evaluation file does not match the expected schema."""


AlertKey = Tuple[str, str]
TransitionKey = Tuple[str, str]


def _load_json(path: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvaluationError(f"{path} must contain a JSON object")
    return value


def _zones(document: Mapping[str, object], label: str) -> Mapping[str, object]:
    zones = document.get("zones")
    if not isinstance(zones, dict) or not zones:
        raise EvaluationError(f"{label}.zones must be a non-empty object")
    return zones


def _number(record: object, field: str, label: str) -> float:
    if not isinstance(record, dict):
        raise EvaluationError(f"{label} must be an object")
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise EvaluationError(f"{label}.{field} must be a non-negative number")
    return float(value)


def _transitions(document: Mapping[str, object], label: str) -> Dict[TransitionKey, float]:
    records = document.get("transitions", [])
    if not isinstance(records, list):
        raise EvaluationError(f"{label}.transitions must be an array")
    result: Dict[TransitionKey, float] = {}
    for index, record in enumerate(records):
        item_label = f"{label}.transitions[{index}]"
        if not isinstance(record, dict):
            raise EvaluationError(f"{item_label} must be an object")
        source, target = record.get("from"), record.get("to")
        if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
            raise EvaluationError(f"{item_label} requires non-empty from and to values")
        result[(source, target)] = _number(record, "count", item_label)
    return result


def _alerts(document: Mapping[str, object], label: str) -> Set[AlertKey]:
    records = document.get("alerts", [])
    if not isinstance(records, list):
        raise EvaluationError(f"{label}.alerts must be an array")
    result: Set[AlertKey] = set()
    for index, record in enumerate(records):
        item_label = f"{label}.alerts[{index}]"
        if not isinstance(record, dict):
            raise EvaluationError(f"{item_label} must be an object")
        alert_type, zone_id = record.get("type"), record.get("zone_id")
        if not isinstance(alert_type, str) or not alert_type or not isinstance(zone_id, str) or not zone_id:
            raise EvaluationError(f"{item_label} requires non-empty type and zone_id values")
        result.add((alert_type, zone_id))
    return result


def _mae(keys: Iterable[object], predicted: Mapping[object, float], expected: Mapping[object, float]) -> float:
    values = [abs(predicted.get(key, 0.0) - expected.get(key, 0.0)) for key in keys]
    return mean(values) if values else 0.0


def evaluate_report(report: Mapping[str, object], ground_truth: Mapping[str, object]) -> Dict[str, object]:
    predicted_zones = _zones(report, "report")
    expected_zones = _zones(ground_truth, "ground_truth")
    if set(predicted_zones) != set(expected_zones):
        raise EvaluationError("report and ground truth must contain the same zone IDs")

    zone_ids = sorted(expected_zones)
    predicted_visits = {
        zone: _number(predicted_zones[zone], "visits", f"report.zones.{zone}") for zone in zone_ids
    }
    expected_visits = {
        zone: _number(expected_zones[zone], "visits", f"ground_truth.zones.{zone}") for zone in zone_ids
    }
    predicted_dwell = {
        zone: _number(predicted_zones[zone], "mean_dwell_seconds", f"report.zones.{zone}") for zone in zone_ids
    }
    expected_dwell = {
        zone: _number(expected_zones[zone], "mean_dwell_seconds", f"ground_truth.zones.{zone}") for zone in zone_ids
    }

    predicted_transitions = _transitions(report, "report")
    expected_transitions = _transitions(ground_truth, "ground_truth")
    transition_keys = set(predicted_transitions) | set(expected_transitions)
    predicted_alerts = _alerts(report, "report")
    expected_alerts = _alerts(ground_truth, "ground_truth")
    true_positives = len(predicted_alerts & expected_alerts)
    precision = true_positives / len(predicted_alerts) if predicted_alerts else float(not expected_alerts)
    recall = true_positives / len(expected_alerts) if expected_alerts else float(not predicted_alerts)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "scope": "aggregate business metrics",
        "zone_count": len(zone_ids),
        "visit_count_mae": round(_mae(zone_ids, predicted_visits, expected_visits), 4),
        "mean_dwell_mae_seconds": round(_mae(zone_ids, predicted_dwell, expected_dwell), 4),
        "transition_count_mae": round(
            _mae(transition_keys, predicted_transitions, expected_transitions), 4
        ),
        "alert_precision": round(precision, 4),
        "alert_recall": round(recall, 4),
        "alert_f1": round(f1, 4),
    }


def evaluate_files(report_path: str, ground_truth_path: str, output_path: str) -> Dict[str, object]:
    metrics = evaluate_report(_load_json(report_path), _load_json(ground_truth_path))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics
