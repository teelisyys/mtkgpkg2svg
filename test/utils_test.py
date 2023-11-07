import logging
import unittest
from typing import Dict

from mtkgpkg2svg.utils import (
    intersection_point,
    perpendicular_distance,
    sutherland_hodgman,
    Point,
)

logging.basicConfig(level=logging.WARN)


def is_close(expected: float, actual: float, epsilon: float):
    return expected - epsilon < actual < expected + epsilon


def is_point_close(expected: Point, actual: Point, epsilon: float):
    return is_close(expected.x, actual.x, epsilon) and is_close(
        expected.y, actual.y, epsilon
    )


def get_points() -> Dict[str, Point]:
    """Returns points like:
    A B C
    D E F
    G H I"""

    return {
        # Row 1
        "A": Point(-1, 1),
        "B": Point(0, 1),
        "C": Point(1, 1),
        # Row 2
        "D": Point(-1, 0),
        "E": Point(0, 0),
        "F": Point(1, 0),
        # Row 3
        "G": Point(-1, -1),
        "H": Point(0, -1),
        "I": Point(1, -1),
    }


class MTKGPKG2SVGUtilsTestCase(unittest.TestCase):
    def test_intersection(self):
        pp = get_points()

        def ip_np(l1, l2) -> Point:
            return intersection_point(pp[l1[0]], pp[l1[1]], pp[l2[0]], pp[l2[1]])

        self.assertEqual(pp["E"], ip_np("AI", "CG"))
        self.assertEqual(pp["E"], ip_np("BH", "CG"))
        self.assertEqual(pp["E"], ip_np("BH", "DF"))
        self.assertEqual(pp["E"], ip_np("DE", "EH"))

        self.assertEqual(pp["B"], ip_np("AB", "EH"))
        self.assertEqual(pp["B"], ip_np("EH", "AB"))

        self.assertEqual(None, ip_np("AB", "DE"))
        self.assertEqual(None, ip_np("DE", "AB"))
        self.assertEqual(None, ip_np("DG", "DG"))

        self.assertEqual(Point(0.5, 0.5), ip_np("BF", "EC"))

        self.assertEqual(pp["H"], ip_np("AH", "BH"))

        self.assertEqual(Point(-1, -3), ip_np("AG", "CH"))
        self.assertEqual(Point(-1, -3), ip_np("CH", "AG"))

        self.assertEqual(Point(1, -3), ip_np("CI", "AH"))
        self.assertEqual(Point(1, -3), ip_np("AH", "CI"))

    def test_perpendicular_distance(self):
        pp = get_points()

        def pd_np(p, l):
            return perpendicular_distance(pp[p], pp[l[0]], pp[l[1]])

        self.assertEqual(1.0, pd_np("E", "CA"))
        self.assertEqual(1.0, pd_np("E", "AC"))
        self.assertEqual(0.0, pd_np("E", "IA"))
        self.assertEqual(0.7071067811865475, pd_np("E", "HD"))

    def test_sutherland_hodgman_polygon(self):
        self.assertEqual(
            [Point(0, 0), Point(1, 0), Point(1.0, -0), Point(0, 0)],
            sutherland_hodgman([Point(0, 0), Point(2, 0), Point(0, 0)], 1, 1, -1, -1),
        )
        self.assertEqual(
            [Point(-0.9, 0), Point(0.9, 0), Point(-0.9, 0)],
            sutherland_hodgman(
                [Point(-0.9, 0), Point(0.9, 0), Point(-0.9, 0)], 1, 1, -1, -1
            ),
        )
        self.assertEqual(
            [Point(0.9, 0), Point(-0.9, 0), Point(0.9, 0)],
            sutherland_hodgman(
                [Point(0.9, 0), Point(-0.9, 0), Point(0.9, 0)], 1, 1, -1, -1
            ),
        )

        expected = [Point(0.9, 0.1), Point(0.5, 0.1), Point(0, 0.1)]
        actual = sutherland_hodgman(
            [Point(0.9, 0.1), Point(0.5, 0.1), Point(-0.9, 0.1), Point(0.9, 0.1)],
            1,
            1,
            0,
            0,
        )
        self.assertTrue(
            all(is_point_close(e, a, 1e-08) for e, a in zip(expected, actual))
        )

        self.assertEqual(
            [Point(8.0, 8.0), Point(12.0, 8.0), Point(12.0, 12.0), Point(8.0, 8.0)],
            sutherland_hodgman(
                [Point(7, 7), Point(14, 7), Point(14, 14), Point(7, 7)], 12, 12, 8, 8
            ),
        )
        self.assertEqual(
            [Point(8.0, 8.0), Point(8.0, 8.0), Point(12.0, 12.0), Point(12.0, 8.0)],
            sutherland_hodgman(
                [Point(7, 7), Point(14, 14), Point(14, 7), Point(7, 7)], 12, 12, 8, 8
            ),
        )

    def test_sutherland_hodgman_polyline(self):
        self.assertEqual(
            [Point(8.0, 8.0), Point(12.0, 8.0), Point(12.0, 12.0)],
            sutherland_hodgman(
                [Point(7, 7), Point(14, 7), Point(14, 14)], 12, 12, 8, 8
            ),
        )

        self.assertEqual(
            [Point(8.0, 8.0), Point(12.0, 12.0), Point(12.0, 8.0)],
            sutherland_hodgman(
                [Point(7, 7), Point(14, 14), Point(14, 7)], 12, 12, 8, 8
            ),
        )
