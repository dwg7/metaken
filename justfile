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
