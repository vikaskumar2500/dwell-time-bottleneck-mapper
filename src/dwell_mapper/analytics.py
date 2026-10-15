from collections import Counter
from statistics import mean, median
from typing import Dict, Iterable, List, Optional, Tuple

from .models import Observation, StoreConfig, TrackState, Visit, ZoneMetrics


class AnalyticsError(ValueError):
    """Raised when an observation stream violates the analytics contract."""


class TrafficAnalyzer:
    """Turn anonymous tracker observations into aggregate spatial metrics."""

    def __init__(self, config: StoreConfig):
        self.config = config
        cell = config.analytics.heatmap_cell_px
        rows = (config.frame.height + cell - 1) // cell
        columns = (config.frame.width + cell - 1) // cell
        self.heatmap: List[List[float]] = [[0.0] * columns for _ in range(rows)]
        self.tracks: Dict[str, TrackState] = {}
        self.zone_metrics = {zone.id: ZoneMetrics() for zone in config.zones}
        self.transitions: Counter[Tuple[str, str]] = Counter()
        self.completed_visits: List[Visit] = []
        self.started_at: Optional[float] = None
        self.last_timestamp: Optional[float] = None

    def update(self, timestamp: float, observations: Iterable[Observation]) -> None:
        if timestamp < 0:
            raise AnalyticsError("timestamp must be non-negative")
        if self.last_timestamp is not None and timestamp < self.last_timestamp:
            raise AnalyticsError("timestamps must be non-decreasing")

        batch = list(observations)
        ids = [observation.track_id for observation in batch]
        if len(ids) != len(set(ids)):
            raise AnalyticsError("a track_id may appear only once per timestamp")
        for observation in batch:
            if not observation.track_id:
                raise AnalyticsError("track_id must be non-empty")
            if not (0 <= observation.x <= self.config.frame.width and 0 <= observation.y <= self.config.frame.height):
                raise AnalyticsError(f"track {observation.track_id} is outside the configured frame")

        if self.started_at is None:
            self.started_at = timestamp
        if self.last_timestamp is not None:
            self._accumulate_visible_interval(timestamp - self.last_timestamp)

        for state in self.tracks.values():
            state.visible = False
        self._expire_tracks(timestamp)

        for observation in batch:
            zone = self.config.zone_at(observation.point)
            zone_id = zone.id if zone else None
            state = self.tracks.get(observation.track_id)
            if state is None:
                state = TrackState(timestamp, observation.point)
                self.tracks[observation.track_id] = state
            self._move_track(observation.track_id, state, zone_id, timestamp)
            state.last_seen_at = timestamp
            state.last_point = observation.point
            state.visible = True
            if state.active_visit is not None:
                state.active_visit.last_seen_at = timestamp

        self.last_timestamp = timestamp

    def _accumulate_visible_interval(self, duration: float) -> None:
        if duration <= 0:
            return
        occupancy = Counter(
            state.current_zone
            for state in self.tracks.values()
            if state.visible and state.current_zone is not None
        )
        cell = self.config.analytics.heatmap_cell_px
        for state in self.tracks.values():
            if not state.visible:
                continue
            x, y = state.last_point
            row = min(int(y // cell), len(self.heatmap) - 1)
            column = min(int(x // cell), len(self.heatmap[0]) - 1)
            self.heatmap[row][column] += duration

        threshold = self.config.analytics.bottleneck_occupancy
        for zone_id, metrics in self.zone_metrics.items():
            count = occupancy[zone_id]
            metrics.occupancy_seconds += count * duration
            metrics.max_occupancy = max(metrics.max_occupancy, count)
            if count >= threshold:
                metrics.bottleneck_seconds += duration
                metrics.bottleneck_streak_seconds += duration
                metrics.longest_bottleneck_seconds = max(
                    metrics.longest_bottleneck_seconds,
                    metrics.bottleneck_streak_seconds,
                )
            else:
                metrics.bottleneck_streak_seconds = 0.0

    def _move_track(self, track_id: str, state: TrackState, zone_id: Optional[str], timestamp: float) -> None:
        if state.current_zone == zone_id:
            return
        previous_zone = state.current_zone
        if state.active_visit is not None:
            state.active_visit.exited_at = timestamp
            self._close_visit(state.active_visit)
            state.active_visit = None
        if previous_zone is not None and zone_id is not None:
            self.transitions[(previous_zone, zone_id)] += 1
        state.current_zone = zone_id
        if zone_id is not None:
            state.active_visit = Visit(track_id, zone_id, timestamp, timestamp)
            metrics = self.zone_metrics[zone_id]
            metrics.visits += 1
            metrics.unique_tracks.add(track_id)

    def _close_visit(self, visit: Visit) -> None:
        self.completed_visits.append(visit)
        self.zone_metrics[visit.zone_id].dwell_seconds.append(visit.duration)

    def _expire_tracks(self, timestamp: float) -> None:
        ttl = self.config.analytics.track_ttl_seconds
        expired = [
            track_id
            for track_id, state in self.tracks.items()
            if timestamp - state.last_seen_at > ttl
        ]
        for track_id in expired:
            state = self.tracks.pop(track_id)
            if state.active_visit is not None:
                state.active_visit.exited_at = state.last_seen_at
                self._close_visit(state.active_visit)

    def finalize(self) -> None:
        for state in self.tracks.values():
            if state.active_visit is not None:
                state.active_visit.exited_at = state.last_seen_at
                self._close_visit(state.active_visit)
                state.active_visit = None

    def report(self) -> Dict[str, object]:
        zones: Dict[str, object] = {}
        alerts = []
        for zone in self.config.zones:
            metrics = self.zone_metrics[zone.id]
            dwell = metrics.dwell_seconds
            zones[zone.id] = {
                "name": zone.name,
                "visits": metrics.visits,
                "unique_visitors": len(metrics.unique_tracks),
                "mean_dwell_seconds": round(mean(dwell), 2) if dwell else 0.0,
                "median_dwell_seconds": round(median(dwell), 2) if dwell else 0.0,
                "total_dwell_seconds": round(sum(dwell), 2),
                "occupancy_seconds": round(metrics.occupancy_seconds, 2),
                "max_occupancy": metrics.max_occupancy,
                "bottleneck_seconds": round(metrics.bottleneck_seconds, 2),
                "longest_bottleneck_seconds": round(metrics.longest_bottleneck_seconds, 2),
            }
            if (
                metrics.longest_bottleneck_seconds > 0
                and metrics.longest_bottleneck_seconds >= self.config.analytics.bottleneck_min_seconds
            ):
                alerts.append({
                    "type": "bottleneck",
                    "zone_id": zone.id,
                    "evidence_seconds": round(metrics.longest_bottleneck_seconds, 2),
                })
            if metrics.visits <= self.config.analytics.dead_zone_max_visits:
                alerts.append({"type": "dead_zone", "zone_id": zone.id, "visits": metrics.visits})

        duration = 0.0
        if self.started_at is not None and self.last_timestamp is not None:
            duration = self.last_timestamp - self.started_at
        peak = max((max(row) for row in self.heatmap), default=0.0)
        occupied_cells = sum(value > 0 for row in self.heatmap for value in row)
        return {
            "store_id": self.config.store_id,
            "analysis_duration_seconds": round(duration, 2),
            "zones": zones,
            "transitions": [
                {"from": source, "to": target, "count": count}
                for (source, target), count in self.transitions.most_common()
            ],
            "alerts": alerts,
            "heatmap": {
                "rows": len(self.heatmap),
                "columns": len(self.heatmap[0]),
                "cell_size_px": self.config.analytics.heatmap_cell_px,
                "peak_seconds": round(peak, 2),
                "occupied_cells": occupied_cells,
            },
            "privacy": {
                "frames_stored": False,
                "biometrics_used": False,
                "track_ids_persisted": False,
            },
        }

    def normalized_heatmap(self) -> List[List[float]]:
        peak = max((max(row) for row in self.heatmap), default=0.0)
        if peak == 0:
            return [row.copy() for row in self.heatmap]
        return [[value / peak for value in row] for row in self.heatmap]
