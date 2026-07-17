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

# There is no structured code list in JMP 2.0 that distinguishes 測量メイン
# (surveys whose deliverable is measurement itself -- control points, boundary/
# route/land survey, etc.) from 地図メイン (surveys that produce a mapping/imagery
# data product) -- topicCategory and hierarchyLevel do not encode this. Classified
# by keyword against title+abstract: only an *explicit* map/imagery-product term
# (都市計画図, 地形図, ドローン, 点群, オルソ, ...) marks 地図メイン; everything else
# (including 基準点測量, 用地測量, 路線測量, 境界確定測量, 道路台帳補正, etc.)
# defaults to 測量メイン. This ordering and the category split (roughly 3:1 in the
# full R05-R07 dataset) were calibrated against a domain expert's expectation for
# the true 測量メイン:地図メイン ratio in public survey work -- see HANDOVER.md.
#
# 航空写真 added after the R05-R07 sample validation against 公共測量実施情報
# (HANDOVER.md "sample validation against 公共測量実施情報"): record F0532's
# title "高槻市デジタル航空写真撮影業務" was misclassified as 測量メイン because
# it uses 航空写真, not the only aerial-photo synonym this list had (空中写真).
# The other false negatives found in that 20-record sample (数値図化, 数値撮影,
# 数値地形図データの作成 as the *official* 測量種別, not necessarily verbatim in
# the title/abstract text) are deliberately left unfixed here -- adding keywords
# from an official category label without seeing the actual source text would be
# guessing, not the same kind of concrete fix as this one.
SURVEY_TYPE_MAP_PRODUCT = re.compile(
    r"都市計画図|都市計画基本図|地形図|地形測量|地形調査|ドローン|無人航空機|UAV|"
    r"点群|レーザ|空中写真|航空写真|オルソ|写真測量|写真地図|数値地形図|森林基本図"
)

# Filenames are normally {fiscal_year}{region}{seq}, e.g. "R07A0001.xml", but a
# few files in the wild don't follow the convention (e.g. a Japanese-prefixed
# name). Search for the pattern anywhere rather than slicing blindly by position.
FILENAME_YEAR_REGION = re.compile(r"(R\d{2}|H\d{2})([A-K])")

# Official JMP2.0 code lists (codeListValue -> label). Unlike SURVEY_TYPE_MAP_PRODUCT
# above, these are fixed ISO 19115-derived enumerations, not a heuristic -- verified
# against GSI's own JMP2.0 spec (https://www.gsi.go.jp/common/000259949.pdf), Appendix
# C XML Schema (enumeration order) cross-checked with the code tables in
# §5.1 CI_DateTypeCode, §5.2 CI_RoleCode, §5.7 MD_ScopeCode, §5.9 MD_TopicCategoryCode.
TOPIC_CATEGORY_CODES: Dict[str, str] = {
    "001": "農業 (farming)",
    "002": "生物相 (biota)",
    "003": "境界 (boundaries)",
    "004": "気象 (climatologyMeteorologyAtmosphere)",
    "005": "経済 (economy)",
    "006": "高さ (elevation)",
    "007": "環境 (environment)",
    "008": "地球科学の情報 (geoscientificInformation)",
    "009": "健康 (health)",
    "010": "全地球基本地図画像 (imageryBaseMapsEarthCover)",
    "011": "軍事情報 (intelligenceMilitary)",
    "012": "陸水 (inlandWaters)",
    "013": "位置 (location)",
    "014": "大洋 (oceans)",
    "015": "土地台帳計画 (planningCadastre)",
    "016": "社会 (society)",
    "017": "構造物 (structure)",
    "018": "運輸 (transportation)",
    "019": "公共事業・通信 (utilitiesCommunication)",
    "020": "その他の主題 (N/A)",
}

HIERARCHY_LEVEL_CODES: Dict[str, str] = {  # MD_ScopeCode
    "001": "属性 (attribute)",
    "002": "属性型 (attributeType)",
    "003": "収集用機器 (collectionHardware)",
    "004": "収集作業 (collectionSession)",
    "005": "データ集合 (dataset)",
    "006": "シリーズ (series)",
    "007": "非地理データ集合 (nonGeographicDataset)",
    "008": "次元グループ (dimensionGroup)",
    "009": "地物 (feature)",
    "010": "地物型 (featureType)",
    "011": "特質の型 (propertyType)",
    "012": "現場作業 (fieldSession)",
    "013": "ソフトウェア (software)",
    "014": "サービス (service)",
    "015": "モデル (model)",
    "016": "タイル (tile)",
}

DATE_TYPE_CODES: Dict[str, str] = {  # CI_DateTypeCode
    "001": "作成日 (creation)",
    "002": "刊行日 (publication)",
    "003": "改訂日 (revision)",
}

ROLE_CODES: Dict[str, str] = {  # CI_RoleCode
    "001": "情報資源提供者 (resourceProvider)",
    "002": "管理者 (custodian)",
    "003": "所有者 (owner)",
    "004": "利用者 (user)",
    "005": "配布者 (distributor)",
    "006": "創作者 (originator)",
    "007": "問合せ先 (pointOfContact)",
    "008": "主要な調査担当者 (principalInvestigator)",
    "009": "処理担当者 (processor)",
    "010": "刊行者 (publisher)",
    "011": "著作者 (author)",
}


def resolve_codelist(code: str, table: Dict[str, str]) -> str:
    """Resolve a raw JMP2.0 codeListValue to its label. Returns the raw code
    unchanged if unresolved (blank, or a malformed value such as the one stray
    non-zero-padded "1" observed in dateType)."""
    return table.get(code, code)


def classify_crs_family(crs_code: str) -> str:
    """Coarse geodetic-datum family from a coordinateReferenceSystem code string
    (e.g. "JGD2011 / (B,L)" -> "JGD2011"), for tracking the JGD2024 transition."""
    if not crs_code:
        return ""
    if "JGD2024" in crs_code:
        return "JGD2024"
    if "JGD2011" in crs_code:
        return "JGD2011"
    if "JGD2000" in crs_code:
        return "JGD2000"
    if crs_code.startswith("TD"):
        return "TD（旧日本測地系）"
    return "その他/不明"


def classify_survey_type(title: str, abstract: str = "") -> str:
    """Heuristic classification: 測量メイン (survey-primary) vs. 地図メイン (map-primary)."""
    text = f"{title}　{abstract}".strip("　")
    if not text:
        return "不明（記載なし）"
    if SURVEY_TYPE_MAP_PRODUCT.search(text):
        return "地図メイン"
    return "測量メイン"


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
    # Recorded unconditionally (before the parse attempt) so a zero-byte file
    # -- which fails etree.parse() with "Document is empty" -- is still
    # distinguishable from a well-formed file that's merely missing fields.
    # See HANDOVER.md: GSI's own ZIP archives contain a substantial and
    # region-specific rate of zero-byte XML entries.
    file_size_bytes = xml_path.stat().st_size

    record: Dict[str, Any] = {
        "source_file": xml_path.name,
        "fiscal_year": "",
        "region_code": "",
        "file_size_bytes": file_size_bytes,
    }

    # Extract fiscal year and region from the filename, not the XML content,
    # and do it before the parse attempt: a zero-byte file still has a real
    # filename, and region×year corrupt-file rates (see HANDOVER.md) need
    # these fields populated even when the XML itself can't be parsed at all.
    match = FILENAME_YEAR_REGION.search(xml_path.stem)
    if match:
        record["fiscal_year"] = match.group(1)
        record["region_code"] = match.group(2)

    try:
        tree = etree.parse(str(xml_path), etree.XMLParser(recover=True))
        root = tree.getroot()

        # Create namespace map for searching
        def find_elem(path: str) -> Optional[etree._Element]:
            return root.find(f".//{{{ns}}}{path}".replace("//", f"//{{{ns}}}"), None)

        # Title and abstract from identificationInfo
        title_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}title")
        record["title"] = extract_text(title_elem, ns)

        abstract_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}abstract")
        record["abstract"] = extract_text(abstract_elem, ns)

        record["surveyTypeCategory"] = classify_survey_type(record["title"], record["abstract"])

        # Citation date and type
        date_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}date//{{{ns}}}date")
        record["citationDate"] = extract_text(date_elem, ns)

        date_type_elem = root.find(f".//{{{ns}}}identificationInfo//{{{ns}}}citation//{{{ns}}}date//{{{ns}}}dateType")
        record["dateType"] = (date_type_elem.text or "") if date_type_elem is not None else ""
        record["dateType_label"] = resolve_codelist(record["dateType"], DATE_TYPE_CODES)

        # Topic category, character set, language, hierarchy level
        topic_elem = root.find(f".//{{{ns}}}topicCategory")
        record["topicCategory"] = (topic_elem.text or "") if topic_elem is not None else ""
        record["topicCategory_label"] = resolve_codelist(record["topicCategory"], TOPIC_CATEGORY_CODES)

        char_set_elem = root.find(f".//{{{ns}}}characterSet")
        record["characterSet"] = (char_set_elem.text or "") if char_set_elem is not None else ""

        language_elem = root.find(f".//{{{ns}}}language")
        record["language"] = extract_text(language_elem, ns)

        hier_level_elem = root.find(f".//{{{ns}}}hierarchyLevel")
        record["hierarchyLevel"] = (hier_level_elem.text or "") if hier_level_elem is not None else ""
        record["hierarchyLevel_label"] = resolve_codelist(record["hierarchyLevel"], HIERARCHY_LEVEL_CODES)

        # Contact information
        contact_elem = root.find(f".//{{{ns}}}pointOfContact//{{{ns}}}organisationName")
        record["contactOrganisation"] = extract_text(contact_elem, ns)

        contact_role_elem = root.find(f".//{{{ns}}}pointOfContact//{{{ns}}}role")
        record["contactRole"] = (contact_role_elem.text or "") if contact_role_elem is not None else ""
        record["contactRole_label"] = resolve_codelist(record["contactRole"], ROLE_CODES)

        # Bounding box
        west_elem = root.find(f".//{{{ns}}}westBoundLongitude")
        east_elem = root.find(f".//{{{ns}}}eastBoundLongitude")
        south_elem = root.find(f".//{{{ns}}}southBoundLatitude")
        north_elem = root.find(f".//{{{ns}}}northBoundLatitude")

        record["westBoundLongitude"] = (west_elem.text or "") if west_elem is not None else ""
        record["eastBoundLongitude"] = (east_elem.text or "") if east_elem is not None else ""
        record["southBoundLatitude"] = (south_elem.text or "") if south_elem is not None else ""
        record["northBoundLatitude"] = (north_elem.text or "") if north_elem is not None else ""

        # CRS: GSI's JMP 2.0 does not use the ISO 19115 referenceSystemInfo/
        # referenceSystemIdentifier path (that element name never occurs in the
        # actual files). The CRS is instead a sibling of the bbox fields inside
        # the same EX_GeographicBoundingBox, as extentReferenceSystem/code (e.g.
        # "JGD2011 / (B,L)") -- scoped to west_elem's own parent so this pairs
        # with the geographic (lon/lat) bbox specifically, not the separate
        # plane-rectangular-coordinate bbox that dataQualityInfo's scope/extent
        # also carries under its own EX_CoordinateBoundingBox/extentReferenceSystem.
        record["coordinateReferenceSystem"] = ""
        if west_elem is not None:
            geo_bbox = west_elem.getparent()
            if geo_bbox is not None:
                crs_code_elem = geo_bbox.find(f"{{{ns}}}extentReferenceSystem/{{{ns}}}code")
                record["coordinateReferenceSystem"] = extract_text(crs_code_elem, ns)
        record["crs_family"] = classify_crs_family(record["coordinateReferenceSystem"])

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
        dqi_elem = root.find(f".//{{{ns}}}dataQualityInfo")
        record["has_dataQualityInfo"] = "Yes" if dqi_elem is not None else "No"
        record["has_distributionInfo"] = "Yes" if root.find(f".//{{{ns}}}distributionInfo") is not None else "No"
        record["has_referenceSystemInfo"] = "Yes" if root.find(f".//{{{ns}}}referenceSystemInfo") is not None else "No"

        # Quality statement content (DQ_DataQuality has scope/lineage/report;
        # only ~5% of records have dataQualityInfo at all -- these fields let
        # the report distinguish genuinely specific quality text from
        # boilerplate copied verbatim across records, and check whether the
        # (rarer still) quantitative accuracy values are actually present.
        # First occurrence only per record; report.py does the cross-record
        # frequency analysis that needs the full column.
        record["quality_statement_count"] = 0
        record["quality_evaluationMethodDescription"] = ""
        record["quality_specification_title"] = ""
        record["quality_explanation"] = ""
        record["quality_quantitative_result_count"] = 0
        record["lineage_statement"] = ""
        if dqi_elem is not None:
            record["quality_statement_count"] = len(dqi_elem.findall(f".//{{{ns}}}DQ_Element"))

            eval_method_elem = dqi_elem.find(f".//{{{ns}}}evaluationMethodDescription")
            record["quality_evaluationMethodDescription"] = extract_text(eval_method_elem, ns)

            spec_title_elem = dqi_elem.find(
                f".//{{{ns}}}DQ_ConformanceResult/{{{ns}}}specification/{{{ns}}}title"
            )
            record["quality_specification_title"] = extract_text(spec_title_elem, ns)

            explanation_elem = dqi_elem.find(f".//{{{ns}}}explanation")
            record["quality_explanation"] = extract_text(explanation_elem, ns)

            record["quality_quantitative_result_count"] = len(
                dqi_elem.findall(f".//{{{ns}}}DQ_QuantitativeResult//{{{ns}}}otherValue")
            )

            lineage_elem = dqi_elem.find(f".//{{{ns}}}lineage//{{{ns}}}statement")
            record["lineage_statement"] = extract_text(lineage_elem, ns)

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
