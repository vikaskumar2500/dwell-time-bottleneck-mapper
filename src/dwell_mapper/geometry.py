from typing import Iterable, Optional, Sequence

from .models import Point, Zone

EPSILON = 1e-9


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    return (
        abs(cross) <= EPSILON
        and min(x1, x2) - EPSILON <= x <= max(x1, x2) + EPSILON
        and min(y1, y2) - EPSILON <= y <= max(y1, y2) + EPSILON
    )


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """Return whether a point is inside a polygon; boundary points are included."""
    if len(polygon) < 3:
        return False

    inside = False
    previous = polygon[-1]
    for current in polygon:
        if _point_on_segment(point, previous, current):
            return True
        x, y = point
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def polygon_area(polygon: Sequence[Point]) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1])
        )
    ) / 2.0


def locate_zone(point: Point, zones: Iterable[Zone]) -> Optional[Zone]:
    """Return the zone containing a point, or None when it is outside all zones."""
    return next((zone for zone in zones if point_in_polygon(point, zone.polygon)), None)

