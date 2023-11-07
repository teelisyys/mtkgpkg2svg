import logging
import math
from typing import Callable, List, Optional, Tuple, TypeVar

from mtkgpkg2svg.datatypes import Point, WKBPointZ

U = TypeVar("U", bound=Point)


def ramer_douglas_peucker(line: List[U], epsilon: float) -> List[U]:
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


def perpendicular_distance(p: Point, start_p: Point, end_p: Point) -> float:
    if start_p == end_p:
        return math.sqrt((start_p.x - p.x) ** 2 + (start_p.y - p.y) ** 2)

    dx = end_p.x - start_p.x
    dy = end_p.y - start_p.y
    d = math.sqrt(dx**2 + dy**2)

    if d == 0:
        return float("inf")

    return (
        math.fabs(p.x * dy - p.y * dx + end_p.x * start_p.y - end_p.y * start_p.x) / d
    )


def intersection_point(c: U, d: U, a: Point, b: Point) -> Optional[U]:
    """Returns the intersection point of the lines defined by (a, b) and (c, d) or None if
    the lines are parallel."""

    a0_m_b0 = a.x - b.x
    c1_m_d1 = c.y - d.y
    a1_m_b1 = a.y - b.y
    c0_m_d0 = c.x - d.x
    denominator = a0_m_b0 * c1_m_d1 - a1_m_b1 * c0_m_d0
    if denominator == 0:
        return None

    a0b1_m_a1b0 = a.x * b.y - a.y * b.x
    c0d1_m_c1d0 = c.x * d.y - c.y * d.x
    x_nom = a0b1_m_a1b0 * c0_m_d0 - a0_m_b0 * c0d1_m_c1d0
    y_nom = a0b1_m_a1b0 * c1_m_d1 - a1_m_b1 * c0d1_m_c1d0

    if isinstance(c, WKBPointZ) and isinstance(d, WKBPointZ):
        return WKBPointZ(
            x_nom / denominator, y_nom / denominator, (c.z + d.z) / 2
        )  # type:ignore[return-value]

    return c.__class__(x_nom / denominator, y_nom / denominator)


# pylint: disable=too-many-locals
def sutherland_hodgman(
    input_polygon: List[U],
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> List[U]:
    """https://en.wikipedia.org/wiki/Sutherland%E2%80%93Hodgman_algorithm"""

    is_polyline = False
    if input_polygon[0] != input_polygon[-1]:
        is_polyline = True

    clip_lines: List[Tuple[Point, Point, Callable[[U], bool]]] = [
        (Point(left, top), Point(right, top), lambda p: p.y < top),
        (Point(right, top), Point(right, bottom), lambda p: p.x < right),
        (Point(left, bottom), Point(right, bottom), lambda p: p.y > bottom),
        (Point(left, top), Point(left, bottom), lambda p: p.x > left),
    ]
    sides = ["top", "right", "bottom", "left"]

    current_polygon = input_polygon
    if is_polyline:
        current_polygon.append(input_polygon[0])

    for i, (a, b, is_inside) in enumerate(clip_lines):
        logging.debug("--> %s: a=%s, b=%s", sides[i], a, b)
        new_polygon: List[U] = []
        point: U
        for p_idx, point in enumerate(current_polygon):
            previous_point: U = current_polygon[p_idx - 1]

            xp: Optional[U] = intersection_point(previous_point, point, a, b)
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
            if inside:
                if not prev_inside and xp is not None:
                    new_polygon.append(xp)
                assert point is not None
                new_polygon.append(point)
            else:
                if prev_inside and xp is not None:
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
