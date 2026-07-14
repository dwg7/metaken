# HANDOVER

This document records the current intent, assumptions, design notes, and near-term implementation plan for the `metaken` repository.

`metaken` is intended to be more than a parser for XML files. It is an empirical infrastructure project for evaluating the current practice of Japanese public survey metadata XML.

## 1. Project intent

`metaken` provides an empirical basis for discussing Japanese public survey metadata.

The central question is not whether metadata is necessary in general.

The central question is whether the current XML metadata required, submitted, reviewed, maintained, and published in the public survey workflow provides benefits proportional to its production and operational costs.

In short:

> The project is not anti-metadata.  
> The project is pro-useful-metadata.

## 2. Core framing

The project focuses on XML metadata for public survey results, especially metadata published by the Geospatial Information Authority of Japan (GSI).

It does not address metadata in the abstract.

The working hypothesis is:

> If useful information exists only in the XML metadata and cannot be derived from public survey records, survey result files, SAPLIS registration information, or review records, that information should be identified and evaluated.
>
> If such information does not exist, or if its benefit is limited, the current XML metadata practice should be reconsidered.

The intended framing is therefore cost-benefit, not presence-absence.

The weak form of the question is:

> Is there any information in the XML metadata?

The stronger and more relevant question is:

> Is there useful information in the XML metadata that justifies the cost of creating, correcting, reviewing, maintaining, and publishing it?

## 3. Why this matters

Public survey metadata is embedded in public survey workflows.

Even if metadata appears to be available to GSI as a submitted artifact, it is not cost-free. It imposes costs on:

- planning organizations;
- survey contractors;
- reviewers;
- metadata maintainers;
- downstream users who must interpret the files;
- the broader public survey industry.

If metadata is useful, these costs may be justified.

If metadata is mainly a procedural artifact, or if most of its contents can be mechanically generated from other records, the current practice should be redesigned.

## 4. Analytical posture

This repository should be framed as empirical, not rhetorical.

Avoid claims such as:

> Metadata is unnecessary.

Prefer claims such as:

> The actual contents, completeness, consistency, and usefulness of the current XML metadata practice should be measured.

The project should help distinguish between:

1. metadata as useful public data infrastructure; and
2. metadata as a procedural artifact that merely appears to document quality.

A useful guiding phrase is:

> If metadata is important, it should be generated, maintained, validated, and distributed in a way that users and machines can actually use.

## 5. Initial observations from sample XML files

A small initial sample of public survey metadata XML files suggested the following preliminary observations:

- Many files mainly contain title, abstract, bounding box, contact information, dates, and JMP 2.0 metadata declaration.
- Some files do not contain an independent `dataQualityInfo` section.
- When quality information exists, it may be limited, template-like, or not directly useful for non-expert quality judgment.
- Some metadata may include suspicious inconsistencies, such as old `dateStamp` values in otherwise recent records.
- Some fields are represented as numeric codes, such as `dateType`, `role`, `topicCategory`, and `hierarchyLevel`, which are not directly useful to non-expert users without code-list resolution.
- Some information appears likely to be derivable from existing survey records, survey result files, or registration/review systems.

These observations are preliminary and must be tested at scale.

## 6. Initial research questions

The first version of `metaken` should answer the following questions:

1. How many XML files are available by fiscal year and regional office?
2. What fields are actually present in the files?
3. How often is `dataQualityInfo` present?
4. What quality-related elements are actually recorded?
5. Are quality statements meaningful, repeated, or template-like?
6. How often are metadata dates inconsistent or suspicious?
7. How often are coordinate reference systems specified?
8. How often are bounding boxes present and plausible?
9. How often are contact fields complete?
10. Which fields appear manually entered?
11. Which fields could be generated automatically?
12. Which fields, if any, appear to contain useful information not available elsewhere?

## 7. Data source and scope

The initial data source is the GSI public survey metadata download site:

- <https://www.gsi.go.jp/GIS/metaindex.html>

The site provides metadata ZIP files by fiscal year and regional office.

Initial scope:

- GSI-published public survey metadata XML files
- JMP 2.0 XML structure
- Fiscal year and regional office based ZIP files
- Basic completeness and consistency analysis
- Quality-information presence analysis

Out of scope for now:

- Evaluating individual survey results themselves
- Judging individual survey projects
- Criticizing specific planning organizations or survey contractors
- Replacing official GSI systems
- Making legal or administrative determinations

## 8. Suggested repository structure

```text
metaken/
  README.md
  HANDOVER.md
  LICENSE
  justfile
  pyproject.toml
  data/
    raw/
    extracted/
    normalized/
  src/
    metaken/
      __init__.py
      fetch.py
      extract.py
      parse.py
      normalize.py
      validate.py
      report.py
  notebooks/
    001_overview.ipynb
    002_quality_fields.ipynb
    003_date_anomalies.ipynb
  reports/
    overview.md
    metadata_quality.md
    generated/
  schema/
    normalized_metadata.schema.json
  docs/
    index.md
```

## 9. Operational model

Use `just` for repeatable batch operations.

The `justfile` should be the operational entry point of the repository.

Recurring tasks should be exposed through `just` commands rather than documented as ad-hoc shell snippets.

Expected commands:

```bash
just clean
just download
just download-one R07 A
just extract
just parse
just validate
just report
just all
```

Suggested `justfile` skeleton:

```makefile
# Show available commands
default:
    just --list

# Remove generated files
clean:
    rm -rf data/raw
    rm -rf data/extracted
    rm -rf data/normalized
    rm -rf reports/generated

# Download all configured metadata ZIP files
download:
    python -m metaken.fetch

# Download a specific fiscal year and region
download-one year region:
    python -m metaken.fetch --year {{year}} --region {{region}}

# Extract downloaded ZIP files
extract:
    python -m metaken.extract

# Parse XML files into normalized records
parse:
    python -m metaken.parse

# Validate normalized metadata
validate:
    python -m metaken.validate

# Generate reports
report:
    python -m metaken.report

# Full workflow
all: clean download extract parse validate report
```

## 10. Initial normalized fields

The initial parser should extract at least:

```text
source_file
fiscal_year
region_code
fileIdentifier
metadataStandardName
metadataStandardVersion
metadataDateStamp
title
abstract
citationDate
dateType
topicCategory
language
characterSet
hierarchyLevel
contactOrganisation
contactRole
westBoundLongitude
eastBoundLongitude
southBoundLatitude
northBoundLatitude
coordinateReferenceSystem
geographicDescription
has_dataQualityInfo
has_distributionInfo
has_referenceSystemInfo
element_count
```

Useful derived fields may include:

```text
bbox_area_approx
dateStamp_year
citationDate_year
date_inconsistency_flag
has_email
email_suspicious_flag
has_phone
crs_family
quality_statement_count
quality_quantitative_result_count
lineage_statement
template_like_lineage_flag
```

## 11. Validation checks

The first validator should check:

- title presence;
- abstract presence;
- geographic bounding box presence;
- bounding box plausibility;
- coordinate reference system presence;
- `dataQualityInfo` presence;
- `referenceSystemInfo` presence;
- `distributionInfo` presence;
- metadata date plausibility;
- citation date versus metadata date consistency;
- contact organization presence;
- email presence and suspicious patterns;
- code-list fields that require interpretation;
- repeated or template-like lineage and quality statements.

## 12. Expected outputs

Possible normalized and derived outputs:

```text
data/normalized/metadata_inventory.csv
data/normalized/metadata_inventory.parquet
data/normalized/quality_info_summary.csv
data/normalized/date_anomalies.csv
data/normalized/crs_summary.csv
data/normalized/bbox_summary.csv
reports/generated/overview.md
reports/generated/metadata_quality.md
```

Possible summary indicators:

```text
total_xml_files
files_with_title
files_with_abstract
files_with_bbox
files_with_dataQualityInfo
files_with_referenceSystemInfo
files_with_distributionInfo
files_with_suspicious_dateStamp
most_common_topicCategory
most_common_hierarchyLevel
most_common_crs
```

## 13. Implementation sequence

Suggested first implementation sequence:

1. Create repository description and initial README.
2. Add `HANDOVER.md`.
3. Add `justfile` skeleton.
4. Add Python package skeleton under `src/metaken`.
5. Implement URL extraction from the GSI metadata index page.
6. Implement `download-one` for one fiscal year and one region.
7. Implement ZIP extraction.
8. Implement XML parsing for a small sample.
9. Generate `metadata_inventory.csv`.
10. Implement basic validation checks.
11. Generate first Markdown report for `R07 A`.
12. Expand to all regions for a selected fiscal year.
13. Expand across fiscal years.

## 14. Near-term tasks

- [x] Create initial README
- [x] Create HANDOVER
- [x] Add `justfile`
- [x] Add Python package skeleton
- [x] Implement downloader for GSI metadata ZIP files
- [x] Implement `download-one year region`
- [x] Implement ZIP extraction
- [x] Parse JMP 2.0 XML files
- [x] Normalize key fields to CSV
- [x] Compute basic completeness statistics
- [x] Detect presence of `dataQualityInfo`
- [x] Detect suspicious `dateStamp` values
- [x] Produce first report for `R07 A`

## 15. Longer-term tasks

- [ ] Analyze all available fiscal years
- [ ] Compare regions
- [ ] Compare before/after JGD2024 transition
- [ ] Analyze quality statements in detail
- [ ] Identify template-derived metadata
- [ ] Resolve code-list values into human-readable labels
- [ ] Compare XML metadata fields with information available from other public survey records
- [ ] Explore automatic generation of lightweight metadata labels
- [x] Publish generated reports through GitHub Pages (`docs/index.html` generator implemented; GitHub Pages needs to be enabled in repo settings)

## 16. Institutional posture

This repository should not be framed as anti-GSI or anti-metadata.

It should be framed as a small, reproducible, evidence-based tool for improving public geospatial metadata.

A useful external message is:

> `metaken` analyzes the actual contents of public survey metadata XML so that metadata policy can be discussed using evidence rather than intuition.

A useful internal message is:

> The purpose is to turn a potentially exhausting institutional debate into a reproducible data analysis problem.

## 17. Strategic meaning

This project fits the broader idea that public geospatial infrastructure should be implemented as working, inspectable, and reusable tools.

For public survey metadata, that means moving the discussion from:

> Metadata is necessary, therefore XML metadata should continue.

or:

> XML metadata is burdensome, therefore metadata is unnecessary.

to:

> What information is actually present?  
> What value does it have?  
> What can be generated automatically?  
> What should be redesigned so that metadata is useful to people, machines, and future public geospatial infrastructure?

## 18. Caution

Avoid overclaiming from small samples.

The initial sample analysis is useful for designing the parser and hypotheses, but conclusions should be based on larger-scale analysis across fiscal years and regions.

Also avoid evaluating individual projects or organizations. The intended level of analysis is structural and institutional, not personal or project-specific.

## 19. One-line summary

`metaken` is empirical infrastructure for testing whether Japanese public survey metadata XML functions as useful metadata or merely as a procedural artifact.

## 20. Progress log

**2026-07-14**

Implemented the full pilot pipeline end to end (`just clean download extract parse validate report`):

- `src/metaken/config.py`: fiscal year list and region-code table, GSI download URL builder.
- `src/metaken/fetch.py`: downloads ZIP archives from `service.gsi.go.jp`, per year/region or in bulk, skips existing files unless `--force`.
- `src/metaken/extract.py`: extracts ZIPs into `data/extracted/`.
- `src/metaken/parse.py`: parses JMP 2.0 XML. Note — GSI's actual XML uses a custom namespace (`http://zgate.gsi.go.jp/ch/jmp/`), not the ISO 19115 `gmd`/`gco` namespaces the field list in §10 implied; the parser was written against the real namespace after inspecting sample files.
- `src/metaken/validate.py`: required-field, date-plausibility, and Japan-bbox-plausibility checks.
- `src/metaken/report.py`: Markdown report (`reports/generated/overview.md`, not committed) and a static HTML report (`docs/index.html`, committed, intended for GitHub Pages).

Pilot run on `R07 A` (北海道, FY2025), 717 files:

- title/abstract: 100% present
- bounding box: 77% present
- `dataQualityInfo`: 5% present
- `referenceSystemInfo`: 3% present
- explicit CRS code: 0% present
- contact organisation: 96% of files are *missing* it

This matches the preliminary observations in §5 — most files carry the descriptive
basics (title, abstract, bbox) but quality/lineage/CRS information is rare. The 0%
explicit-CRS figure for this sample should be treated as provisional until checked
across more regions/years; it may reflect a real gap in the source data or a field
this parser has not yet located correctly.

Decision: `data/normalized/*.csv` (parsed fields, including verbatim `title`/`abstract`
text from GSI's XML) is committed to the repo rather than gitignored, as the empirical
record this project produces. `data/raw/` and `data/extracted/` (the original ZIPs/XML)
remain gitignored — redistributing those wholesale is a separate question under GSI's
content terms of use (see README § LICENSE) that has not been decided.

**2026-07-14 (same day, continued) — full-dataset run**

Ran `just all` across every year/region GSI currently publishes and fixed what it
surfaced:

- GSI's download index (checked live) only has ZIP links for `R05`/`R06`/`R07`;
  `config.FISCAL_YEARS` originally listed back to `H31` on the assumption GSI keeps
  a longer retention window. It doesn't (or not on this page) — trimmed the list to
  the three years that actually resolve, so `just download` no longer spends 55 of
  88 requests on 404s. Re-check the source page before re-adding older years.
- ~11% of XML entries across the full dataset (1,231 of 11,059) are **zero-byte
  files inside GSI's own ZIP archives** — not a bug in `extract`/`parse`, confirmed
  by reading `file_size` off the raw zip's `ZipInfo` directly. This is itself an
  empirical finding about the current practice, not just noise to filter out.
- One filename (`メタデータ(R06D0254_3level).xml`) doesn't follow the
  `{year}{region}{seq}` convention; the naive `name[:3]`/`name[3]` slice in
  `parse.py` silently produced garbage (`fiscal_year="メタデ"`). Replaced with a
  regex search (`FILENAME_YEAR_REGION`) that finds the pattern anywhere in the
  filename instead of assuming position 0.

Full-dataset numbers (R05–R07, 11,059 files, 6,510 with a usable title after
excluding the zero-byte files):

- title/abstract: 89% present (vs. 100% in the R07-A-only pilot — the pilot
  sample's completeness was not representative; the zero-byte files pull this down)
- bounding box: 59%
- `dataQualityInfo`: 5%
- explicit CRS code: still 0% across all 11,059 files — this now looks like a real
  gap in the source data rather than a parser miss, though the field has only been
  checked against one XPath (`referenceSystemIdentifier`)

Added a survey-type breakdown per user request (基準点測量 vs. 地理空間情報を作る測量):
JMP 2.0 has no structured code list for this distinction (`topicCategory` is 83%
one single ISO value, `013`/"location", regardless of actual survey type — not
useful for this split). Implemented as a heuristic in
`metaken.parse.classify_survey_type`: title contains
基準点測量/水準測量/三角点測量/多角測量 → 基準点測量, else (non-empty title) →
地理空間情報を作る測量. Matched against **title only**, not abstract — most surveys
set a few auxiliary control points regardless of their primary purpose, so an
abstract-text match over-classified (55% of records) versus a title match (10%).
Result: 1,060 基準点測量 (10%) vs. 8,745 地理空間情報を作る測量 (79%) vs. 1,254 unknown
(11%, mostly the zero-byte files). Notably, `dataQualityInfo` presence is 2% for
基準点測量 vs. 6% for 地理空間情報を作る測量 — a first concrete data point for the
project's central cost-benefit question, though from one heuristic split and worth
re-checking once a cleaner classification signal is found.

**2026-07-14 (same day, continued) — survey-type category revised after user review**

The user's own field intuition put the true split at roughly **7:3**, the opposite
of the 10:79 title-only result above. Rather than assume either number, walked
through several classification passes against the actual title/abstract text with
the user before settling on a definition, since "measurement vs. mapping" turned
out to be genuinely ambiguous from the data alone:

1. Title-only match on 基準点測量-type phrases → 10% control-point. Too narrow:
   most public-survey titles name the parent project (e.g. "オサツナイ川外砂防工事
   地形調査"), not the specific advisory-registered task, so this undercounted.
2. Matched the structured `作業内容は…です` clause in the abstract (present in 64%
   of records) instead, treating a short clause as "pure control-point work" →
   32:68. Closer, but still inverted from the user's expectation.
3. User's correction: **the category is about what the survey's deliverable is,
   not whether 基準点 is mentioned at all.** A survey that sets control points as
   one step toward an application (boundary work, road ledger correction, drainage
   management, etc.) still counts as the survey-primary category; only an
   *explicit* mapping/imagery-product term marks the other category. Renamed the
   categories accordingly: **測量メイン** (survey-primary — includes 基準点測量, 用地
   測量, 路線測量, 境界確定測量, 道路台帳補正, and anything else without an explicit
   map-product term) and **地図メイン** (map-primary — explicitly names a mapping or
   imagery product: 都市計画図, 都市計画基本図, 地形図, 地形測量, 地形調査, ドローン,
   無人航空機, UAV, 点群, レーザ, 空中写真, オルソ, 写真測量, 写真地図, 数値地形図,
   森林基本図).

Final numbers (`metaken.parse.SURVEY_TYPE_MAP_PRODUCT`, matched against
title+abstract combined): **測量メイン 7,549 (68% of all records, 77% of
classified) : 地図メイン 2,256 (20% / 23%)** — matches the user's 7:3 expectation.
`dataQualityInfo` presence is 3% for 測量メイン vs. 14% for 地図メイン (~5x), a
sharper version of the same cost-benefit signal as the superseded split above.

This category boundary was fitted to one domain expert's expectation using a
fairly small, hand-picked keyword list — it has not been validated against a
labeled sample, and the "explicit map-product term" rule will misclassify records
that describe a mapping deliverable without using one of the listed words (e.g.
"砂防基盤図作成業務" — "基盤図" isn't in the keyword list, so it fell into 測量メイン
in a spot-check). Worth a proper precision/recall check against manually-labeled
examples before leaning on this split for any published conclusion.
