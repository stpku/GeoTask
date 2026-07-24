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

if [[ ! -f "$SOURCE/gt03/index.html" ]]; then
  echo "Missing GT03 page: $SOURCE/gt03/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt04/index.html" ]]; then
  echo "Missing GT04 page: $SOURCE/gt04/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt05/index.html" ]]; then
  echo "Missing GT05 page: $SOURCE/gt05/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt06/index.html" ]]; then
  echo "Missing GT06 page: $SOURCE/gt06/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt07/index.html" ]]; then
  echo "Missing GT07 page: $SOURCE/gt07/index.html" >&2
  exit 1
fi

sudo install -d -m 0755 "$TARGET"
sudo rsync -a --delete "$SOURCE/" "$TARGET/"

test -f "$TARGET/index.html"
test -f "$TARGET/gt02/index.html"
test -f "$TARGET/gt03/index.html"
test -f "$TARGET/gt04/index.html"
test -f "$TARGET/gt05/index.html"
test -f "$TARGET/gt06/index.html"
test -f "$TARGET/gt07/index.html"

sudo nginx -t
sudo systemctl reload nginx

echo "GeoTask static site deployed:"
echo "  GT01: $TARGET/index.html"
echo "  GT02: $TARGET/gt02/index.html"
echo "  GT03: $TARGET/gt03/index.html"
echo "  GT04: $TARGET/gt04/index.html"
echo "  GT05: $TARGET/gt05/index.html"
echo "  GT06: $TARGET/gt06/index.html"
echo "  GT07: $TARGET/gt07/index.html"
echo
echo "Verify externally:"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt02/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt03/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt04/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt05/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt06/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt07/"
