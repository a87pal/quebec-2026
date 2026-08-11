#!/usr/bin/env bash
# Everything CI checks, runnable locally. Touches no network.
#
#   ./check.sh
#
# The map pipeline is re-run from its committed inputs (maps.json, markers.py,
# places.json, tilemeta.json). That does two jobs at once: it proves the
# fragments still regenerate, and it catches a guide.html whose maps are stale
# because someone edited markers.py without re-running maps.py.
set -euo pipefail
cd "$(dirname "$0")"

for d in destinations/*/; do
  slug=$(basename "$d")
  [ -f "$d/maps/maps.json" ] || continue
  echo "== $slug"
  python3 tools/overlay.py  --dest "$slug"   # fragments from committed inputs
  python3 tools/boxes.py    --dest "$slug"   # must be 0 overlaps, 0 dot-covers
  python3 tools/maps.py     --dest "$slug"   # splice them into the guide
  python3 tools/validate.py --dest "$slug"   # structure + prose preservation
  echo
done

# If splicing changed a guide, the committed guide had stale maps in it.
if ! git diff --quiet -- 'destinations/*/guide.html'; then
  echo "ERROR: a guide is out of date with its markers.py / places.json." >&2
  git diff --stat -- 'destinations/*/guide.html' >&2
  echo "Fix: python3 tools/overlay.py --dest SLUG && python3 tools/maps.py --dest SLUG, then commit." >&2
  exit 1
fi

python3 build.py --check
echo
echo "all checks pass"
