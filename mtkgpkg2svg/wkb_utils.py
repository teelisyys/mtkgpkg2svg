import binascii
import logging
import struct
from typing import Optional, Tuple, TypeVar

from mtkgpkg2svg.datatypes import (
    BoundingBox,
    WKBGeometry,
    WKBLinearRingZ,
    WKBLineStringZ,
    WKBPoint,
    WKBPointZ,
    WKBPolygonZ,
)
from mtkgpkg2svg.utils import ramer_douglas_peucker, sutherland_hodgman

WKB_POINT = 1
WKB_POINT_Z = 1001

WKB_LINE_STRING_Z = 1002
WKB_POLYGON_Z = 1003


def is_inside(x: float, y: float, bounding_box: BoundingBox) -> bool:
    return (
        bounding_box.west < x < bounding_box.east
        and bounding_box.south < y < bounding_box.north
    )


class WellKnownBinaryParser:
    def __init__(
        self,
        bounding_box: Optional[BoundingBox] = None,
        epsilon: Optional[float] = None,
    ):
        self.bounding_box = bounding_box
        self.epsilon = epsilon

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
            offset, geometry = self.parse_multipointsish_z(
                wkb, ec, offset, WKBLineStringZ
            )
        elif wkb_geometry_type == WKB_POLYGON_Z:
            offset, geometry = self.parse_polygon_z(wkb, ec, offset)
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
        if self.bounding_box is not None and not is_inside(x, y, self.bounding_box):
            return offset + struct.calcsize(fmt), None

        return offset + struct.calcsize(fmt), WKBPointZ(x, y, z)

    T = TypeVar("T")

    def parse_multipointsish_z(
        self, wkb: bytes, ec: str, offset: int, func: type[T]
    ) -> Tuple[int, Optional[T]]:
        fmt = "I"
        (num_points,) = struct.unpack_from(ec + fmt, wkb, offset)
        offset += struct.calcsize(fmt)

        fmt = f"{(num_points * 3)}d"
        flatted_points = struct.unpack_from(ec + fmt, wkb, offset)
        points = [
            WKBPointZ(
                flatted_points[i * 3],
                flatted_points[i * 3 + 1],
                flatted_points[i * 3 + 2],
            )
            for i in range(num_points)
        ]

        if self.bounding_box is not None:
            points = sutherland_hodgman(
                points,
                self.bounding_box.north,
                self.bounding_box.east,
                self.bounding_box.south,
                self.bounding_box.west,
            )
            if not points:
                return offset + struct.calcsize(fmt), None

        if self.epsilon:
            points = ramer_douglas_peucker(points, self.epsilon)

        return offset + struct.calcsize(fmt), func(points)  # type:ignore[call-arg]

    def parse_polygon_z(
        self, wkb: bytes, ec: str, offset: int
    ) -> Tuple[int, Optional[WKBPolygonZ]]:
        fmt = "I"
        (num_rings,) = struct.unpack_from(ec + fmt, wkb, offset)
        offset += struct.calcsize(fmt)

        rings = []
        for _ in range(num_rings):
            offset, geometry = self.parse_multipointsish_z(
                wkb, ec, offset, WKBLinearRingZ
            )
            if geometry is not None:
                rings.append(geometry)
        if not rings:
            return offset + struct.calcsize(fmt), None

        return offset + struct.calcsize(fmt), WKBPolygonZ(rings)
