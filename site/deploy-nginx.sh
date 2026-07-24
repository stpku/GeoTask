#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:-site}"
TARGET="${2:-/var/www/geotask-experience}"

if [[ ! -f "$SOURCE/index.html" ]]; then
  echo "Missing GT01 page: $SOURCE/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt02/index.html" ]]; then
  echo "Missing GT02 page: $SOURCE/gt02/index.html" >&2
  exit 1
fi

sudo install -d -m 0755 "$TARGET"
sudo rsync -a --delete "$SOURCE/" "$TARGET/"

test -f "$TARGET/index.html"
test -f "$TARGET/gt02/index.html"

sudo nginx -t
sudo systemctl reload nginx

echo "GeoTask static site deployed:"
echo "  GT01: $TARGET/index.html"
echo "  GT02: $TARGET/gt02/index.html"
echo
echo "Verify externally:"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt02/"
