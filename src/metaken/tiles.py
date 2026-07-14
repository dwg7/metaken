"""
Export survey extent bounding boxes as GeoJSON, for vector-tile generation
via tippecanoe (see justfile's `tiles` recipe).
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Same plausibility range as validate.validate_record's Japan bbox check.
# Covers Japan's four extremities with a safety margin, not just the
# mainland (an earlier ~130-145°E/30-45°N range silently dropped every
# Okinawa record's bbox from the map entirely; see HANDOVER.md):
#   択捉島カモイワッカ岬 (north) 45.557°N, 148.857°E
#   沖ノ鳥島 (south)             20.425°N, 136.082°E
#   南鳥島 (east)                24.283°N, 153.987°E -- only 0.013° inside
#                                the previous 154°E cap; widened to 155°E
#   与那国島 (west)              24.450°N, 122.933°E
# Records outside this range are already flagged in validate.py as
# implausible_longitude/implausible_latitude; excluded here too since a
# rectangle outside Japan would just be a stray, unreadable mark on this map.
JAPAN_LON_RANGE = (122, 155)
JAPAN_LAT_RANGE = (20, 46)

# A handful of records have a bbox spanning several degrees -- e.g. one file's
# extent covers lon 136.2-139.9, lat 36.4-38.5, roughly half of Honshu, which
# is not a plausible single public-survey extent (median extent is ~0.00005
# deg^2; p99.5 is 0.48 deg^2; this jumps to 2-8 deg^2 for a handful of
# records). Almost certainly a data-entry error in the source XML (duplicate
# or placeholder coordinates) rather than a real extent. Left unfiltered,
# tippecanoe duplicates these giant polygons into a huge number of tiles
# across every zoom level -- one test run produced a 190MB+ mbtiles from
# 5,636 features before this cutoff was added. 1 deg^2 sits cleanly between
# p99.5 (0.48) and the next real cluster (2.17 at p99.9).
MAX_PLAUSIBLE_AREA_DEG2 = 1.0


def bbox_to_polygon(west: float, east: float, south: float, north: float) -> Dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }


def build_geojson(
    csv_file: Path = Path("data/normalized/metadata_inventory.csv"),
    output_file: Path = Path("data/normalized/survey_extents.geojson"),
) -> int:
    """Write one Polygon feature per record with a plausible bounding box."""
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return 0

    features = []
    skipped_implausible = 0
    skipped_oversized = 0
    with open(csv_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                west = float(row["westBoundLongitude"])
                east = float(row["eastBoundLongitude"])
                south = float(row["southBoundLatitude"])
                north = float(row["northBoundLatitude"])
            except (KeyError, ValueError):
                continue
            if not (west < east and south < north):
                continue
            if not (
                JAPAN_LON_RANGE[0] <= west <= JAPAN_LON_RANGE[1]
                and JAPAN_LON_RANGE[0] <= east <= JAPAN_LON_RANGE[1]
                and JAPAN_LAT_RANGE[0] <= south <= JAPAN_LAT_RANGE[1]
                and JAPAN_LAT_RANGE[0] <= north <= JAPAN_LAT_RANGE[1]
            ):
                skipped_implausible += 1
                continue
            if (east - west) * (north - south) > MAX_PLAUSIBLE_AREA_DEG2:
                skipped_oversized += 1
                continue

            features.append(
                {
                    "type": "Feature",
                    "geometry": bbox_to_polygon(west, east, south, north),
                    "properties": {
                        "source_file": row.get("source_file", ""),
                        "fiscal_year": row.get("fiscal_year", ""),
                        "region_code": row.get("region_code", ""),
                        "title": row.get("title", ""),
                        "surveyTypeCategory": row.get("surveyTypeCategory", ""),
                        "has_dataQualityInfo": row.get("has_dataQualityInfo", ""),
                        "coordinateReferenceSystem": row.get("coordinateReferenceSystem", ""),
                    },
                }
            )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

    logger.info(
        f"Wrote {len(features)} extent features to {output_file} "
        f"({skipped_implausible} skipped as outside the plausible Japan range, "
        f"{skipped_oversized} skipped as larger than {MAX_PLAUSIBLE_AREA_DEG2} deg^2)"
    )
    return len(features)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    build_geojson()


if __name__ == "__main__":
    main()
