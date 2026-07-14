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

# Build survey-extent vector tiles: CSV -> GeoJSON -> tippecanoe -> PMTiles.
# No fill, thin outline only, --drop-smallest-as-needed so tile-size pressure
# drops the smallest-area features first (larger extents surface at lower
# zoom); maxzoom capped at 12 since these are plain rectangles, not detailed
# geometry -- deeper zoom just duplicates the same shape into more tiles for
# no visual gain. See src/metaken/tiles.py for the bbox-plausibility filters.
tiles:
    python3 -m metaken.tiles
    tippecanoe \
        --force \
        --output=data/normalized/survey_extents.mbtiles \
        --layer=survey_extents \
        --name="metaken survey extents" \
        --attribution="国土地理院 公共測量成果等メタデータ (metaken)" \
        --minimum-zoom=0 \
        --maximum-zoom=12 \
        --drop-smallest-as-needed \
        --quiet \
        data/normalized/survey_extents.geojson
    pmtiles convert data/normalized/survey_extents.mbtiles data/normalized/survey_extents.pmtiles
    cp data/normalized/survey_extents.pmtiles viewer/public/survey_extents.pmtiles

# Build the map viewer (Vite, single-file, -> docs/map/). Run `just tiles` first.
map-build:
    cd viewer && npm install && npm run build

# Full workflow (metadata pipeline only; run `just tiles map-build` separately)
all: clean download extract parse validate report
