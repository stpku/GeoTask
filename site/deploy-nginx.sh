#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:-site}"
TARGET="${2:-/var/www/geotask-experience}"
CASE_LIST="$SOURCE/cases.txt"
EXTERNAL_BASE="https://skyswind.tailf4fad8.ts.net/geotask"

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "Missing $label: $path" >&2
    exit 1
  fi
}

require_file "$SOURCE/index.html" "GeoTask project portal"
require_file "$SOURCE/robots.txt" "robots.txt"
require_file "$SOURCE/sitemap.xml" "sitemap.xml"
require_file "$SOURCE/cases.json" "generated case navigation index"
require_file "$CASE_LIST" "generated case slug list"

mapfile -t CASE_SLUGS < <(grep -E '^gt[0-9]{2}$' "$CASE_LIST")
if [[ ${#CASE_SLUGS[@]} -eq 0 ]]; then
  echo "No case slugs found in $CASE_LIST" >&2
  exit 1
fi

for slug in "${CASE_SLUGS[@]}"; do
  require_file "$SOURCE/$slug/index.html" "${slug^^} page"
done

sudo install -d -m 0755 "$TARGET"
sudo rsync -a --delete "$SOURCE/" "$TARGET/"

require_file "$TARGET/index.html" "deployed GeoTask project portal"
require_file "$TARGET/robots.txt" "deployed robots.txt"
require_file "$TARGET/sitemap.xml" "deployed sitemap.xml"
require_file "$TARGET/cases.json" "deployed case navigation index"
require_file "$TARGET/cases.txt" "deployed case slug list"

for slug in "${CASE_SLUGS[@]}"; do
  require_file "$TARGET/$slug/index.html" "deployed ${slug^^} page"
done

sudo nginx -t
sudo systemctl reload nginx

echo "GeoTask static site deployed:"
echo "  Portal: $TARGET/index.html"
for slug in "${CASE_SLUGS[@]}"; do
  echo "  ${slug^^}: $TARGET/$slug/index.html"
done

echo
echo "Verify externally:"
echo "  $EXTERNAL_BASE/"
for slug in "${CASE_SLUGS[@]}"; do
  echo "  $EXTERNAL_BASE/$slug/"
done
