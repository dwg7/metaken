"""
Extract XML files from downloaded ZIP archives.
"""

import logging
from pathlib import Path
from zipfile import ZipFile

logger = logging.getLogger(__name__)


def extract_zip(zip_path: Path, output_dir: Path) -> int:
    """Extract a single ZIP file. Returns count of extracted files."""
    if not zip_path.exists():
        logger.error(f"ZIP file not found: {zip_path}")
        return 0

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(zip_path) as zf:
            zf.extractall(output_dir)
        extracted_count = len(list(zf.namelist()))
        logger.info(f"Extracted {extracted_count} files from {zip_path.name}")
        return extracted_count
    except Exception as e:
        logger.error(f"Failed to extract {zip_path}: {e}")
        return 0


def extract_all(raw_dir: Path = Path("data/raw"), output_dir: Path = Path("data/extracted")) -> None:
    """Extract all ZIP files from raw directory."""
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()

    zip_files = sorted(raw_dir.glob("*-files.zip"))
    if not zip_files:
        logger.warning(f"No ZIP files found in {raw_dir}")
        return

    total = 0
    for zip_path in zip_files:
        extracted = extract_zip(zip_path, output_dir / zip_path.stem)
        total += extracted

    logger.info(f"Extracted {total} total files")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    extract_all()


if __name__ == "__main__":
    main()
