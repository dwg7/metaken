# Run recipes with src/ on PYTHONPATH so `metaken` is importable without a package install
export PYTHONPATH := justfile_directory() + "/src"

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
    python3 -m metaken.fetch

# Download a specific fiscal year and region
download-one year region:
    python3 -m metaken.fetch --year {{year}} --region {{region}}

# Extract downloaded ZIP files
extract:
    python3 -m metaken.extract

# Parse XML files into normalized records
parse:
    python3 -m metaken.parse

# Validate normalized metadata
validate:
    python3 -m metaken.validate

# Generate reports
report:
    python3 -m metaken.report

# Full workflow
all: clean download extract parse validate report
