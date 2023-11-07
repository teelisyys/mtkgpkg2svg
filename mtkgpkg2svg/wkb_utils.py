import abc
import binascii
import logging
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TypeVar, Union
from xml.etree import ElementTree

WKB_POINT = 1
WKB_POINT_Z = 1001

WKB_LINE_STRING_Z = 1002
WKB_POLYGON_Z = 1003

Styling = Dict[str, str]


# pylint: disable=too-few-public-methods
class SVGAble(abc.ABC):
    @abc.abstractmethod
    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        """Provides an representation of the object as SVG"""


@dataclass
class WKBPoint(SVGAble):
    x: float
    y: float

    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        return None


@dataclass
class WKBPointZ(SVGAble):
    x: float
    y: float
    z: float

    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        if href_id:
            return ElementTree.Element(
                "{http://www.w3.org/2000/svg}use",
                attrib={
                    "{http://www.w3.org/2000/svg}href": f"#{href_id}",
                    "{http://www.w3.org/2000/svg}x": f"{self.x-20}",
                    "{http://www.w3.org/2000/svg}y": f"-{self.y+20}",
                    **styling,
                },
            )
        return ElementTree.Element(
            "{http://www.w3.org/2000/svg}rect",
            attrib={
                "{http://www.w3.org/2000/svg}x": f"{self.x-20}",
                "{http://www.w3.org/2000/svg}y": f"{self.x-20}",
                "{http://www.w3.org/2000/svg}height": "40",
                "{http://www.w3.org/2000/svg}width": "40",
                **styling,
            },
        )


@dataclass
class WKBLineStringZ(SVGAble):
    points: List[WKBPointZ]

    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        if not self.points:
            return None
        return ElementTree.Element(
            "{http://www.w3.org/2000/svg}polyline",
            attrib={
                "{http://www.w3.org/2000/svg}points": " ".join(
                    [f"{p.x},-{p.y}" for p in self.points]
                ),
                **styling,
            },
        )


@dataclass
class WKBLinearRingZ(SVGAble):
    points: List[WKBPointZ]

    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        if not self.points:
            return None
        return ElementTree.Element(
            "{http://www.w3.org/2000/svg}polygon",
            attrib={
                "{http://www.w3.org/2000/svg}points": " ".join(
                    [f"{p.x},-{p.y}" for p in self.points]
                ),
                **styling,
            },
        )


@dataclass
class WKBPolygonZ(SVGAble):
    rings: List[WKBLinearRingZ]

    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        path_coords = []
        for linear_ring in self.rings:
            for ring_index, p in enumerate(linear_ring.points):
                pcmd = "M" if ring_index == 0 else "L"
                path_coords.append(f"{pcmd} {p.x},-{p.y}")
            path_coords.append("Z")
        return ElementTree.Element(
            "{http://www.w3.org/2000/svg}path",
            attrib={"{http://www.w3.org/2000/svg}d": " ".join(path_coords), **styling},
        )

        # group = ElementTree.Element("{http://www.w3.org/2000/svg}g")
        # has_children = False
        # for ring in self.rings:
        #     element = ring.to_svg_element(styling)
        #     if element is not None:
        #         group.append(element)
        #         has_children = True
        # if has_children:
        #     return group
        # return None


WKBGeometry = Union[WKBPoint, WKBPointZ, WKBLineStringZ, WKBPolygonZ, WKBLinearRingZ]


def parse_gpkgblob(
    blob: bytes,
) -> WKBGeometry:
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
    return parse_wkb(blob, offset)


def parse_wkb(wkb: bytes, offset: int) -> WKBGeometry:
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

    logging.debug("endianess=%s, wkb_geometry_type=%s", endianess, wkb_geometry_type)

    geometry: WKBGeometry
    if wkb_geometry_type == WKB_POINT:
        offset, geometry = parse_point(wkb, ec, offset)
    elif wkb_geometry_type == WKB_POINT_Z:
        offset, geometry = parse_point_z(wkb, ec, offset)
    elif wkb_geometry_type == WKB_LINE_STRING_Z:
        offset, geometry = parse_multipointsish_z(wkb, ec, offset, WKBLineStringZ)
    elif wkb_geometry_type == WKB_POLYGON_Z:
        offset, geometry = parse_polygon_z(wkb, ec, offset)
    else:
        raise ValueError(
            f"Unknown Geometry »{wkb_geometry_type}» »{binascii.hexlify(wkb)!r}»"
        )

    logging.debug("geometry=%s", geometry)
    return geometry


def parse_point(wkb: bytes, ec: str, offset: int) -> Tuple[int, WKBPoint]:
    fmt = "dd"
    x, y = struct.unpack_from(ec + fmt, wkb, offset)
    return offset + struct.calcsize(fmt), WKBPoint(x, y)


def parse_point_z(wkb: bytes, ec: str, offset: int) -> Tuple[int, WKBPointZ]:
    fmt = "ddd"
    x, y, z = struct.unpack_from(ec + fmt, wkb, offset)
    return offset + struct.calcsize(fmt), WKBPointZ(x, y, z)


T = TypeVar("T")


def parse_multipointsish_z(
    wkb: bytes, ec: str, offset: int, func: type[T]
) -> Tuple[int, T]:
    fmt = "I"
    (num_points,) = struct.unpack_from(ec + fmt, wkb, offset)
    offset += struct.calcsize(fmt)

    fmt = f"{(num_points * 3)}d"
    flatted_points = struct.unpack_from(ec + fmt, wkb, offset)
    points = [
        WKBPointZ(
            flatted_points[i * 3], flatted_points[i * 3 + 1], flatted_points[i * 3 + 2]
        )
        for i in range(num_points)
    ]

    return offset + struct.calcsize(fmt), func(points)  # type:ignore[call-arg]


def parse_polygon_z(wkb: bytes, ec: str, offset: int) -> Tuple[int, WKBPolygonZ]:
    fmt = "I"
    (num_rings,) = struct.unpack_from(ec + fmt, wkb, offset)
    offset += struct.calcsize(fmt)

    rings = []
    for _ in range(num_rings):
        offset, geometry = parse_multipointsish_z(wkb, ec, offset, WKBLinearRingZ)
        rings.append(geometry)

    return offset + struct.calcsize(fmt), WKBPolygonZ(rings)
