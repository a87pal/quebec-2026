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
  # overlay.py places every label automatically and is fatal on a marker with no
  # places.json entry, or one whose coordinate falls outside the map it is drawn
  # on. boxes.py then re-checks the placement it produced.
  python3 tools/overlay.py  --dest "$slug"   # fragments from committed inputs
  python3 tools/boxes.py    --dest "$slug"   # must be 0 overlaps, 0 dot-covers
  # The day/category layer, and the per-day Google Maps links built from it.
  # Offline. inventory.py is fatal on a key that is not a real place, a day the
  # guide does not have, or a route stop not tagged to the day it is routed on.
  if [ -f "$d/maps/inventory.json" ]; then
    python3 tools/inventory.py --dest "$slug" --brief
    python3 tools/dayroutes.py --dest "$slug"
  fi
  # Also regenerated from committed inputs (places.json), for the same reason:
  # it catches a guide whose checklist is stale with respect to the places.
  if grep -q 'id="savedlist"' "$d/guide.html" 2>/dev/null; then
    python3 tools/savedlist.py --dest "$slug"
  fi
  python3 tools/maps.py     --dest "$slug"   # splice them into the guide
  python3 tools/validate.py --dest "$slug"   # structure + prose preservation
  # Advisory, and offline: reports legs whose endpoints have moved since their
  # geometry was fetched. Refetching needs the network, so it is not a gate.
  if [ -f "$d/maps/legs.json" ]; then
    python3 tools/routes.py --dest "$slug" | head -1
  fi
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
