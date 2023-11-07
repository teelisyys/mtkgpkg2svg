import abc
from dataclasses import dataclass
from typing import Dict, List, Optional
from xml.etree import ElementTree

Styling = Dict[str, str]


@dataclass
class BoundingBox:
    north: float
    east: float
    south: float
    west: float
    height_km: float
    width_km: float


@dataclass
class Point:
    x: float
    y: float


# pylint: disable=too-few-public-methods
class AsSVG(abc.ABC):
    @abc.abstractmethod
    def to_svg_element(
        self, styling: Styling, href_id: Optional[str] = None
    ) -> Optional[ElementTree.Element]:
        """Provides representation of the object as SVG"""


@dataclass
class WKBPoint(AsSVG, Point):
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
class WKBPointZ(WKBPoint):
    z: float


@dataclass
class WKBLineStringZ(AsSVG):
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
class WKBLinearRingZ(AsSVG):
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
class WKBPolygonZ(AsSVG):
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


WKBGeometry = WKBPoint | WKBPointZ | WKBLineStringZ | WKBPolygonZ | WKBLinearRingZ
