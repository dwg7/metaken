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

- [ ] Create initial README
- [ ] Create HANDOVER
- [ ] Add `justfile`
- [ ] Add Python package skeleton
- [ ] Implement downloader for GSI metadata ZIP files
- [ ] Implement `download-one year region`
- [ ] Implement ZIP extraction
- [ ] Parse JMP 2.0 XML files
- [ ] Normalize key fields to CSV
- [ ] Compute basic completeness statistics
- [ ] Detect presence of `dataQualityInfo`
- [ ] Detect suspicious `dateStamp` values
- [ ] Produce first report for `R07 A`

## 15. Longer-term tasks

- [ ] Analyze all available fiscal years
- [ ] Compare regions
- [ ] Compare before/after JGD2024 transition
- [ ] Analyze quality statements in detail
- [ ] Identify template-derived metadata
- [ ] Resolve code-list values into human-readable labels
- [ ] Compare XML metadata fields with information available from other public survey records
- [ ] Explore automatic generation of lightweight metadata labels
- [ ] Publish generated reports through GitHub Pages

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
