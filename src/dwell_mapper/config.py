import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from .geometry import polygon_area
from .models import AnalyticsSettings, FrameSize, Point, StoreConfig, VisionSettings, Zone


class ConfigError(ValueError):
    """Raised when a store configuration cannot be used safely."""


REQUIRED_ANALYTICS = {
    "heatmap_cell_px",
    "bottleneck_occupancy",
    "bottleneck_min_seconds",
    "dead_zone_max_visits",
    "track_ttl_seconds",
}


def _mapping(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be an object")
    return value


def _number(value: Any, label: str, *, integer: bool = False, minimum: float = 0) -> float:
    expected = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, expected):
        article_and_kind = "an integer" if integer else "a number"
        raise ConfigError(f"{label} must be {article_and_kind}")
    if not math.isfinite(float(value)) or value < minimum:
        raise ConfigError(f"{label} must be finite and >= {minimum}")
    return value


def _point(value: Any, label: str, frame: FrameSize) -> Point:
    if not isinstance(value, list) or len(value) != 2:
        raise ConfigError(f"{label} must be [x, y]")
    x = float(_number(value[0], f"{label}.x"))
    y = float(_number(value[1], f"{label}.y"))
    if x > frame.width or y > frame.height:
        raise ConfigError(f"{label} lies outside the configured frame")
    return x, y


def _require_keys(data: Dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = sorted(set(keys) - set(data))
    if missing:
        raise ConfigError(f"{label} is missing: {', '.join(missing)}")


def parse_store_config(raw: Any) -> StoreConfig:
    data = _mapping(raw, "config")
    _require_keys(data, {"store_id", "frame", "zones", "analytics"}, "config")
    if not isinstance(data["store_id"], str) or not data["store_id"].strip():
        raise ConfigError("store_id must be a non-empty string")

    frame_data = _mapping(data["frame"], "frame")
    _require_keys(frame_data, {"width", "height"}, "frame")
    frame = FrameSize(
        int(_number(frame_data["width"], "frame.width", integer=True, minimum=1)),
        int(_number(frame_data["height"], "frame.height", integer=True, minimum=1)),
    )

    if not isinstance(data["zones"], list) or not data["zones"]:
        raise ConfigError("zones must be a non-empty array")
    zones = []
    zone_ids = set()
    for index, item in enumerate(data["zones"]):
        zone_data = _mapping(item, f"zones[{index}]")
        _require_keys(zone_data, {"id", "name", "polygon"}, f"zones[{index}]")
        zone_id = zone_data["id"]
        name = zone_data["name"]
        if not isinstance(zone_id, str) or not zone_id.strip():
            raise ConfigError(f"zones[{index}].id must be a non-empty string")
        if zone_id in zone_ids:
            raise ConfigError(f"duplicate zone id: {zone_id}")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"zones[{index}].name must be a non-empty string")
        polygon_data = zone_data["polygon"]
        if not isinstance(polygon_data, list) or len(polygon_data) < 3:
            raise ConfigError(f"zones[{index}].polygon needs at least three points")
        polygon = tuple(_point(value, f"zones[{index}].polygon[{point_index}]", frame) for point_index, value in enumerate(polygon_data))
        if polygon_area(polygon) <= 0:
            raise ConfigError(f"zones[{index}].polygon must have a positive area")
        zones.append(Zone(zone_id, name, polygon))
        zone_ids.add(zone_id)

    analytics_data = _mapping(data["analytics"], "analytics")
    _require_keys(analytics_data, REQUIRED_ANALYTICS, "analytics")
    analytics = AnalyticsSettings(
        heatmap_cell_px=int(_number(analytics_data["heatmap_cell_px"], "analytics.heatmap_cell_px", integer=True, minimum=1)),
        bottleneck_occupancy=int(_number(analytics_data["bottleneck_occupancy"], "analytics.bottleneck_occupancy", integer=True, minimum=1)),
        bottleneck_min_seconds=float(_number(analytics_data["bottleneck_min_seconds"], "analytics.bottleneck_min_seconds", minimum=0)),
        dead_zone_max_visits=int(_number(analytics_data["dead_zone_max_visits"], "analytics.dead_zone_max_visits", integer=True, minimum=0)),
        track_ttl_seconds=float(_number(analytics_data["track_ttl_seconds"], "analytics.track_ttl_seconds", minimum=0)),
    )

    vision_data = _mapping(data.get("vision", {}), "vision")
    defaults = VisionSettings()
    model = vision_data.get("model", defaults.model)
    tracker = vision_data.get("tracker", defaults.tracker)
    if not isinstance(model, str) or not model.strip():
        raise ConfigError("vision.model must be a non-empty string")
    if not isinstance(tracker, str) or not tracker.strip():
        raise ConfigError("vision.tracker must be a non-empty string")
    confidence = float(_number(vision_data.get("confidence", defaults.confidence), "vision.confidence"))
    iou = float(_number(vision_data.get("iou", defaults.iou), "vision.iou"))
    if confidence > 1 or iou > 1:
        raise ConfigError("vision confidence and iou must be <= 1")
    vision = VisionSettings(
        model=model.strip(),
        tracker=tracker.strip(),
        confidence=confidence,
        iou=iou,
        image_size=int(_number(vision_data.get("image_size", defaults.image_size), "vision.image_size", integer=True, minimum=32)),
    )
    return StoreConfig(data["store_id"].strip(), frame, tuple(zones), analytics, vision)


def load_store_config(path: str) -> StoreConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    return parse_store_config(raw)

