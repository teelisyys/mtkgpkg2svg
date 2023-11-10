import binascii
import logging
import struct
from typing import List, Optional, Tuple, TypeVar

from mtkgpkg2svg.datatypes import (
    BoundingBox,
    P,
    WKBGeometry,
    WKBLinearRing,
    WKBLineString,
    WKBPoint,
    WKBPointZ,
    WKBPolygon,
)
from mtkgpkg2svg.utils import (
    OUTCODE_INSIDE,
    OutCode,
    clip_poly,
    out_code,
    ramer_douglas_peucker,
)

WKB_POINT = 1
WKB_POINT_Z = 1001

WKB_LINE_STRING_Z = 1002
WKB_POLYGON = 3
WKB_POLYGON_Z = 1003


# pylint: disable=too-many-arguments
def is_inside(
    x: float,
    y: float,
    y_top: float,
    x_right: float,
    y_bottom: float,
    x_left: float,
) -> bool:
    return out_code(x, y, y_top, x_right, y_bottom, x_left) == OUTCODE_INSIDE


class WellKnownBinaryParser:
    def __init__(
        self,
        bounding_box: Optional[BoundingBox] = None,
        epsilon: Optional[float] = None,
    ):
        self.bounding_box = bounding_box
        self.epsilon = epsilon
        self.bounding_box_tuple: Optional[Tuple[float, float, float, float]] = None
        if bounding_box is not None:
            self.bounding_box_tuple = (
                bounding_box.north,
                bounding_box.east,
                bounding_box.south,
                bounding_box.west,
            )

    def parse_gpkgblob(
        self,
        blob: bytes,
    ) -> Optional[WKBGeometry]:
        # https://www.geopackage.org/spec131/index.html#gpb_spec
        fmt = ">2sBBi"
        magic, version, flags_i, _srs_id = struct.unpack_from(fmt, blob, 0)
        assert magic == b"GP"
        assert version == 0
        offset = struct.calcsize(fmt)
        flags = f"{flags_i:08b}"
        envelope_contents_indicator_code = int(flags[4:7], 2)
        envelope_sizes = [0, 32, 48, 48, 64]
        offset += envelope_sizes[envelope_contents_indicator_code]
        return self.parse_wkb(blob, offset)

    def parse_wkb(self, wkb: bytes, offset: int) -> Optional[WKBGeometry]:
        fmt = ">B"
        (endianess,) = struct.unpack_from(fmt, wkb, offset)
        offset += struct.calcsize(fmt)
        if endianess == 0:
            ec = ">"
        else:
            ec = "<"

        fmt = f"{ec}I"
        (wkb_geometry_type,) = struct.unpack_from(fmt, wkb, offset)
        offset += struct.calcsize(fmt)

        logging.debug(
            "endianess=%s, wkb_geometry_type=%s", endianess, wkb_geometry_type
        )

        geometry: Optional[WKBGeometry]
        if wkb_geometry_type == WKB_POINT:
            offset, geometry = self.parse_point(wkb, ec, offset)
        elif wkb_geometry_type == WKB_POINT_Z:
            offset, geometry = self.parse_point_z(wkb, ec, offset)
        elif wkb_geometry_type == WKB_LINE_STRING_Z:
            offset, geometry = self.parse_multipointsish(
                wkb, ec, offset, WKBLineString, WKBPointZ
            )
        elif wkb_geometry_type == WKB_POLYGON:
            offset, geometry = self.parse_polygon(wkb, ec, offset, WKBPoint)
        elif wkb_geometry_type == WKB_POLYGON_Z:
            offset, geometry = self.parse_polygon(wkb, ec, offset, WKBPointZ)
        else:
            raise ValueError(
                f"Unknown Geometry »{wkb_geometry_type}» »{binascii.hexlify(wkb)!r}»"
            )

        logging.debug("geometry=%s", geometry)
        return geometry

    def parse_point(self, wkb: bytes, ec: str, offset: int) -> Tuple[int, WKBPoint]:
        fmt = "dd"
        x, y = struct.unpack_from(ec + fmt, wkb, offset)
        return offset + struct.calcsize(fmt), WKBPoint(x, y)

    def parse_point_z(
        self, wkb: bytes, ec: str, offset: int
    ) -> Tuple[int, Optional[WKBPointZ]]:
        fmt = "ddd"
        x, y, z = struct.unpack_from(ec + fmt, wkb, offset)
        if (
            self.bounding_box is not None
            and self.bounding_box_tuple is not None
            and not is_inside(x, y, *self.bounding_box_tuple)
        ):
            return offset + struct.calcsize(fmt), None

        return offset + struct.calcsize(fmt), WKBPointZ(x, y, z)

    T = TypeVar("T")

    def parse_multipointsish(
        self, wkb: bytes, ec: str, offset: int, func: type[T], payload_clz: type[P]
    ) -> Tuple[int, Optional[T]]:
        # pylint: disable=too-many-locals
        dim = 3 if payload_clz == WKBPointZ else 2

        fmt = "I"
        (num_points,) = struct.unpack_from(ec + fmt, wkb, offset)
        offset += struct.calcsize(fmt)

        fmt = f"{(num_points * dim)}d"
        flatted_points = struct.unpack_from(ec + fmt, wkb, offset)

        if self.bounding_box is not None and self.bounding_box_tuple is not None:
            all_points: List[P] = []
            out_codes: List[OutCode] = []
            all_outside = True
            for i in range(num_points):
                point: P
                if dim == 3:
                    point = WKBPointZ(  # type: ignore[assignment]
                        flatted_points[i * 3],
                        flatted_points[i * 3 + 1],
                        flatted_points[i * 3 + 2],
                    )
                else:
                    point = WKBPoint(  # type: ignore[assignment]
                        flatted_points[i * 2],
                        flatted_points[i * 2 + 1],
                    )

                all_points.append(point)
                code = out_code(point.x, point.y, *self.bounding_box_tuple)
                if code == OUTCODE_INSIDE:
                    all_outside = False
                out_codes.append(code)

            if all_outside:
                return offset + struct.calcsize(fmt), None

            points: List[P] = []
            for i, (oc, point) in enumerate(zip(out_codes, all_points)):
                # Since the Sutherland-Hodgman algorithm is somewhat heavy,
                # we simplify the input by removing the points whose both neighbors are
                # in the same outside sector
                if not (
                    oc != OUTCODE_INSIDE
                    and 0 < i < (num_points - 1)
                    and out_codes[i - 1] == oc
                    and oc == out_codes[i + 1]
                ):
                    points.append(point)

            points = clip_poly(
                points,
                self.bounding_box.north,
                self.bounding_box.east,
                self.bounding_box.south,
                self.bounding_box.west,
            )
            if not points:
                return offset + struct.calcsize(fmt), None
        else:
            points = [
                WKBPointZ(  # type: ignore[misc]
                    flatted_points[i * 3],
                    flatted_points[i * 3 + 1],
                    flatted_points[i * 3 + 2],
                )
                if dim == 3
                else WKBPoint(
                    flatted_points[i * 2],
                    flatted_points[i * 2 + 1],
                )
                for i in range(num_points)
            ]

        if self.epsilon:
            points = ramer_douglas_peucker(points, self.epsilon)

        return offset + struct.calcsize(fmt), func(points)  # type:ignore[call-arg]

    def parse_polygon(
        self, wkb: bytes, ec: str, offset: int, clz: type[P]
    ) -> Tuple[int, Optional[WKBPolygon[P]]]:
        fmt = "I"
        (num_rings,) = struct.unpack_from(ec + fmt, wkb, offset)
        offset += struct.calcsize(fmt)

        rings = []
        for _ in range(num_rings):
            offset, geometry = self.parse_multipointsish(
                wkb, ec, offset, WKBLinearRing, clz
            )
            if geometry is not None:
                rings.append(geometry)
        if not rings:
            return offset + struct.calcsize(fmt), None

        return offset + struct.calcsize(fmt), WKBPolygon[P](rings)
