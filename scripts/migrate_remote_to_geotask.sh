#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "GeoTask Remote Repository Migration Helper"
echo "============================================"
echo

echo "Current remotes:"
git remote -v
echo

echo "Recommended migration:"
echo "  1) Ensure new repo exists on Gitee: https://gitee.com/stpku/GeoTask"
echo "  2) Keep old remote as stir-origin"
echo "  3) Add new remote as origin or geotask-origin"
echo

read -p "Proceed to rename origin to stir-origin and add geotask-origin? [y/N] " ans
if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
  echo "Cancelled."
  exit 0
fi

# Rename existing origin to preserve it
if git remote get-url origin >/dev/null 2>&1; then
  old_url=$(git remote get-url origin)
  echo "Current origin URL: $old_url"

  # Only rename if it looks like the old STIR repo
  if echo "$old_url" | grep -q "stir"; then
    echo "Renaming origin -> stir-origin..."
    git remote rename origin stir-origin || true
  else
    echo "Current origin does not appear to be the old STIR repo."
    echo "Renaming anyway to preserve it..."
    git remote rename origin stir-origin || true
  fi
else
  echo "No 'origin' remote found."
fi

# Add new GeoTask remote
if git remote get-url geotask-origin >/dev/null 2>&1; then
  echo "geotask-origin already exists. URL:"
  git remote get-url geotask-origin
else
  echo "Adding geotask-origin remote..."
  git remote add geotask-origin https://gitee.com/stpku/GeoTask.git || {
    echo "Failed to add geotask-origin. It may already exist or the URL may be incorrect."
    echo "Check: https://gitee.com/stpku/GeoTask"
  }
fi

echo
echo "Updated remotes:"
git remote -v
echo

echo "============================================"
echo "Next steps (manual):"
echo "============================================"
echo
echo "  Push current branch:"
echo "    git push geotask-origin rename/geotask"
echo
echo "  Or push main directly:"
echo "    git push geotask-origin main"
echo
echo "  To rename geotask-origin to origin later:"
echo "    git remote rename origin old-origin"
echo "    git remote rename geotask-origin origin"
echo
echo "Done. No force push was performed."
