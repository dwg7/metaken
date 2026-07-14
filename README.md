# metaken

Empirical analysis of Japanese public survey metadata XML published by the Geospatial Information Authority of Japan (GSI).

`metaken` is a repository for collecting, parsing, validating, and analyzing XML metadata files for Japanese public survey results.
The repository focuses on the actual structure, completeness, consistency, and usefulness of the current XML metadata practice.

国土地理院が公開する公共測量成果等メタデータ XML を収集・解析し、現行の公共測量メタデータが実際にどのような情報を含み、品質表示・検索・再利用・機械処理にどの程度寄与しているかを検証するためのリポジトリです。

## STATUS

The fetch → extract → parse → validate → report pipeline is implemented and runnable end to end via `just all`. See [`docs/index.html`](docs/index.html) for the latest generated report and [HANDOVER.md § 20](HANDOVER.md#20-progress-log) for the progress log and pilot findings.

## SYNOPSIS

GSI publishes public survey metadata XML files by fiscal year and regional office.
GSI describes these metadata files as overview data for survey results, including information such as survey summary, work title, advisory number, data extent, and planning organization. The files are distributed as ZIP archives by fiscal year and regional office.

Source page:

- <https://www.gsi.go.jp/GIS/metaindex.html>

`metaken` downloads these XML metadata files, parses their JMP 2.0 structure, normalizes selected fields, and generates reproducible analyses.

Typical workflow:

```bash
just clean
just download
just extract
just parse
just validate
just report
```

For a focused pilot analysis:

```bash
just clean
just download-one R07 A
just extract
just parse
just validate
just report
```

The first practical target is likely to be `R07 A`, namely FY2025 Hokkaido metadata, because it is a manageable regional subset and useful for testing parser behavior, completeness checks, and quality-information analysis.

## OBJECTIVE

The objective of `metaken` is not to criticize metadata as a concept.

The objective is to empirically evaluate the current XML metadata practice for public survey results.

In particular, this repository asks:

1. What information is actually present in public survey metadata XML files?
2. How often do XML files contain explicit quality information?
3. Are metadata dates, coordinate reference systems, bounding boxes, and contact fields internally consistent?
4. Which fields appear to be manually entered, and which fields could be generated automatically?
5. Does the current XML metadata practice provide useful information that is not already available from public survey records, survey result files, SAPLIS registration information, or review records?
6. Is the current metadata practice suitable for non-expert users, AI systems, and modern web-based geospatial data discovery?
7. Does the benefit of creating, reviewing, maintaining, and publishing these XML metadata files exceed the cost imposed on planning organizations, survey contractors, reviewers, and the broader survey industry?

The central question is therefore not:

> Is metadata necessary?

The central question is:

> Does the current XML metadata practice provide enough practical value to justify its cost, and if not, what should replace or supplement it?

## BACKGROUND

Public survey metadata is embedded in Japan's public survey workflow.
Even when metadata appears to be available to GSI as a submitted artifact, its creation, correction, review, maintenance, and interpretation impose costs on multiple actors.

At the same time, metadata should be useful if it is to remain part of public geospatial data infrastructure.

Useful metadata should help users and machines understand:

- what the survey result is;
- where it applies;
- when it was created or published;
- who created or provided it;
- what coordinate reference system it uses;
- what quality or accuracy information is available;
- what limitations or intended uses should be considered;
- whether the data can be discovered, interpreted, and reused reliably.

`metaken` treats the published XML files as an empirical dataset and examines whether the current practice actually supports these purposes.

## SCOPE

Initial scope:

- Public survey metadata XML files published by GSI
- Fiscal year and regional-office based ZIP archives
- JMP 2.0 XML metadata
- Basic completeness checks
- Structural consistency checks
- Quality-information presence analysis
- Date anomaly detection
- Coordinate reference system and bounding box analysis

Out of scope, at least initially:

- Evaluating the accuracy of individual survey results
- Judging individual survey projects
- Criticizing specific planning organizations or contractors
- Replacing official GSI systems
- Making legal or administrative determinations

## DATA SOURCE

The primary data source is the GSI public survey metadata download site.

GSI provides XML metadata ZIP archives by fiscal year and by regional office. The site explains that the metadata includes survey summary, work title, advisory number, data extent, and planning organization, and that GSI provides metadata held by GSI through the download site.

- <https://www.gsi.go.jp/GIS/metaindex.html>

Users of GSI-published data should follow the applicable GSI content terms of use.

## ANALYSIS TARGETS

The initial parser should extract at least the following fields:

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

Additional derived fields may include:

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

## VALIDATION QUESTIONS

`metaken` should support reproducible validation checks, including:

- Does the XML file have a title?
- Does it have an abstract?
- Does it have a bounding box?
- Does it identify a coordinate reference system?
- Does it include `dataQualityInfo`?
- Does it include `referenceSystemInfo`?
- Does it include `distributionInfo`?
- Is `dateStamp` plausible?
- Is `dateStamp` unexpectedly old compared with the citation date?
- Are longitude and latitude values plausible for Japan?
- Are code-list fields unresolved numeric codes?
- Is the contact information structurally complete?
- Are quality statements meaningful, empty, or template-like?

## BATCH OPERATIONS

This repository uses [`just`](https://github.com/casey/just) to manage repeatable batch operations.

The `justfile` is the operational entry point of this repository.
All recurring tasks should be exposed through `just` commands rather than documented as ad-hoc shell snippets.

Show available commands:

```bash
just
```

Clean generated outputs:

```bash
just clean
```

Download metadata ZIP files:

```bash
just download
```

Download metadata for a specific fiscal year and regional office:

```bash
just download-one R07 A
```

Extract downloaded ZIP files:

```bash
just extract
```

Parse XML files into normalized records:

```bash
just parse
```

Run structural and consistency checks:

```bash
just validate
```

Generate summary reports:

```bash
just report
```

Run the full workflow:

```bash
just all
```

The intended full workflow is equivalent to:

```bash
just clean
just download
just extract
just parse
just validate
just report
```

## PROPOSED JUST COMMANDS

The initial `justfile` may expose the following commands:

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

## REPOSITORY STRUCTURE

Proposed structure:

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

## EXPECTED OUTPUTS

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

## INITIAL RESEARCH QUESTIONS

The first reports should aim to answer:

1. How many XML metadata files are available by fiscal year and regional office?
2. What percentage includes `dataQualityInfo`?
3. What types of quality information are actually recorded?
4. Are quality statements specific or template-like?
5. How often are metadata date stamps suspicious?
6. How often are coordinate reference systems explicitly specified?
7. How often are bounding boxes present and plausible?
8. How often are contact fields complete?
9. Which fields appear suitable for automatic generation?
10. Which fields, if any, appear to contain useful information that is not available elsewhere?

## POSTURE

This repository is pro-useful-metadata.

It does not assume that metadata is unnecessary.
It assumes that metadata should be evaluated by its actual usefulness, maintainability, and cost.

The intended message is:

> If metadata is important, it should be generated, maintained, validated, and distributed in a way that users and machines can actually use.

`metaken` is therefore an empirical infrastructure project for better public geospatial metadata.

## LICENSE

CCO

Code and derived analysis outputs should have an explicit open license before publication.

Use of source metadata downloaded from GSI should follow the applicable GSI content terms of use.
