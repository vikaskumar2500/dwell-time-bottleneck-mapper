from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

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
class VisionSettings:
    model: str = "yolo11n.pt"
    tracker: str = "bytetrack.yaml"
    confidence: float = 0.35
    iou: float = 0.7
    image_size: int = 640


@dataclass(frozen=True)
class StoreConfig:
    store_id: str
    frame: FrameSize
    zones: Tuple[Zone, ...]
    analytics: AnalyticsSettings
    vision: VisionSettings = VisionSettings()

    def zone_at(self, point: Point) -> Optional[Zone]:
        # Local import avoids coupling the domain models to implementation details.
        from .geometry import point_in_polygon

        return next((zone for zone in self.zones if point_in_polygon(point, zone.polygon)), None)


@dataclass(frozen=True)
class Observation:
    track_id: str
    x: float
    y: float

    @property
    def point(self) -> Point:
        return self.x, self.y


@dataclass
class Visit:
    track_id: str
    zone_id: str
    entered_at: float
    last_seen_at: float
    exited_at: Optional[float] = None

    @property
    def duration(self) -> float:
        end = self.exited_at if self.exited_at is not None else self.last_seen_at
        return max(0.0, end - self.entered_at)


@dataclass
class TrackState:
    last_seen_at: float
    last_point: Point
    current_zone: Optional[str] = None
    active_visit: Optional[Visit] = None
    visible: bool = True


@dataclass
class ZoneMetrics:
    visits: int = 0
    unique_tracks: Set[str] = field(default_factory=set)
    dwell_seconds: List[float] = field(default_factory=list)
    occupancy_seconds: float = 0.0
    max_occupancy: int = 0
    bottleneck_seconds: float = 0.0
    bottleneck_streak_seconds: float = 0.0
    longest_bottleneck_seconds: float = 0.0

