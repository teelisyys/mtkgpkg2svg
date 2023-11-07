import argparse
import datetime
import logging
import sqlite3
import timeit
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Cursor
from textwrap import dedent
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from xml.etree import ElementTree

from tqdm import tqdm

from mtkgpkg2svg.kohdeluokka_definitions import (
    KohdeluokkaSpecTuple,
    overview_map,
    topographic_map,
)
from mtkgpkg2svg.utils import BoundingBox, ramer_douglas_peucker, sutherland_hodgman
from mtkgpkg2svg.wkb_utils import parse_gpkgblob

logging.basicConfig(level=logging.INFO)

LinearRing = List[Tuple[int, Tuple[float, float]]]
Styling = Dict[str, str]

GeoJson = Any


@dataclass
class KohdeluokkaSpec:
    alias: str
    elem_count: int
    kohdeluokka: Optional[int]
    table_name: str
    use_id: Optional[str]


# pylint: disable=too-many-arguments,disable=too-many-locals
def main(
    north: float,
    east: float,
    output_height: float,
    output_width: float,
    scale: int,
    output_path: Path,
    input_paths: List[Path],
    variant: str,
) -> None:
    workdir = Path(__file__).parent.parent

    bounding_box = determine_bounding_box(
        north, east, output_height, output_width, scale
    )
    svg_root = prepare_output(
        bounding_box, output_height, output_width, workdir, variant
    )

    for gpkg_path in input_paths:
        con = sqlite3.connect(gpkg_path)
        cur = con.cursor()

        table_names = frozenset(
            r[0]
            for r in cur.execute(
                """SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"""
            ).fetchall()
        )

        print([tn for tn in table_names if "rtree_" not in tn])

        tpl: KohdeluokkaSpecTuple
        kohdeluokat: List[KohdeluokkaSpecTuple] = topographic_map
        if variant == "overview":
            kohdeluokat = overview_map

        for tpl in kohdeluokat:
            logging.info("Starting  %s", tpl)
            try:
                t0 = timeit.default_timer()
                process_item_type(
                    cur, table_names, gpkg_path, bounding_box, svg_root, tpl
                )
                t1 = timeit.default_timer()
                logging.info(
                    "Completed %s in %s", tpl, datetime.timedelta(seconds=t1 - t0)
                )
            except ValueError:
                logging.exception("An error occured")
                # raise

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


def clip_to_bb(
    coordinates: List[Tuple[float, float]],
    bounding_box: BoundingBox,
) -> List[Tuple[float, float]]:
    if len(coordinates) > 10_000:
        if all(not is_inside_bb(p, bounding_box) for p in coordinates):
            return []

    return sutherland_hodgman(
        coordinates,
        bounding_box.north,
        bounding_box.east,
        bounding_box.south,
        bounding_box.west,
    )


def is_inside_bb(point: Tuple[float, float], bounding_box: BoundingBox) -> bool:
    return (
        bounding_box.west < point[0] < bounding_box.east
        and bounding_box.south < point[1] < bounding_box.north
    )


def simplify_coordinates(
    coordinates: List[Tuple[float, float]],
    bounding_box: BoundingBox,
) -> List[Tuple[float, float]]:
    return ramer_douglas_peucker(clip_to_bb(coordinates, bounding_box), 0.1)


def sty(raw_styling: Dict[str, str]) -> Styling:
    svgnsprfx = "{http://www.w3.org/2000/svg}"
    return {
        **{f"{svgnsprfx}{k.replace('_', '-')}": str(v) for k, v in raw_styling.items()},
    }


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
    logging.info("Found %i rows", len(rows))
    for row in tqdm(rows):
        for i in range(spec.elem_count):
            if (
                spec.kohdeluokka is not None
                and row[colmap["kohdeluokka"]] != spec.kohdeluokka
            ):
                continue
            geom_blob = row[colmap["geom"]]
            assert isinstance(geom_blob, bytes), f"{type(geom_blob)}"
            geometry = parse_gpkgblob(geom_blob)
            element = geometry.to_svg_element(
                sty({"class": f"{spec.alias} {spec.alias}_{i}"}), href_id=spec.use_id
            )
            if element is not None:
                svg_root.append(element)


def prepare_output(
    bounding_box: BoundingBox,
    output_height: float,
    output_width: float,
    workdir: Path,
    variant: str,
) -> ElementTree.Element:
    style = "topo"
    if variant == "overview":
        style = variant

    svg_root = ElementTree.Element("{http://www.w3.org/2000/svg}svg")
    style_elem = ElementTree.Element("{http://www.w3.org/2000/svg}style")
    with (workdir / f"styles/{style}/style.css").open() as ifd:
        style_elem.text = ifd.read()
    svg_root.append(style_elem)
    with (workdir / f"styles/{style}/defs.svg").open() as ifd:
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
        description="mtkgpkg2svg converts data from the Topographic Database of National Land Survey of Finland to svg",
    )

    parser.add_argument(
        "north",
        type=float,
        help="The north coordinate of the centre point of the render",
    )
    parser.add_argument(
        "east", type=float, help="The east coordinate of the centre point of the render"
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
    parser.add_argument(
        "--variant",
        type=str,
        choices=["topo", "overview"],
        default="topo",
        help="The presentation variant of the output",
    )
    parser.add_argument("output_file", type=Path, help="Path to the output svg file")
    parser.add_argument(
        "input_file", type=Path, nargs="+", help="Paths of the input .gpkg files"
    )

    args = parser.parse_args()

    import cProfile

    with cProfile.Profile() as pr:
        main(
            args.north,
            args.east,
            args.height,
            args.width,
            args.scale,
            args.output_file,
            args.input_file,
            args.variant,
        )
        pr.print_stats(sort="cumulative")
