import logging
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class BoundingBox:
    north: float
    east: float
    south: float
    west: float
    height_km: float
    width_km: float


FPoint = Tuple[float, float]


def ramer_douglas_peucker(line: List[FPoint], epsilon: float) -> List[FPoint]:
    if not epsilon or len(line) < 3:
        return line
    max_distance: float = 0.0
    max_distance_index: int = 0
    for i in range(1, len(line) - 1):
        current_distance = perpendicular_distance(line[i], line[0], line[-1])
        if current_distance > max_distance:
            max_distance = current_distance
            max_distance_index = i

    if max_distance > epsilon:
        return [
            *ramer_douglas_peucker(line[: max_distance_index + 1], epsilon),
            *ramer_douglas_peucker(line[max_distance_index:], epsilon)[1:],
        ]
    return [line[0], line[-1]]


def perpendicular_distance(p: FPoint, start_p: FPoint, end_p: FPoint) -> float:
    if start_p == end_p:
        return math.sqrt((start_p[0] - p[0]) ** 2 + (start_p[1] - p[1]) ** 2)

    dx = end_p[0] - start_p[0]
    dy = end_p[1] - start_p[1]
    d = math.sqrt(dx**2 + dy**2)

    if d == 0:
        return float("inf")

    return (
        math.fabs(p[0] * dy - p[1] * dx + end_p[0] * start_p[1] - end_p[1] * start_p[0])
        / d
    )


# def intersection_point(c: FPoint, d: FPoint, a: FPoint, b: FPoint) -> Optional[FPoint]:
#     """Returns the intersection point of the lines defined by (a, b) and (c, d) or None if
#     the lines are parallel."""
#
#     def x(p: FPoint) -> float:
#         return p[0]
#
#     def y(p: FPoint) -> float:
#         return p[1]
#
#     denominator = (x(a) - x(b)) * (y(c) - y(d)) - (y(a) - y(b)) * (x(c) - x(d))
#     if denominator == 0:
#         return None
#
#     x_nom = (x(a) * y(b) - y(a) * x(b)) * (x(c) - x(d)) - (x(a) - x(b)) * (
#         x(c) * y(d) - y(c) * x(d)
#     )
#
#     y_nom = (x(a) * y(b) - y(a) * x(b)) * (y(c) - y(d)) - (y(a) - y(b)) * (
#         x(c) * y(d) - y(c) * x(d)
#     )
#
#     return x_nom / denominator, y_nom / denominator


def intersection_point(c: FPoint, d: FPoint, a: FPoint, b: FPoint) -> Optional[FPoint]:
    """Returns the intersection point of the lines defined by (a, b) and (c, d) or None if
    the lines are parallel."""

    a0_m_b0 = a[0] - b[0]
    c1_m_d1 = c[1] - d[1]
    a1_m_b1 = a[1] - b[1]
    c0_m_d0 = c[0] - d[0]
    denominator = a0_m_b0 * c1_m_d1 - a1_m_b1 * c0_m_d0
    if denominator == 0:
        return None

    a0b1_m_a1b0 = a[0] * b[1] - a[1] * b[0]
    c0d1_m_c1d0 = c[0] * d[1] - c[1] * d[0]
    x_nom = a0b1_m_a1b0 * c0_m_d0 - a0_m_b0 * c0d1_m_c1d0
    y_nom = a0b1_m_a1b0 * c1_m_d1 - a1_m_b1 * c0d1_m_c1d0

    return x_nom / denominator, y_nom / denominator


# pylint: disable=too-many-locals
def sutherland_hodgman(
    input_polygon: List[FPoint],
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> List[FPoint]:
    """https://en.wikipedia.org/wiki/Sutherland%E2%80%93Hodgman_algorithm"""

    is_polyline = False
    if input_polygon[0] != input_polygon[-1]:
        is_polyline = True

    clip_lines: List[Tuple[FPoint, FPoint, Callable[[FPoint], bool]]] = [
        ((left, top), (right, top), lambda x: x[1] < top),
        ((right, top), (right, bottom), lambda x: x[0] < right),
        ((left, bottom), (right, bottom), lambda x: x[1] > bottom),
        ((left, top), (left, bottom), lambda x: x[0] > left),
    ]
    sides = ["top", "right", "bottom", "left"]

    current_polygon = input_polygon
    if is_polyline:
        current_polygon.append(input_polygon[0])

    for i, (a, b, is_inside) in enumerate(clip_lines):
        logging.debug("--> %s: a=%s, b=%s", sides[i], a, b)
        new_polygon: List[FPoint] = []
        for p_idx, point in enumerate(current_polygon):
            previous_point = current_polygon[p_idx - 1]

            xp = intersection_point(previous_point, point, a, b)
            inside = is_inside(point)
            prev_inside = is_inside(previous_point)
            logging.debug(
                "p_idx=%d, point=%s, previous_point=%s, xp=%s, inside=%s, prev_inside=%s",
                p_idx,
                point,
                previous_point,
                xp,
                inside,
                prev_inside,
            )
            assert xp is not None
            if inside:
                if not prev_inside:
                    new_polygon.append(xp)
                assert point is not None
                new_polygon.append(point)
            else:
                if prev_inside:
                    new_polygon.append(xp)
            logging.debug("new_polygon=%s", new_polygon)
        current_polygon = new_polygon
        logging.debug("current_polygon=%s", current_polygon)

    if not current_polygon:
        return []

    if is_polyline:
        if current_polygon[0] == current_polygon[-1]:
            return current_polygon[:-1]
        return current_polygon[1:]

    return current_polygon


if __name__ == "__main__":
    # assert ramer_douglas_peucker([(0, -1000), (0, 0), (0, 1000)], epsilon=100) == [
    #     (0, -1000),
    #     (0, 1000),
    # ]
    # assert ramer_douglas_peucker([(0, -1000), (99, 0), (0, 1000)], epsilon=100) == [
    #     (0, -1000),
    #     (0, 1000),
    # ]
    # print(ramer_douglas_peucker([(0, -1000), (101, 0), (0, 1000)], epsilon=100))
    assert ramer_douglas_peucker(
        [
            (0, -1000),
            (0, -800),
            (0, -600),
            (0, -400),
            (0, -200),
            (101, 0),
            (0, 200),
            (0, 400),
            (0, 600),
            (0, 800),
            (0, 1000),
        ],
        epsilon=100,
    ) == [(0, -1000), (101, 0), (0, 1000)]
    assert ramer_douglas_peucker(
        [
            (0, -1000),
            (0, -800),
            (0, -600),
            (0, -400),
            (0, -200),
            (200, 0),
            (0, 200),
            (0, 400),
            (0, 600),
            (0, 800),
            (0, 1000),
        ],
        epsilon=100,
    ) == [(0, -1000), (0, -200), (200, 0), (0, 200), (0, 1000)]

    print(
        ramer_douglas_peucker(
            [
                (0, -1000),
                (0, -800),
                (200, -600),
                (0, -400),
                (0, -200),
                (0, 0),
                (0, 200),
                (0, 400),
                (0, 600),
                (0, 800),
                (0, 1000),
            ],
            epsilon=100,
        )
    )
