import unittest

from dwell_mapper.geometry import locate_zone, point_in_polygon, polygon_area
from dwell_mapper.models import Zone


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.square = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))

    def test_inside_and_outside(self):
        self.assertTrue(point_in_polygon((5, 5), self.square))
        self.assertFalse(point_in_polygon((11, 5), self.square))

    def test_edges_and_vertices_are_inside(self):
        self.assertTrue(point_in_polygon((10, 5), self.square))
        self.assertTrue(point_in_polygon((0, 0), self.square))

    def test_concave_polygon(self):
        polygon = ((0, 0), (6, 0), (6, 6), (3, 3), (0, 6))
        self.assertTrue(point_in_polygon((1, 4), polygon))
        self.assertFalse(point_in_polygon((3, 5), polygon))

    def test_area_is_independent_of_winding(self):
        self.assertEqual(polygon_area(self.square), 100)
        self.assertEqual(polygon_area(tuple(reversed(self.square))), 100)

    def test_locate_zone(self):
        zone = Zone("a", "A", self.square)
        self.assertEqual(locate_zone((5, 5), [zone]), zone)
        self.assertIsNone(locate_zone((20, 20), [zone]))


if __name__ == "__main__":
    unittest.main()

