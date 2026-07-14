"""
Configuration for metaken project.
"""

from typing import Dict

# GSI Metadata service base URL
GSI_METADATA_BASE = "https://service.gsi.go.jp/geolib/contents/screen/geolib/metadata"

# Fiscal years actually published on https://www.gsi.go.jp/GIS/metaindex.html
# (checked 2026-07-14: only R05-R07 have download links; earlier years 404).
# GSI appears to retire older years as new ones are added — update this list
# by checking the source page rather than assuming a fixed retention window.
FISCAL_YEARS = [
    "R07",  # FY2025
    "R06",  # FY2024
    "R05",  # FY2023
]

# Available regions with Japanese names
REGIONS: Dict[str, str] = {
    "A": "北海道",      # Hokkaido
    "B": "東北",        # Tohoku
    "C": "関東",        # Kanto
    "D": "北陸",        # Hokuriku
    "E": "中部",        # Chubu
    "F": "近畿",        # Kinki
    "G": "中国",        # Chugoku
    "H": "四国",        # Shikoku
    "I": "九州",        # Kyushu
    "J": "沖縄",        # Okinawa
    "K": "企画部",      # Planning Division
}


def build_download_url(year: str, region: str) -> str:
    """Build GSI metadata ZIP download URL."""
    return f"{GSI_METADATA_BASE}/{year}{region}-files.zip"


def validate_year(year: str) -> bool:
    """Check if year is valid."""
    return year in FISCAL_YEARS


def validate_region(region: str) -> bool:
    """Check if region is valid."""
    return region in REGIONS
