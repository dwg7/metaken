"""
Download public survey metadata ZIP files from GSI.
"""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GSI metadata ZIP files")
    parser.add_argument("--year", help="Fiscal year (e.g., R07)")
    parser.add_argument("--region", help="Region code (e.g., A)")
    args = parser.parse_args()

    logger.info("Fetching metadata files...")
    if args.year and args.region:
        logger.info(f"Downloading {args.year} {args.region}")
    else:
        logger.info("Downloading all configured metadata files")


if __name__ == "__main__":
    main()
