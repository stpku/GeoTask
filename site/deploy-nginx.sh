#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:-site}"
TARGET="${2:-/var/www/geotask-experience}"

if [[ ! -f "$SOURCE/index.html" ]]; then
  echo "Missing GeoTask project portal: $SOURCE/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt01/index.html" ]]; then
  echo "Missing GT01 page: $SOURCE/gt01/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/robots.txt" || ! -f "$SOURCE/sitemap.xml" ]]; then
  echo "Missing robots.txt or sitemap.xml in $SOURCE" >&2
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

if [[ ! -f "$SOURCE/gt08/index.html" ]]; then
  echo "Missing GT08 page: $SOURCE/gt08/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt09/index.html" ]]; then
  echo "Missing GT09 page: $SOURCE/gt09/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt10/index.html" ]]; then
  echo "Missing GT10 page: $SOURCE/gt10/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt11/index.html" ]]; then
  echo "Missing GT11 page: $SOURCE/gt11/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt12/index.html" ]]; then
  echo "Missing GT12 page: $SOURCE/gt12/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt13/index.html" ]]; then
  echo "Missing GT13 page: $SOURCE/gt13/index.html" >&2
  exit 1
fi

if [[ ! -f "$SOURCE/gt14/index.html" ]]; then
  echo "Missing GT14 page: $SOURCE/gt14/index.html" >&2
  exit 1
fi

sudo install -d -m 0755 "$TARGET"
sudo rsync -a --delete "$SOURCE/" "$TARGET/"

test -f "$TARGET/index.html"
test -f "$TARGET/gt01/index.html"
test -f "$TARGET/robots.txt"
test -f "$TARGET/sitemap.xml"
test -f "$TARGET/gt02/index.html"
test -f "$TARGET/gt03/index.html"
test -f "$TARGET/gt04/index.html"
test -f "$TARGET/gt05/index.html"
test -f "$TARGET/gt06/index.html"
test -f "$TARGET/gt07/index.html"
test -f "$TARGET/gt08/index.html"
test -f "$TARGET/gt09/index.html"
test -f "$TARGET/gt10/index.html"
test -f "$TARGET/gt11/index.html"
test -f "$TARGET/gt12/index.html"
test -f "$TARGET/gt13/index.html"
test -f "$TARGET/gt14/index.html"

sudo nginx -t
sudo systemctl reload nginx

echo "GeoTask static site deployed:"
echo "  Portal: $TARGET/index.html"
echo "  GT01: $TARGET/gt01/index.html"
echo "  GT02: $TARGET/gt02/index.html"
echo "  GT03: $TARGET/gt03/index.html"
echo "  GT04: $TARGET/gt04/index.html"
echo "  GT05: $TARGET/gt05/index.html"
echo "  GT06: $TARGET/gt06/index.html"
echo "  GT07: $TARGET/gt07/index.html"
echo "  GT08: $TARGET/gt08/index.html"
echo "  GT09: $TARGET/gt09/index.html"
echo "  GT10: $TARGET/gt10/index.html"
echo "  GT11: $TARGET/gt11/index.html"
echo "  GT12: $TARGET/gt12/index.html"
echo "  GT13: $TARGET/gt13/index.html"
echo "  GT14: $TARGET/gt14/index.html"
echo
echo "Verify externally:"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt01/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt02/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt03/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt04/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt05/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt06/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt07/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt08/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt09/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt10/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt11/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt12/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt13/"
echo "  https://skyswind.tailf4fad8.ts.net/geotask/gt14/"
