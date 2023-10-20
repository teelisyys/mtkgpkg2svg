import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Cursor
from textwrap import dedent
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from xml.etree import ElementTree

from .wkb_to_geojson import wkb_to_geojson

LinearRing = List[Tuple[int, Tuple[float, float]]]
Styling = Dict[str, str]

GeoJson = Any

KohdeluokkaSpecTuple = (
    Tuple[str, int]
    | Tuple[str, int, str]
    | Tuple[str, int, int, str]
    | Tuple[str, int, int, str, str]
)


@dataclass
class KohdeluokkaSpec:
    alias: str
    elem_count: int
    kohdeluokka: Optional[int]
    table_name: str
    use_id: Optional[str]


@dataclass
class BoundingBox:
    north: float
    east: float
    south: float
    west: float
    height_km: float
    width_km: float


# pylint: disable=too-many-arguments
def main(
    north: float,
    east: float,
    output_height: float,
    output_width: float,
    scale: int,
    output_path: Path,
    input_paths: List[Path],
) -> None:
    workdir = Path(__file__).parent.parent

    bounding_box = determine_bounding_box(
        north, east, output_height, output_width, scale
    )
    svg_root = prepare_output(bounding_box, output_height, output_width, workdir)

    for gpkg_path in input_paths:
        con = sqlite3.connect(gpkg_path)
        cur = con.cursor()

        table_names = frozenset(
            r[0]
            for r in cur.execute(
                """SELECT name FROM  sqlite_schema WHERE type ='table' AND name NOT LIKE 'sqlite_%';"""
            ).fetchall()
        )

        tpl: KohdeluokkaSpecTuple
        for tpl in [  # type: ignore[assignment]
            ("meri", 1),
            ("jarvi", 1),
            ("virtavesialue", 1),
            ("virtavesikapea", 1),
            ("kallioalue", 1),
            ("korkeuskayra", 1),
            # ("rakennusreunaviiva", 1),
            ("rakennus", 1),
            ("suo", 1, 35411, "suo_helppo_avoin"),
            ("suo", 1, 35412, "suo_helppo_metsa"),
            ("suo", 1, 35421, "suo_vaikea_avoin"),
            ("suo", 1, 35422, "suo_vaikea_metsa"),
            ("soistuma", 1),
            ("jyrkanne", 1),
            ("kalliohalkeama", 1),
            ("tieviiva", 1, 12316, "ajopolku"),
            ("tieviiva", 1, 12314, "kavelyjapyoratie"),
            ("tieviiva", 1, 12313, "polku"),
            ("tieviiva", 1, 12312, "talvitie"),
            ("tieviiva", 1, 12141, "ajotie"),
            ("tieviiva", 2, 12132, "autotie_IIIb"),
            ("tieviiva", 2, 12131, "autotie_IIIa"),
            ("tieviiva", 2, 12122, "autotie_IIb"),
            ("tieviiva", 2, 12121, "autotie_IIa"),
            ("tieviiva", 2, 12112, "autotie_Ib"),
            ("tieviiva", 2, 12111, "autotie_Ia"),
            ("rautatie", 2),
            ("aita", 2),
            ("kivi", 1, "p_kivi"),
            ("lahde", 1, "p_lahde"),
            ("metsamaankasvillisuus", 1, 32710, "havupuu", "p_havupuu"),
            ("metsamaankasvillisuus", 1, 32714, "sekapuu", "p_sekapuu"),
            ("metsamaankasvillisuus", 1, 32713, "lehtipuu", "p_lehtipuu"),
            # ("metsamaankasvillisuus", 1, 32715, "varvikko", "p_varvikko"),
            ("metsamaankasvillisuus", 1, 32719, "pensaikko", "p_pensaikko"),
            ("sahkolinja", 1),
            ("luonnonsuojelualue", 1),
            ("kansallispuisto", 1),
            ("puisto", 1),
            ("maatalousmaa", 1),
            # ("kunta", 1),
        ]:
            process_item_type(cur, table_names, gpkg_path, bounding_box, svg_root, tpl)

    write_svg(output_path, svg_root)


def determine_bounding_box(
    north: float, east: float, height: float, width: float, scale: int
) -> BoundingBox:
    height_km = height * (scale / 1000)
    width_km = width * (scale / 1000)
    return BoundingBox(
        north + (height_km / 2),
        east + (width_km / 2),
        north - (height_km / 2),
        east - (width_km / 2),
        height_km,
        width_km,
    )


def geojson_to_svg(
    datum: GeoJson, styling: Styling, use_id: Optional[str]
) -> ElementTree.Element:
    # pylint: disable=too-many-return-statements
    linear_rings: List[LinearRing]
    if datum["type"] == "Polygon":
        linear_rings = datum["coordinates"]
        return path_shape(linear_rings, styling)

    if datum["type"] == "MultiPolygon":
        group = ElementTree.Element("{http://www.w3.org/2000/svg}g")
        for linear_rings in datum["coordinates"]:
            group.append(path_shape(linear_rings, styling))
        return group

    if datum["type"] == "LineString":
        return points_shape(datum["coordinates"], "polyline", styling)

    if datum["type"] == "MultiLineString":
        group = ElementTree.Element("{http://www.w3.org/2000/svg}g")
        for line_string in datum["coordinates"]:
            group.append(points_shape(line_string, "polyline", styling))
        return group

    if datum["type"] == "Point":
        if use_id:
            return ElementTree.Element(
                "{http://www.w3.org/2000/svg}use",
                attrib={
                    "{http://www.w3.org/2000/svg}href": f"#{use_id}",
                    "{http://www.w3.org/2000/svg}x": f"{float(datum['coordinates'][0])-20}",
                    "{http://www.w3.org/2000/svg}y": f"-{float(datum['coordinates'][1])+20}",
                    **styling,
                },
            )
        return ElementTree.Element(
            "{http://www.w3.org/2000/svg}rect",
            attrib={
                "{http://www.w3.org/2000/svg}x": f"{float(datum['coordinates'][0])-20}",
                "{http://www.w3.org/2000/svg}y": f"-{float(datum['coordinates'][1])+20}",
                "{http://www.w3.org/2000/svg}height": "40",
                "{http://www.w3.org/2000/svg}width": "40",
                **styling,
            },
        )

    if datum["type"] == "GeometryCollection":
        group = ElementTree.Element("{http://www.w3.org/2000/svg}g")
        for geometry in datum["geometries"]:
            group.append(geojson_to_svg(geometry, styling, use_id))
        return group

    raise ValueError(f"Unsupported datatype in geojson, got {datum['type']}")


def path_shape(linear_rings: List[LinearRing], styling: Styling) -> ElementTree.Element:
    path_coords = []
    for linear_ring in linear_rings:
        for ring_index, (x, y) in enumerate(linear_ring):
            pcmd = "M" if ring_index == 0 else "L"
            path_coords.append(f"{pcmd} {x},-{y}")
        path_coords.append("Z")
    return ElementTree.Element(
        "{http://www.w3.org/2000/svg}path",
        attrib={"{http://www.w3.org/2000/svg}d": " ".join(path_coords), **styling},
    )


def points_shape(
    line_string: List[Tuple[float, float]], shape: str, styling: Styling
) -> ElementTree.Element:
    return ElementTree.Element(
        "{http://www.w3.org/2000/svg}" + shape,
        attrib={
            "{http://www.w3.org/2000/svg}points": " ".join(
                [f"{a},-{b}" for a, b in line_string]
            ),
            **styling,
        },
    )


def sty(raw_styling: Dict[str, str]) -> Styling:
    svgnsprfx = "{http://www.w3.org/2000/svg}"
    return {
        **{f"{svgnsprfx}{k.replace('_', '-')}": str(v) for k, v in raw_styling.items()},
    }


def blob_to_geojson(blob: bytes) -> GeoJson:
    # https://www.geopackage.org/spec131/index.html#gpb_spec
    flags = f"{int.from_bytes(blob[3:4]):08b}"
    envelope_contents_indicator_code = int(flags[4:7], 2)
    envelope_sizes = [0, 32, 48, 48, 64]
    geojson, _ = wkb_to_geojson(
        bytearray(blob[8 + envelope_sizes[envelope_contents_indicator_code] :])
    )
    return geojson


def fetch_rows(
    table_name: str,
    _dbname: Path,
    table_names: FrozenSet[str],
    bounding_box: BoundingBox,
    cur: Cursor,
) -> Tuple[Dict[str, int], List[List[str | int | bytes]]]:
    tn_geom = f"rtree_{table_name}_geom"
    if table_name not in table_names or tn_geom not in table_names:
        raise ValueError(f"Unknown table name »{table_name}»!")

    res = cur.execute(
        dedent(
            f"""\
            SELECT *
            FROM {table_name}
            WHERE fid IN(
              SELECT id FROM {tn_geom}
              WHERE NOT ((maxy < :bb_south OR miny > :bb_north) AND (maxx < :bb_west OR minx > :bb_east)));"""
        ),
        {
            "bb_south": bounding_box.south,
            "bb_west": bounding_box.west,
            "bb_north": bounding_box.north,
            "bb_east": bounding_box.east,
        },
    )
    colmap = {x[0]: i for i, x in enumerate(cur.description)}
    rows = res.fetchall()
    return colmap, rows


def write_svg(output_path: Path, svg_root: ElementTree.Element) -> None:
    with output_path.open("wb") as ofd:
        svg_tree = ElementTree.ElementTree(svg_root)
        ofd.write(
            b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n"""
        )
        ElementTree.indent(svg_tree)
        svg_tree.write(
            ofd,
            encoding="utf-8",
            xml_declaration=False,
            default_namespace="http://www.w3.org/2000/svg",
        )


def process_item_type(
    cur: Cursor,
    table_names: FrozenSet[str],
    gpkg_path: Path,
    bounding_box: BoundingBox,
    svg_root: ElementTree.Element,
    item_type_spec: KohdeluokkaSpecTuple,
) -> None:
    spec = unpack_spec_tuple(item_type_spec)
    colmap, rows = fetch_rows(
        spec.table_name,
        gpkg_path,
        table_names,
        bounding_box,
        cur,
    )
    for row in rows:
        for i in range(spec.elem_count):
            if (
                spec.kohdeluokka is not None
                and row[colmap["kohdeluokka"]] != spec.kohdeluokka
            ):
                continue
            geom_blob = row[colmap["geom"]]
            assert isinstance(geom_blob, bytes), f"{type(geom_blob)}"
            datum = blob_to_geojson(geom_blob)
            svg_elem = geojson_to_svg(
                datum, sty({"class": f"{spec.alias} {spec.alias}_{i}"}), spec.use_id
            )
            svg_root.append(svg_elem)


def prepare_output(
    bounding_box: BoundingBox,
    output_height: float,
    output_width: float,
    workdir: Path,
) -> ElementTree.Element:
    svg_root = ElementTree.Element("{http://www.w3.org/2000/svg}svg")
    style_elem = ElementTree.Element("{http://www.w3.org/2000/svg}style")
    with (workdir / "styles/topo/style.css").open() as ifd:
        style_elem.text = ifd.read()
    svg_root.append(style_elem)
    with (workdir / "styles/topo/defs.svg").open() as ifd:
        defs_tree = ElementTree.parse(ifd).getroot()
    svg_root.append(defs_tree[0])
    svg_root.set(
        "{http://www.w3.org/2000/svg}viewBox",
        f"{bounding_box.west} -{bounding_box.north} {bounding_box.width_km} {bounding_box.height_km}",
    )
    svg_root.set(
        "{http://www.w3.org/2000/svg}height",
        f"{output_height}mm",
    )
    svg_root.set(
        "{http://www.w3.org/2000/svg}width",
        f"{output_width}mm",
    )
    return svg_root


def unpack_spec_tuple(tpl: KohdeluokkaSpecTuple) -> KohdeluokkaSpec:
    use_id = None
    kohdeluokka = None
    if len(tpl) == 2:
        table_name, elem_count = tpl  # type: ignore[misc]
        alias = table_name
    elif len(tpl) == 3:
        table_name, elem_count, use_id = tpl  # type: ignore[misc]
        alias = table_name
    elif len(tpl) == 5:
        table_name, elem_count, kohdeluokka, alias, use_id = tpl  # type: ignore[misc]
    else:
        table_name, elem_count, kohdeluokka, alias = tpl  # type: ignore[misc]
    return KohdeluokkaSpec(alias, elem_count, kohdeluokka, table_name, use_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="mtkgpkg2svg",
        description="mtkgpkg2svg converts data from the Topographic Database of National Land survey of Finland to svg",
    )

    parser.add_argument(
        "north",
        type=float,
        help="The north coordinate of the centrepoint of the render",
    )
    parser.add_argument(
        "east", type=float, help="The east coordinate of the centrepoint of the render"
    )
    parser.add_argument(
        "--height", type=int, default=210, help="The height of the output in mm"
    )
    parser.add_argument(
        "--width", type=int, default=297, help="The width of the output in mm"
    )
    parser.add_argument(
        "--scale", type=int, default=25_000, help="The scale of the output (1 : scale)"
    )
    parser.add_argument("output_file", type=Path, help="Path to the output svg file")
    parser.add_argument(
        "input_file", type=Path, nargs="+", help="Paths of the input .gpkg files"
    )

    args = parser.parse_args()

    main(
        args.north,
        args.east,
        args.height,
        args.width,
        args.scale,
        args.output_file,
        args.input_file,
    )
