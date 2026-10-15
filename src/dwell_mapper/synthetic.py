import json
from pathlib import Path
from typing import Dict, List, Tuple

Point = Tuple[float, float]


def _position(elapsed: int) -> Point:
    if elapsed <= 1:
        return 100.0, 600.0  # entrance
    if elapsed <= 6:
        return 430.0, 240.0  # produce
    return 1060.0, 500.0  # checkout


def generate_demo(path: str) -> None:
    """Create a deterministic scenario with a queue and an unused promo zone."""
    starts = {"shopper-1": 0, "shopper-2": 2, "shopper-3": 4, "shopper-4": 6}
    records: List[Dict[str, object]] = []
    for timestamp in range(26):
        observations = []
        for track_id, start in starts.items():
            elapsed = timestamp - start
            if 0 <= elapsed <= 16:
                x, y = _position(elapsed)
                observations.append({"track_id": track_id, "x": x, "y": y})
        records.append({"timestamp": float(timestamp), "observations": observations})

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
