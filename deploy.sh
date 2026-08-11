#!/usr/bin/env bash
# Escape hatch: verify, build, commit and push. CI publishes once main moves,
# so this is really "check my work and hand it to CI".
#
#   ./deploy.sh                 -> commit message "update guide"
#   ./deploy.sh "fixed the map" -> custom commit message
#
# There is no rsync here any more. Images used to be copied into site/ and the
# toolchain mirrored into site/tools/ purely because site/ was the only git
# repo; the repo root is versioned now, so git handles both, and build.py
# writes the publishable tree to dist/ (which is never committed).
set -euo pipefail
cd "$(dirname "$0")"

MSG="${1:-update guide}"

./check.sh
python3 build.py

# --porcelain, not `git diff`: diff only sees tracked files, so a brand-new
# directory (a whole new destination, say) reads as "nothing changed".
if [ -z "$(git status --porcelain)" ]; then
  echo "  nothing changed - not publishing"
  exit 0
fi

git add -A
git commit -qm "$MSG"
git push -q
echo "  pushed. GitHub Actions will publish in ~1 min."
