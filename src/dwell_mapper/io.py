import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

from .models import Observation


class ObservationError(ValueError):
    """Raised when an observation file violates the input contract."""


def read_observations(path: str) -> Iterator[Tuple[float, List[Observation]]]:
    try:
        source = Path(path).open(encoding="utf-8")
    except OSError as exc:
        raise ObservationError(f"cannot read observations: {path}") from exc
    with source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                timestamp = float(record["timestamp"])
                raw_observations = record["observations"]
                if not math.isfinite(timestamp) or not isinstance(raw_observations, list):
                    raise ValueError
                observations = []
                for item in raw_observations:
                    if not isinstance(item["track_id"], str) or not item["track_id"]:
                        raise ValueError
                    observations.append(Observation(item["track_id"], float(item["x"]), float(item["y"])))
                if any(not math.isfinite(value) for item in observations for value in (item.x, item.y)):
                    raise ValueError
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ObservationError(f"invalid observation record on line {line_number}") from exc
            yield timestamp, observations


def write_outputs(report: Dict[str, object], heatmap: List[List[float]], output_dir: str) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    zone_rows = report["zones"]
    with (target / "zone_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["zone_id"] + list(next(iter(zone_rows.values())).keys())
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for zone_id, metrics in zone_rows.items():
            writer.writerow({"zone_id": zone_id, **metrics})

    peak = max((max(row) for row in heatmap), default=0.0)
    with (target / "heatmap.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["row", "column", "seconds", "normalized"])
        for row_index, row in enumerate(heatmap):
            for column_index, seconds in enumerate(row):
                if seconds > 0:
                    writer.writerow([
                        row_index,
                        column_index,
                        round(seconds, 3),
                        round(seconds / peak, 6) if peak else 0.0,
                    ])
