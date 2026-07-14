"""
Validate normalized metadata and check for consistency.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def validate_record(record: Dict[str, Any]) -> List[str]:
    """Validate a single record. Returns list of issues found."""
    issues = []

    # Required fields
    if not record.get("title"):
        issues.append("missing_title")
    if not record.get("abstract"):
        issues.append("missing_abstract")
    if not (
        record.get("westBoundLongitude")
        and record.get("eastBoundLongitude")
        and record.get("southBoundLatitude")
        and record.get("northBoundLatitude")
    ):
        issues.append("missing_bbox")

    if not record.get("coordinateReferenceSystem"):
        issues.append("missing_crs")

    # Data quality info
    if record.get("has_dataQualityInfo") != "Yes":
        issues.append("missing_dataQualityInfo")

    # Plausibility checks
    if record.get("metadataDateStamp"):
        try:
            date_str = record["metadataDateStamp"][:10]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            age_days = (now - date_obj).days
            if age_days > 3650:  # ~10 years
                issues.append("suspicious_old_dateStamp")
        except (ValueError, TypeError):
            issues.append("invalid_dateStamp_format")

    # Coordinate plausibility covering Japan's four extremities with a
    # safety margin, not just the mainland (an earlier ~130-145°E/30-45°N
    # range was tuned to Honshu/Hokkaido/Kyushu/Shikoku and silently
    # excluded all of Okinawa -- see HANDOVER.md):
    #   択捉島カモイワッカ岬 (north) 45.557°N, 148.857°E
    #   沖ノ鳥島 (south)             20.425°N, 136.082°E
    #   南鳥島 (east)                24.283°N, 153.987°E
    #   与那国島 (west)              24.450°N, 122.933°E
    try:
        west = float(record.get("westBoundLongitude", 0))
        east = float(record.get("eastBoundLongitude", 0))
        south = float(record.get("southBoundLatitude", 0))
        north = float(record.get("northBoundLatitude", 0))

        if not (122 <= west <= 155 and 122 <= east <= 155):
            issues.append("implausible_longitude")
        if not (20 <= south <= 46 and 20 <= north <= 46):
            issues.append("implausible_latitude")
    except (ValueError, TypeError):
        pass

    # Contact completeness
    if not record.get("contactOrganisation"):
        issues.append("missing_contact_organisation")

    return issues


def validate_all(
    input_file: Path = Path("data/normalized/metadata_inventory.csv"),
    output_file: Path = Path("data/normalized/validation_issues.json"),
) -> Dict[str, Any]:
    """Validate all records and generate issue report."""
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return {}

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    validation_results = {
        "total_records": len(records),
        "records_with_issues": 0,
        "issue_counts": {},
        "issue_details": [],
    }

    for record in records:
        issues = validate_record(record)
        if issues:
            validation_results["records_with_issues"] += 1
            for issue in issues:
                validation_results["issue_counts"][issue] = (
                    validation_results["issue_counts"].get(issue, 0) + 1
                )

            validation_results["issue_details"].append(
                {
                    "file": record.get("source_file"),
                    "issues": issues,
                }
            )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Validation complete: {validation_results['records_with_issues']}/{len(records)} records have issues")
    return validation_results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    validate_all()


if __name__ == "__main__":
    main()
