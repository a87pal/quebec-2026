#!/usr/bin/env bash
# Build and serve dist/ locally, so you can look at a change before CI ships it.
#
#   ./preview.sh          -> http://localhost:8000
#   ./preview.sh 8080     -> another port
#
# Serving over HTTP rather than opening the file directly matters: file:// URLs
# resolve relative paths differently and will not show you what Pages shows.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8000}"

python3 build.py
echo
echo "  http://localhost:${PORT}/          landing"
for d in dist/*/; do
  [ -d "$d" ] || continue
  echo "  http://localhost:${PORT}/$(basename "$d")/"
done
echo "  Ctrl-C to stop"
echo
exec python3 -m http.server "$PORT" --directory dist
