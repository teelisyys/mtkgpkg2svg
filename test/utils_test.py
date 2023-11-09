import logging
import unittest
from itertools import zip_longest
from typing import Dict

from mtkgpkg2svg.utils import (
    intersection_point,
    perpendicular_distance,
    sutherland_hodgman,
    Point,
    is_point_close,
    cohen_sutherland,
)

logging.basicConfig(level=logging.WARN)


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

        self.assertEqual(
            [Point(9.0, 9.0), Point(12.0, 12.0), Point(12.0, 9.6)],
            sutherland_hodgman(
                [Point(9, 9), Point(14, 14), Point(14, 10)], 12, 12, 8, 8
            ),
        )

    def test_cohen_sutherland(self):
        input_polyline = [
            Point(7, 9.5),
            Point(8.5, 9.5),
            Point(9.5, 8.5),
            Point(9.5, 7),
        ]
        actual = cohen_sutherland(
            input_polyline,
            12,
            12,
            8,
            8,
        )
        self.assertEqual(
            [
                Point(x=8.0, y=9.5),
                Point(x=8.5, y=9.5),
                Point(x=9.5, y=8.5),
                Point(x=9.5, y=8.0),
            ],
            actual,
        )

    def test_cohen_sutherland_edge_case_1(self):
        input_polyline = [
            Point(x=16.75, y=891.604),
            Point(x=15.65, y=883.684),
            Point(x=90.439, y=770.425),
        ]
        actual = cohen_sutherland(
            input_polyline,
            7223890.633 - 7118000,
            576398.845 - 432200.0,
            7118890.633 - 7118000,
            427898.845 - 432200.0,
        )

        expected = [
            Point(x=16.75, y=891.604),
            Point(x=16.615138888941463, y=890.6330000003801),
        ]
        for exp, act in zip_longest(expected, actual):
            self.assertTrue(is_point_close(exp, act, 0.001))

    def test_cohen_sutherland_edge_case_2(self):
        dx = -432200.0
        dy = -7118000.0
        actual = self.get_actual(dx, dy)
        expected = [
            Point(x=16.75, y=891.604),
            Point(x=16.615138888941658, y=890.63300000038),
        ]
        for exp, act in zip_longest(expected, actual):
            self.assertTrue(is_point_close(exp, act, 0.001))

        dx = 0.0
        dy = 0.0
        actual = self.get_actual(dx, dy)
        expected = [
            Point(x=432216.75, y=7118891.604),
            Point(x=432216.6151388889, y=7118890.633),
        ]
        for exp, act in zip_longest(expected, actual):
            self.assertTrue(is_point_close(exp, act, 0.001))

    def get_actual(self, dx, dy):
        input_polyline = [
            Point(x=round(432216.750 + dx, 3), y=round(7118891.604 + dy, 3)),
            Point(x=round(432215.650 + dx, 3), y=round(7118883.684 + dy, 3)),
            Point(x=round(432290.439 + dx, 3), y=round(7118770.425 + dy, 3)),
        ]
        actual = cohen_sutherland(
            input_polyline,
            7223890.633 + dy,
            576398.845 + dx,
            7118890.633 + dy,
            427898.845 + dx,
        )
        return actual

    def test_cohen_sutherland_edge_case_4(self):
        expected = [
            Point(x=467061.22339631367, y=7118890.633),
            Point(x=467072.306, y=7119547.363),
        ]
        input_polyline = [
            Point(x=460317.509, y=7096721.518),
            Point(x=467055.727, y=7118564.929),
            Point(x=467072.306, y=7119547.363),
        ]

        actual = cohen_sutherland(
            input_polyline, 7223890.633, 576398.845, 7118890.633, 427898.845
        )

        for exp, act in zip_longest(expected, actual):
            self.assertTrue(is_point_close(exp, act, 0.001))

    def test_cohen_sutherland_edge_case_5(self):
        expected = []
        input_polyline = [
            Point(x=-3, y=3),
            Point(x=-2, y=3),
            Point(x=-1, y=3),
            Point(x=0, y=3),
            Point(x=1, y=3),
            Point(x=2, y=3),
            Point(x=3, y=3),
        ]

        actual = cohen_sutherland(input_polyline, 2, 2, -2, -2)

        for exp, act in zip_longest(expected, actual):
            self.assertTrue(is_point_close(exp, act, 0.001))
