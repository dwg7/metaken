"""
Configuration for metaken project.
"""

from typing import Dict

# GSI Metadata service base URL
GSI_METADATA_BASE = "https://service.gsi.go.jp/geolib/contents/screen/geolib/metadata"

# Available fiscal years (most recent first)
FISCAL_YEARS = [
    "R07",  # FY2025
    "R06",  # FY2024
    "R05",  # FY2023
    "R04",  # FY2022
    "R03",  # FY2021
    "R02",  # FY2020
    "R01",  # FY2019
    "H31",  # FY2018
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
