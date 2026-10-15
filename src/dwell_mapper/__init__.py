"""Core spatial models for the Dwell-Time & Bottleneck Mapper."""

from .config import ConfigError, load_store_config
from .geometry import locate_zone, point_in_polygon
from .models import AnalyticsSettings, FrameSize, Point, StoreConfig, Zone

__all__ = [
    "AnalyticsSettings",
    "ConfigError",
    "FrameSize",
    "Point",
    "StoreConfig",
    "Zone",
    "load_store_config",
    "locate_zone",
    "point_in_polygon",
]

__version__ = "0.2.0"

