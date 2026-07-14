"""
Parse JMP 2.0 XML metadata files into normalized records.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from lxml import etree

logger = logging.getLogger(__name__)

# GSI JMP namespace (custom)
GSI_NS = "http://zgate.gsi.go.jp/ch/jmp/"

# There is no structured code list in JMP 2.0 that distinguishes control-point
# surveys from surveys that produce geospatial data products (topicCategory and
# hierarchyLevel do not encode this). Titles follow a public-survey work-naming
# convention that usually ends with the survey type, e.g. "...３級基準点測量",
# so a title keyword match is used as a heuristic proxy instead. Matched only
# against the title (not the abstract): most surveys set a handful of auxiliary
# control points as a means to an end, and abstract text mentions of "基準点"
# for that reason are not a reliable signal of the survey's primary purpose.
SURVEY_TYPE_CONTROL_POINT = re.compile(r"基準点測量|水準測量|三角点測量|多角測量")

# Filenames are normally {fiscal_year}{region}{seq}, e.g. "R07A0001.xml", but a
# few files in the wild don't follow the convention (e.g. a Japanese-prefixed
# name). Search for the pattern anywhere rather than slicing blindly by position.
FILENAME_YEAR_REGION = re.compile(r"(R\d{2}|H\d{2})([A-K])")


def classify_survey_type(title: str) -> str:
    """Heuristic classification: control-point survey vs. geospatial-data survey."""
    if not title:
        return "不明（タイトルなし）"
    if SURVEY_TYPE_CONTROL_POINT.search(title):
        return "基準点測量"
    return "地理空間情報を作る測量"


def extract_text(elem: Optional[etree._Element], ns: str = GSI_NS) -> str:
    """Extract text from an element."""
    if elem is None:
        return ""
    text = (elem.text or "").strip()
    if not text and elem.tag.endswith("language"):
        # Handle language isoCode
        iso_code = elem.find(f"{{{ns}}}isoCode")
        if iso_code is not None:
            text = (iso_code.text or "").strip()
    return text


def parse_xml_file(xml_path: Path, ns: str = GSI_NS) -> Dict[str, Any]:
    """Parse a single JMP 2.0 XML file into a record."""
    record: Dict[str, Any] = {
        "source_file": xml_path.name,
        "fiscal_year": "",
        "region_code": "",
    }

    try:
        tree = etree.parse(str(xml_path), etree.XMLParser(recover=True))
        root = tree.getroot()

        # Extract fiscal year and region from filename
        name = xml_path.stem
        match = FILENAME_YEAR_REGION.search(name)
        if match:
            record["fiscal_year"] = match.group(1)
            record["region_code"] = match.group(2)

        # Create namespace map for searching
        def find_elem(path: str) -> Optional[etree._Element]:
            return root.find(f".//{{{ns}}}{path}".replace("//", f"//{{{ns}}}"), None)

        # Title and abstract from identificationInfo
        title_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}title")
        record["title"] = extract_text(title_elem, ns)

        abstract_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}abstract")
        record["abstract"] = extract_text(abstract_elem, ns)

        record["surveyTypeCategory"] = classify_survey_type(record["title"])

        # Citation date and type
        date_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}date//{{{ns}}}date")
        record["citationDate"] = extract_text(date_elem, ns)

        date_type_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}date//{{{ns}}}dateType")
        record["dateType"] = (date_type_elem.text or "") if date_type_elem is not None else ""

        # Topic category, character set, language, hierarchy level
        topic_elem = root.find(f".//{{{ns}}}topicCategory")
        record["topicCategory"] = (topic_elem.text or "") if topic_elem is not None else ""

        char_set_elem = root.find(f".//{{{ns}}}characterSet")
        record["characterSet"] = (char_set_elem.text or "") if char_set_elem is not None else ""

        language_elem = root.find(f".//{{{ns}}}language")
        record["language"] = extract_text(language_elem, ns)

        hier_level_elem = root.find(f".//{{{ns}}}hierarchyLevel")
        record["hierarchyLevel"] = (hier_level_elem.text or "") if hier_level_elem is not None else ""

        # Contact information
        contact_elem = root.find(f".//{{{ns}}}pointOfContact//{{{ns}}}organisationName")
        record["contactOrganisation"] = extract_text(contact_elem, ns)

        contact_role_elem = root.find(f".//{{{ns}}}pointOfContact//{{{ns}}}role")
        record["contactRole"] = (contact_role_elem.text or "") if contact_role_elem is not None else ""

        # Bounding box
        west_elem = root.find(f".//{{{ns}}}westBoundLongitude")
        east_elem = root.find(f".//{{{ns}}}eastBoundLongitude")
        south_elem = root.find(f".//{{{ns}}}southBoundLatitude")
        north_elem = root.find(f".//{{{ns}}}northBoundLatitude")

        record["westBoundLongitude"] = (west_elem.text or "") if west_elem is not None else ""
        record["eastBoundLongitude"] = (east_elem.text or "") if east_elem is not None else ""
        record["southBoundLatitude"] = (south_elem.text or "") if south_elem is not None else ""
        record["northBoundLatitude"] = (north_elem.text or "") if north_elem is not None else ""

        # CRS
        crs_elem = root.find(f".//{{{ns}}}referenceSystemIdentifier")
        record["coordinateReferenceSystem"] = extract_text(crs_elem, ns)

        # Geographic description
        geo_desc_elem = root.find(f".//{{{ns}}}EX_GeographicDescription//{{{ns}}}geographicIdentifier")
        record["geographicDescription"] = extract_text(geo_desc_elem, ns)

        # Metadata standard and file identifier
        std_name_elem = root.find(f".//{{{ns}}}metadataStandardName")
        record["metadataStandardName"] = extract_text(std_name_elem, ns)

        std_version_elem = root.find(f".//{{{ns}}}metadataStandardVersion")
        record["metadataStandardVersion"] = extract_text(std_version_elem, ns)

        file_id_elem = root.find(f".//{{{ns}}}fileIdentifier")
        record["fileIdentifier"] = extract_text(file_id_elem, ns)

        date_stamp_elem = root.find(f".//{{{ns}}}dateStamp")
        record["metadataDateStamp"] = extract_text(date_stamp_elem, ns)

        # Presence checks
        record["has_dataQualityInfo"] = "Yes" if root.find(f".//{{{ns}}}dataQualityInfo") is not None else "No"
        record["has_distributionInfo"] = "Yes" if root.find(f".//{{{ns}}}distributionInfo") is not None else "No"
        record["has_referenceSystemInfo"] = "Yes" if root.find(f".//{{{ns}}}referenceSystemInfo") is not None else "No"

        # Element count
        record["element_count"] = len(root)

    except Exception as e:
        logger.error(f"Error parsing {xml_path.name}: {e}")

    return record


def parse_all(
    extracted_dir: Path = Path("data/extracted"),
    output_file: Path = Path("data/normalized/metadata_inventory.csv"),
) -> int:
    """Parse all XML files and write to CSV."""
    extracted_dir = extracted_dir.resolve()
    xml_files = sorted(extracted_dir.glob("**/*.xml")) + sorted(
        extracted_dir.glob("**/*.XML")
    )

    if not xml_files:
        logger.warning(f"No XML files found in {extracted_dir}")
        return 0

    records = []
    for xml_path in xml_files:
        record = parse_xml_file(xml_path)
        records.append(record)

    # Write CSV
    if records:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(records[0].keys())

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        logger.info(f"Wrote {len(records)} records to {output_file}")
        return len(records)

    return 0


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parse_all()


if __name__ == "__main__":
    main()
