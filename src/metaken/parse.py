"""
Parse JMP 2.0 XML metadata files into normalized records.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from lxml import etree

logger = logging.getLogger(__name__)

# JMP 2.0 XML namespace
JMP_NS = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gsr": "http://www.isotc211.org/2005/gsr",
    "gss": "http://www.isotc211.org/2005/gss",
}


def extract_text(elem: Optional[etree._Element]) -> str:
    """Extract text from an element, handling gco:CharacterString."""
    if elem is None:
        return ""
    text = (elem.text or "").strip()
    if not text:
        char_string = elem.find(".//gco:CharacterString", JMP_NS)
        if char_string is not None:
            text = (char_string.text or "").strip()
    return text


def parse_xml_file(xml_path: Path) -> Dict[str, Any]:
    """Parse a single JMP 2.0 XML file into a record."""
    record: Dict[str, Any] = {
        "source_file": xml_path.name,
        "fiscal_year": "",
        "region_code": "",
    }

    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        # Extract fiscal year and region from filename (e.g., R07A0020.xml)
        name = xml_path.stem
        if len(name) >= 4:
            record["fiscal_year"] = name[:3]  # R07, R06, etc.
            record["region_code"] = name[3] if len(name) > 3 else ""

        # File identifier
        file_id = root.find(".//gmd:fileIdentifier/gco:CharacterString", JMP_NS)
        record["fileIdentifier"] = extract_text(file_id)

        # Metadata standard
        std_name = root.find(
            ".//gmd:metadataStandardName/gco:CharacterString", JMP_NS
        )
        record["metadataStandardName"] = extract_text(std_name)

        std_version = root.find(
            ".//gmd:metadataStandardVersion/gco:CharacterString", JMP_NS
        )
        record["metadataStandardVersion"] = extract_text(std_version)

        # Date stamp
        date_stamp = root.find(
            ".//gmd:dateStamp/gco:Date", JMP_NS
        ) or root.find(".//gmd:dateStamp/gco:DateTime", JMP_NS)
        record["metadataDateStamp"] = extract_text(date_stamp)

        # Title and abstract
        title = root.find(
            ".//gmd:title/gco:CharacterString", JMP_NS
        ) or root.find(".//gmd:identificationInfo//gmd:citation//gmd:title/gco:CharacterString", JMP_NS)
        record["title"] = extract_text(title)

        abstract = root.find(
            ".//gmd:abstract/gco:CharacterString", JMP_NS
        ) or root.find(".//gmd:identificationInfo//gmd:abstract/gco:CharacterString", JMP_NS)
        record["abstract"] = extract_text(abstract)

        # Citation date
        citation_date = root.find(
            ".//gmd:citation//gmd:date/gmd:CI_Date/gmd:date/gco:Date", JMP_NS
        ) or root.find(".//gmd:citation//gmd:date/gmd:CI_Date/gmd:date/gco:DateTime", JMP_NS)
        record["citationDate"] = extract_text(citation_date)

        citation_type = root.find(
            ".//gmd:citation//gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode",
            JMP_NS,
        )
        record["dateType"] = citation_type.get("codeListValue", "") if citation_type is not None else ""

        # Topic category
        topic = root.find(
            ".//gmd:topicCategory/gmd:MD_TopicCategoryCode", JMP_NS
        )
        record["topicCategory"] = (topic.text or "") if topic is not None else ""

        # Character set and language
        char_set = root.find(
            ".//gmd:characterSet/gmd:MD_CharacterSetCode", JMP_NS
        )
        record["characterSet"] = char_set.get("codeListValue", "") if char_set is not None else ""

        language = root.find(
            ".//gmd:language/gco:CharacterString", JMP_NS
        ) or root.find(".//gmd:language/gmd:LanguageCode", JMP_NS)
        record["language"] = extract_text(language)

        # Hierarchy level
        hier_level = root.find(
            ".//gmd:hierarchyLevel/gmd:MD_ScopeCode", JMP_NS
        )
        record["hierarchyLevel"] = hier_level.get("codeListValue", "") if hier_level is not None else ""

        # Contact information
        contact = root.find(
            ".//gmd:contact//gmd:organisationName/gco:CharacterString", JMP_NS
        )
        record["contactOrganisation"] = extract_text(contact)

        contact_role = root.find(
            ".//gmd:contact//gmd:role/gmd:CI_RoleCode", JMP_NS
        )
        record["contactRole"] = contact_role.get("codeListValue", "") if contact_role is not None else ""

        # Bounding box
        extent = root.find(".//gmd:extent//gmd:EX_GeographicBoundingBox", JMP_NS)
        if extent is not None:
            west = extent.find(".//gmd:westBoundLongitude/gco:Decimal", JMP_NS)
            east = extent.find(".//gmd:eastBoundLongitude/gco:Decimal", JMP_NS)
            south = extent.find(".//gmd:southBoundLatitude/gco:Decimal", JMP_NS)
            north = extent.find(".//gmd:northBoundLatitude/gco:Decimal", JMP_NS)

            record["westBoundLongitude"] = (west.text or "") if west is not None else ""
            record["eastBoundLongitude"] = (east.text or "") if east is not None else ""
            record["southBoundLatitude"] = (south.text or "") if south is not None else ""
            record["northBoundLatitude"] = (north.text or "") if north is not None else ""
        else:
            record["westBoundLongitude"] = ""
            record["eastBoundLongitude"] = ""
            record["southBoundLatitude"] = ""
            record["northBoundLatitude"] = ""

        # CRS
        crs = root.find(
            ".//gmd:referenceSystemInfo//gmd:MD_ReferenceSystem//gmd:referenceSystemIdentifier//gmd:code/gco:CharacterString",
            JMP_NS,
        )
        record["coordinateReferenceSystem"] = extract_text(crs)

        # Geographic description
        geo_desc = root.find(
            ".//gmd:extent//gmd:EX_GeographicDescription//gmd:geographicIdentifier//gmd:code/gco:CharacterString",
            JMP_NS,
        )
        record["geographicDescription"] = extract_text(geo_desc)

        # Presence checks
        record["has_dataQualityInfo"] = "Yes" if root.find(".//gmd:dataQualityInfo", JMP_NS) is not None else "No"
        record["has_distributionInfo"] = "Yes" if root.find(".//gmd:distributionInfo", JMP_NS) is not None else "No"
        record["has_referenceSystemInfo"] = "Yes" if root.find(".//gmd:referenceSystemInfo", JMP_NS) is not None else "No"

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
