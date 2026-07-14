"""
Download public survey metadata ZIP files from GSI.
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

import requests

from .config import (
    FISCAL_YEARS,
    REGIONS,
    build_download_url,
    validate_region,
    validate_year,
)

logger = logging.getLogger(__name__)


def download_file(url: str, output_path: Path, force: bool = False) -> bool:
    """Download a single file from URL to output_path. Returns True if successful."""
    if output_path.exists() and not force:
        logger.info(f"File already exists, skipping: {output_path.name}")
        return True

    try:
        logger.info(f"Downloading {output_path.name}...")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded: {output_path.name}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_one(
    year: str, region: str, output_dir: Path = Path("data/raw"), force: bool = False
) -> bool:
    """Download metadata for a specific year and region."""
    if not validate_year(year):
        logger.error(f"Invalid year: {year}. Available: {', '.join(FISCAL_YEARS)}")
        return False

    if not validate_region(region):
        logger.error(
            f"Invalid region: {region}. Available: {', '.join(REGIONS.keys())}"
        )
        return False

    url = build_download_url(year, region)
    region_name = REGIONS[region]
    filename = f"{year}{region}-files.zip"
    output_path = output_dir / filename

    logger.info(f"Metadata: {year} {region_name} ({filename})")
    return download_file(url, output_path, force=force)


def download_all(output_dir: Path = Path("data/raw"), force: bool = False) -> None:
    """Download metadata for all configured years and regions."""
    total = len(FISCAL_YEARS) * len(REGIONS)
    success = 0

    for year in FISCAL_YEARS:
        for region in REGIONS.keys():
            if download_one(year, region, output_dir, force):
                success += 1

    logger.info(f"Downloaded {success}/{total} files")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Download GSI metadata ZIP files")
    parser.add_argument("--year", help="Fiscal year (e.g., R07)")
    parser.add_argument("--region", help="Region code (e.g., A)")
    parser.add_argument("--output", type=Path, default=Path("data/raw"), help="Output directory")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    if args.year and args.region:
        success = download_one(args.year, args.region, args.output, args.force)
        exit(0 if success else 1)
    else:
        download_all(args.output, args.force)


if __name__ == "__main__":
    main()
