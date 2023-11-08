import logging
import math
from enum import Enum
from typing import Callable, List, Optional, Tuple, TypeVar

from mtkgpkg2svg.datatypes import BoundingBox, Point, WKBPointZ

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


def clip_poly(
    input_polyform: List[U],
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> List[U]:
    if input_polyform[0] == input_polyform[-1]:
        return sutherland_hodgman(input_polyform, top, right, bottom, left)
    return cohen_sutherland(input_polyform, top, right, bottom, left)


def sutherland_hodgman(
    input_polygon: List[U],
    top: float,
    right: float,
    bottom: float,
    left: float,
) -> List[U]:
    """https://en.wikipedia.org/wiki/Sutherland%E2%80%93Hodgman_algorithm"""
    # pylint: disable=too-many-locals

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


class OutCode(Enum):
    INSIDE = 0
    LEFT = 0b0001
    RIGHT = 0b0010
    BOTTOM = 0b0100
    TOP = 0b1000
    TOP_LEFT = 0b1001
    TOP_RIGHT = 0b1010
    BOTTOM_LEFT = 0b0101
    BOTTOM_RIGHT = 0b0110


def out_code_bb(x: float, y: float, bounding_box: BoundingBox) -> OutCode:
    return out_code(
        x,
        y,
        bounding_box.north,
        bounding_box.east,
        bounding_box.south,
        bounding_box.west,
    )


# pylint: disable=too-many-arguments
def clip_to_bb(
    p0: U,
    p1: U,
    code_p: OutCode,
    y_top: float,
    x_right: float,
    y_bottom: float,
    x_left: float,
) -> Optional[U]:
    assert code_p != OutCode.INSIDE
    x = 0.0
    y = 0.0
    if code_p.value & OutCode.TOP.value:
        x = p0.x + (p1.x - p0.x) * (y_top - p0.y) / (p1.y - p0.y)
        y = y_top
    elif code_p.value & OutCode.BOTTOM.value:
        x = p0.x + (p1.x - p0.x) * (y_bottom - p0.y) / (p1.y - p0.y)
        y = y_bottom
    elif code_p.value & OutCode.RIGHT.value:
        y = p0.y + (p1.y - p0.y) * (x_right - p0.x) / (p1.x - p0.x)
        x = x_right
    elif code_p.value & OutCode.LEFT.value:
        y = p0.y + (p1.y - p0.y) * (x_left - p0.x) / (p1.x - p0.x)
        x = x_left

    if isinstance(p0, WKBPointZ) and isinstance(p1, WKBPointZ):
        return WKBPointZ(x, y, (p0.z + p1.z) / 2)  # type:ignore[return-value]

    return p0.__class__(x, y)


# pylint: disable=too-many-arguments
def out_code(
    x: float,
    y: float,
    y_top: float,
    x_right: float,
    y_bottom: float,
    x_left: float,
) -> OutCode:
    code: int = OutCode.INSIDE.value

    if x < x_left:
        code |= OutCode.LEFT.value
    elif x > x_right:
        code |= OutCode.RIGHT.value
    if y < y_bottom:
        code |= OutCode.BOTTOM.value
    elif y > y_top:
        code |= OutCode.TOP.value

    return OutCode(code)


def cohen_sutherland(
    input_polyline: List[U],
    y_top: float,
    x_right: float,
    y_bottom: float,
    x_left: float,
) -> List[U]:
    # pylint: disable=too-many-locals,too-many-branches,

    code_previous = out_code(
        input_polyline[0].x, input_polyline[0].y, y_top, x_right, y_bottom, x_left
    )

    segment_under_work: List[U] = []
    result: List[U] = []

    for i, p_current in enumerate(input_polyline):
        if i == 0:
            continue
        p_previous = input_polyline[i - 1]
        code_current = out_code(
            p_current.x, p_current.y, y_top, x_right, y_bottom, x_left
        )
        last_code = code_current

        iteration_counter = 0
        while True:
            if code_previous == OutCode.INSIDE and code_current == OutCode.INSIDE:
                # Both inside -> accept
                segment_under_work.append(p_previous)
                if code_current != last_code:
                    segment_under_work.append(p_current)
                    if i < len(input_polyline) - 1:
                        result.extend(segment_under_work)
                        segment_under_work = []
                elif i == len(input_polyline) - 1:
                    segment_under_work.append(p_current)
                break

            if code_previous.value & code_current.value:
                # Both outside -> reject
                break

            if (iteration_counter + 1) % 1000 == 0:
                logging.warning("Iteration iteration_counter=%s", iteration_counter)

            if code_previous != OutCode.INSIDE:
                # previous outside, current inside -> move previous to edge
                p_potential = clip_to_bb(
                    p_previous,
                    p_current,
                    code_previous,
                    y_top,
                    x_right,
                    y_bottom,
                    x_left,
                )

                assert p_potential is not None
                p_previous = p_potential
                code_previous = out_code(
                    p_previous.x, p_previous.y, y_top, x_right, y_bottom, x_left
                )
            elif code_current != OutCode.INSIDE:
                # current outside, previous inside -> move current to edge
                p_potential = clip_to_bb(
                    p_current,
                    p_previous,
                    code_current,
                    y_top,
                    x_right,
                    y_bottom,
                    x_left,
                )

                assert p_potential is not None
                p_current = p_potential
                code_current = out_code(
                    p_current.x, p_current.y, y_top, x_right, y_bottom, x_left
                )

            iteration_counter += 1
            if iteration_counter > 2000:
                raise ValueError(
                    "There was an issue with the Cohen-Sutherland algorithm."
                )

        code_previous = last_code

    if segment_under_work:
        result.extend(segment_under_work)

    return result


def is_point_close(expected: Point, actual: Point, epsilon: float) -> bool:
    return is_close(expected.x, actual.x, epsilon) and is_close(
        expected.y, actual.y, epsilon
    )


def is_close(expected: float, actual: float, epsilon: float) -> bool:
    return expected - epsilon < actual < expected + epsilon
