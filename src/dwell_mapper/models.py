from dataclasses import dataclass
from typing import Optional, Tuple

Point = Tuple[float, float]


@dataclass(frozen=True)
class FrameSize:
    width: int
    height: int


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    polygon: Tuple[Point, ...]


@dataclass(frozen=True)
class AnalyticsSettings:
    heatmap_cell_px: int
    bottleneck_occupancy: int
    bottleneck_min_seconds: float
    dead_zone_max_visits: int
    track_ttl_seconds: float


@dataclass(frozen=True)
class StoreConfig:
    store_id: str
    frame: FrameSize
    zones: Tuple[Zone, ...]
    analytics: AnalyticsSettings

    def zone_at(self, point: Point) -> Optional[Zone]:
        # Local import avoids coupling the domain models to implementation details.
        from .geometry import point_in_polygon

        return next((zone for zone in self.zones if point_in_polygon(point, zone.polygon)), None)

