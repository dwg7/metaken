"""
Generate summary reports from normalized metadata.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def generate_overview_report(
    csv_file: Path = Path("data/normalized/metadata_inventory.csv"),
    validation_file: Path = Path("data/normalized/validation_issues.json"),
    output_file: Path = Path("reports/generated/overview.md"),
) -> None:
    """Generate overview report from metadata inventory."""
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return

    records = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    # Load validation results if available
    validation_results = {}
    if validation_file.exists():
        with open(validation_file, "r", encoding="utf-8") as f:
            validation_results = json.load(f)

    # Calculate statistics
    stats = {
        "total_files": len(records),
        "with_title": sum(1 for r in records if r.get("title")),
        "with_abstract": sum(1 for r in records if r.get("abstract")),
        "with_bbox": sum(
            1
            for r in records
            if r.get("westBoundLongitude")
            and r.get("eastBoundLongitude")
            and r.get("southBoundLatitude")
            and r.get("northBoundLatitude")
        ),
        "with_crs": sum(1 for r in records if r.get("coordinateReferenceSystem")),
        "with_dataQualityInfo": sum(1 for r in records if r.get("has_dataQualityInfo") == "Yes"),
        "with_referenceSystemInfo": sum(1 for r in records if r.get("has_referenceSystemInfo") == "Yes"),
        "with_distributionInfo": sum(1 for r in records if r.get("has_distributionInfo") == "Yes"),
    }

    # Generate report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Metadata Overview Report\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Total XML files: {stats['total_files']}\n")
        f.write(f"- Files with title: {stats['with_title']} ({100*stats['with_title']//stats['total_files']}%)\n")
        f.write(f"- Files with abstract: {stats['with_abstract']} ({100*stats['with_abstract']//stats['total_files']}%)\n")
        f.write(f"- Files with bounding box: {stats['with_bbox']} ({100*stats['with_bbox']//stats['total_files']}%)\n")
        f.write(f"- Files with CRS: {stats['with_crs']} ({100*stats['with_crs']//stats['total_files']}%)\n")
        f.write(f"- Files with dataQualityInfo: {stats['with_dataQualityInfo']} ({100*stats['with_dataQualityInfo']//stats['total_files']}%)\n")
        f.write(f"- Files with referenceSystemInfo: {stats['with_referenceSystemInfo']} ({100*stats['with_referenceSystemInfo']//stats['total_files']}%)\n")
        f.write(f"- Files with distributionInfo: {stats['with_distributionInfo']} ({100*stats['with_distributionInfo']//stats['total_files']}%)\n")

        if validation_results:
            f.write("\n## Validation Results\n\n")
            f.write(
                f"- Records with issues: {validation_results.get('records_with_issues', 0)}/{validation_results.get('total_records', 0)}\n"
            )
            if validation_results.get("issue_counts"):
                f.write("\n### Issue Breakdown\n\n")
                for issue, count in sorted(
                    validation_results["issue_counts"].items(), key=lambda x: -x[1]
                ):
                    f.write(f"- {issue}: {count}\n")

    logger.info(f"Report written to {output_file}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    generate_overview_report()


if __name__ == "__main__":
    main()
