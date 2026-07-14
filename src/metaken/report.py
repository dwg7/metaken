"""
Generate summary reports from normalized metadata.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def load_records(csv_file: Path) -> List[Dict[str, Any]]:
    with open(csv_file, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_validation(validation_file: Path) -> Dict[str, Any]:
    if not validation_file.exists():
        return {}
    with open(validation_file, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_stats(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Field-completeness counts, shared by the Markdown and HTML reports."""
    return {
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


# Order matches parse.classify_survey_type's possible outputs.
SURVEY_TYPE_CATEGORIES = ["基準点測量", "地理空間情報を作る測量", "不明（タイトルなし）"]


def compute_survey_type_breakdown(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Per-category counts and field-completeness, keyed by classify_survey_type's output.

    The category itself is a title-keyword heuristic (see parse.classify_survey_type) —
    JMP 2.0 has no structured code list for this distinction.
    """
    breakdown: Dict[str, Dict[str, int]] = {}
    for category in SURVEY_TYPE_CATEGORIES:
        subset = [
            r for r in records
            if (r.get("surveyTypeCategory") or "不明（タイトルなし）") == category
        ]
        breakdown[category] = {
            "count": len(subset),
            "with_abstract": sum(1 for r in subset if r.get("abstract")),
            "with_bbox": sum(
                1
                for r in subset
                if r.get("westBoundLongitude")
                and r.get("eastBoundLongitude")
                and r.get("southBoundLatitude")
                and r.get("northBoundLatitude")
            ),
            "with_crs": sum(1 for r in subset if r.get("coordinateReferenceSystem")),
            "with_dataQualityInfo": sum(1 for r in subset if r.get("has_dataQualityInfo") == "Yes"),
        }
    return breakdown


def generate_overview_report(
    csv_file: Path = Path("data/normalized/metadata_inventory.csv"),
    validation_file: Path = Path("data/normalized/validation_issues.json"),
    output_file: Path = Path("reports/generated/overview.md"),
) -> None:
    """Generate overview report from metadata inventory."""
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return

    records = load_records(csv_file)
    validation_results = load_validation(validation_file)
    stats = compute_stats(records)
    survey_breakdown = compute_survey_type_breakdown(records)

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

        f.write("\n## Survey Type Breakdown\n\n")
        f.write(
            "JMP 2.0 has no structured field distinguishing control-point surveys "
            "(基準点測量) from surveys that produce geospatial data products. "
            "Category is a heuristic keyword match against `title`; see "
            "`metaken.parse.classify_survey_type`.\n\n"
        )
        f.write("| Category | Count | % of total | abstract | bbox | CRS | dataQualityInfo |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for category in SURVEY_TYPE_CATEGORIES:
            b = survey_breakdown[category]
            n = b["count"] or 1
            f.write(
                f"| {category} | {b['count']:,} | {100*b['count']//stats['total_files']}% | "
                f"{100*b['with_abstract']//n}% | {100*b['with_bbox']//n}% | "
                f"{100*b['with_crs']//n}% | {100*b['with_dataQualityInfo']//n}% |\n"
            )

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


# Human-readable labels for the HTML report
FIELD_LABELS = {
    "with_title": "タイトル (title)",
    "with_abstract": "概要 (abstract)",
    "with_bbox": "空間範囲 (bounding box)",
    "with_crs": "座標参照系 (CRS)",
    "with_dataQualityInfo": "品質情報 (dataQualityInfo)",
    "with_referenceSystemInfo": "参照系情報 (referenceSystemInfo)",
    "with_distributionInfo": "流通情報 (distributionInfo)",
}

ISSUE_LABELS = {
    "missing_title": "タイトルなし",
    "missing_abstract": "概要なし",
    "missing_bbox": "空間範囲なし",
    "missing_crs": "座標参照系の明示なし",
    "missing_dataQualityInfo": "品質情報なし",
    "missing_contact_organisation": "連絡先組織名なし",
    "suspicious_old_dateStamp": "dateStamp が不自然に古い",
    "implausible_latitude": "緯度が日本の範囲外",
    "implausible_longitude": "経度が日本の範囲外",
    "invalid_dateStamp_format": "dateStamp の形式が不正",
}


def _bar_rows(items: List[tuple], total: int, bar_color_var: str) -> str:
    """Render a list of (label, count) as accessible bar chart rows."""
    rows = []
    max_count = max((count for _, count in items), default=1) or 1
    for label, count in items:
        pct = round(100 * count / total) if total else 0
        width_pct = round(100 * count / max_count, 1) if max_count else 0
        rows.append(
            f"""
        <div class="bar-row">
          <div class="bar-label">{label}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width: {width_pct}%; background: var({bar_color_var});"></div>
          </div>
          <div class="bar-value">{count:,} <span class="bar-pct">({pct}%)</span></div>
        </div>"""
        )
    return "".join(rows)


def _table_rows(items: List[tuple], total: int) -> str:
    rows = []
    for label, count in items:
        pct = round(100 * count / total, 1) if total else 0
        rows.append(f"<tr><td>{label}</td><td>{count:,}</td><td>{pct}%</td></tr>")
    return "".join(rows)


def generate_html_report(
    csv_file: Path = Path("data/normalized/metadata_inventory.csv"),
    validation_file: Path = Path("data/normalized/validation_issues.json"),
    output_file: Path = Path("docs/index.html"),
) -> None:
    """Generate a static HTML report for publishing under docs/ (GitHub Pages)."""
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return

    records = load_records(csv_file)
    validation_results = load_validation(validation_file)
    stats = compute_stats(records)
    total = stats["total_files"] or 1

    years = sorted({r.get("fiscal_year", "") for r in records if r.get("fiscal_year")})
    regions = sorted({r.get("region_code", "") for r in records if r.get("region_code")})
    scope = f"{', '.join(years)} / {', '.join(regions)}" if years else "—"

    completeness_items = [
        (FIELD_LABELS[k], stats[k]) for k in FIELD_LABELS if k in stats
    ]
    completeness_items.sort(key=lambda x: -x[1])

    survey_breakdown = compute_survey_type_breakdown(records)
    survey_count_items = [(cat, survey_breakdown[cat]["count"]) for cat in SURVEY_TYPE_CATEGORIES]

    issue_counts = validation_results.get("issue_counts", {})
    issue_items = [
        (ISSUE_LABELS.get(k, k), v) for k, v in issue_counts.items()
    ]
    issue_items.sort(key=lambda x: -x[1])

    records_with_issues = validation_results.get("records_with_issues", 0)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    survey_table_rows = "".join(
        f"<tr><td>{category}</td>"
        f"<td>{survey_breakdown[category]['count']:,}</td>"
        f"<td>{100*survey_breakdown[category]['with_abstract']//(survey_breakdown[category]['count'] or 1)}%</td>"
        f"<td>{100*survey_breakdown[category]['with_bbox']//(survey_breakdown[category]['count'] or 1)}%</td>"
        f"<td>{100*survey_breakdown[category]['with_crs']//(survey_breakdown[category]['count'] or 1)}%</td>"
        f"<td>{100*survey_breakdown[category]['with_dataQualityInfo']//(survey_breakdown[category]['count'] or 1)}%</td></tr>"
        for category in SURVEY_TYPE_CATEGORIES
    )

    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>metaken — 公共測量メタデータ実態調査</title>
<style>
  :root {{
    --surface-1:      #fcfcfb;
    --page:           #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --bar-color:      #256abf;
    --border:         rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1:      #1a1a19;
      --page:           #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --bar-color:      #3987e5;
      --border:         rgba(255,255,255,0.10);
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    line-height: 1.55;
  }}
  main {{
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 20px 96px;
  }}
  h1 {{
    font-size: 26px;
    font-weight: 600;
    margin: 0 0 4px;
  }}
  .subtitle {{
    color: var(--text-secondary);
    margin: 0 0 32px;
    font-size: 15px;
  }}
  .meta {{
    color: var(--text-muted);
    font-size: 13px;
    margin: 0 0 40px;
  }}
  section {{
    margin-bottom: 48px;
  }}
  h2 {{
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 4px;
  }}
  .section-note {{
    color: var(--text-secondary);
    font-size: 14px;
    margin: 0 0 20px;
  }}
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1px;
    background: var(--gridline);
    border: 1px solid var(--gridline);
    border-radius: 8px;
    overflow: hidden;
  }}
  .stat-tile {{
    background: var(--surface-1);
    padding: 18px 16px;
  }}
  .stat-value {{
    font-size: 30px;
    font-weight: 600;
    font-variant-numeric: proportional-nums;
  }}
  .stat-label {{
    color: var(--text-secondary);
    font-size: 13px;
    margin-top: 4px;
  }}
  .bar-row {{
    display: grid;
    grid-template-columns: 200px 1fr 100px;
    align-items: center;
    gap: 12px;
    padding: 7px 0;
  }}
  .bar-label {{
    font-size: 13px;
    color: var(--text-secondary);
  }}
  .bar-track {{
    height: 24px;
    background: transparent;
    border-bottom: 1px solid var(--baseline);
    display: flex;
    align-items: flex-end;
  }}
  .bar-fill {{
    height: 14px;
    border-radius: 4px 4px 0 0;
    min-width: 2px;
  }}
  .bar-value {{
    font-size: 13px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }}
  .bar-pct {{
    color: var(--text-muted);
  }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 20px;
  }}
  table.data-table caption {{
    text-align: left;
    color: var(--text-muted);
    font-size: 12px;
    margin-bottom: 8px;
  }}
  table.data-table th, table.data-table td {{
    text-align: left;
    padding: 6px 10px;
    border-bottom: 1px solid var(--gridline);
    font-variant-numeric: tabular-nums;
  }}
  table.data-table th {{
    color: var(--text-secondary);
    font-weight: 500;
  }}
  details summary {{
    cursor: pointer;
    color: var(--text-secondary);
    font-size: 13px;
    margin-top: 8px;
  }}
  footer {{
    border-top: 1px solid var(--gridline);
    padding-top: 20px;
    color: var(--text-muted);
    font-size: 12px;
  }}
  footer a {{
    color: var(--text-secondary);
  }}
  code {{
    background: var(--gridline);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 12px;
  }}
</style>
</head>
<body>
<main>
  <h1>metaken</h1>
  <p class="subtitle">公共測量成果等メタデータ XML の実態調査 — 国土地理院公開データの経験的分析</p>
  <p class="meta">対象: {scope}　·　生成日時: {generated_at}</p>

  <section>
    <h2>概要</h2>
    <div class="stat-grid">
      <div class="stat-tile">
        <div class="stat-value">{stats['total_files']:,}</div>
        <div class="stat-label">解析対象 XML ファイル数</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value">{100*stats['with_dataQualityInfo']//total}%</div>
        <div class="stat-label">品質情報 (dataQualityInfo) あり</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value">{100*stats['with_crs']//total}%</div>
        <div class="stat-label">座標参照系を明示</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value">{records_with_issues:,}</div>
        <div class="stat-label">検証で問題を検出したファイル</div>
      </div>
    </div>
  </section>

  <section>
    <h2>フィールド充足率</h2>
    <p class="section-note">各フィールドが実際に記載されていたファイルの割合（全 {stats['total_files']:,} 件中）</p>
    <div class="bars">{_bar_rows(completeness_items, total, '--bar-color')}</div>
    <details>
      <summary>表で見る</summary>
      <table class="data-table">
        <thead><tr><th>フィールド</th><th>件数</th><th>割合</th></tr></thead>
        <tbody>{_table_rows(completeness_items, total)}</tbody>
      </table>
    </details>
  </section>

  <section>
    <h2>測量種別ごとの集計</h2>
    <p class="section-note">
      JMP 2.0 には基準点測量と地理空間情報を作る測量を区別する構造化フィールドが存在しないため、
      <code>title</code> のキーワード一致による推定分類です（多くの測量は主目的に関わらず補助的に基準点を設置するため、
      abstract 中の「基準点」への言及ではなく title のみで判定しています）。
    </p>
    <div class="bars">{_bar_rows(survey_count_items, total, '--bar-color')}</div>
    <table class="data-table">
      <thead><tr><th>種別</th><th>件数</th><th>abstract</th><th>bbox</th><th>CRS</th><th>dataQualityInfo</th></tr></thead>
      <tbody>{survey_table_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>検証で検出された問題</h2>
    <p class="section-note">構造的・整合性チェックで検出された問題の内訳（延べ件数）</p>
    <div class="bars">{_bar_rows(issue_items, total, '--bar-color')}</div>
    <details>
      <summary>表で見る</summary>
      <table class="data-table">
        <thead><tr><th>問題種別</th><th>件数</th><th>割合</th></tr></thead>
        <tbody>{_table_rows(issue_items, total)}</tbody>
      </table>
    </details>
  </section>

  <footer>
    <p>
      データ出典: <a href="https://www.gsi.go.jp/GIS/metaindex.html">国土地理院 公共測量成果等のメタデータダウンロードサイト</a>。
      本サイトの利用は<a href="http://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html">地理院コンテンツ利用規約</a>に従います。
    </p>
    <p>
      本レポートは <code>just report</code> により <code>data/normalized/metadata_inventory.csv</code> から自動生成されています。
      ソースコードは <a href="https://github.com/dwg7/metaken">GitHub: dwg7/metaken</a>。
    </p>
  </footer>
</main>
</body>
</html>
"""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    logger.info(f"HTML report written to {output_file}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    generate_overview_report()
    generate_html_report()


if __name__ == "__main__":
    main()
