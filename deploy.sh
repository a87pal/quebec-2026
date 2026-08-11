#!/usr/bin/env bash
# Rebuild site/index.html from quebec-v3.html (re-injecting the hosted-only
# <head> tags) and publish to https://a87pal.github.io/quebec-2026/
#
#   ./deploy.sh                 -> commit message "update guide"
#   ./deploy.sh "fixed the map" -> custom commit message
set -euo pipefail
cd "$(dirname "$0")"

SRC=quebec-v3.html
MSG="${1:-update guide}"

[ -f "$SRC" ] || { echo "error: $SRC not found"; exit 1; }

# 1. copy the images the page actually references (adds new ones, keeps old)
rsync -a --delete images/ site/images/

# 1b. keep the map/validation toolchain in the repo so it survives this machine.
#     Generated fragments and the lookup cache are build artifacts - excluded.
rsync -a --delete \
  --exclude 'gmap_*.html' --exclude '.resolve-cache.json' --exclude '__pycache__' \
  tools/ site/tools/

# 2. rebuild index.html with the hosted-only head tags injected
python3 - "$SRC" <<'PY'
import sys, re
src = sys.argv[1]
s = open(src, encoding='utf-8').read()

HEAD = ('<meta name="theme-color" content="#1d5540"/>\n'
 '<meta name="robots" content="noindex, nofollow"/>\n'
 '<meta property="og:title" content="Je me souviens — Québec &amp; Montréal, Aug 26 – Sep 6 2026"/>\n'
 '<meta property="og:description" content="Twelve days following the St. Lawrence from the mountains to the sea."/>\n'
 '<meta name="apple-mobile-web-app-title" content="Québec 2026"/>\n'
 '<link rel="icon" href="data:image/svg+xml,'
 '%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E'
 '%3Ctext y=%22.9em%22 font-size=%2290%22%3E%F0%9F%90%8B%3C/text%3E%3C/svg%3E"/>\n')

anchor = '<meta content="width=device-width,initial-scale=1" name="viewport"/>'
if anchor not in s:
    sys.exit("error: viewport meta tag not found - did the <head> change?")
s = s.replace(anchor, anchor + '\n' + HEAD, 1)

# sanity checks before we publish
problems = []
for tag in ('div', 'details', 'summary', 'section', 'article', 'p'):
    o = len(re.findall(r'<%s[\s>]' % tag, s))
    c = len(re.findall(r'</%s>' % tag, s))
    if o != c:
        problems.append('%s %d/%d' % (tag, o, c))
if problems:
    sys.exit('error: unbalanced tags -> ' + ', '.join(problems))

import os
missing = [r for r in set(re.findall(r'src="(images/[^"]+)"', s))
           if not os.path.exists(os.path.join('site', r))]
if missing:
    sys.exit('error: %d referenced assets missing, e.g. %s' % (len(missing), missing[:3]))

open('site/index.html', 'w', encoding='utf-8').write(s)
print('  index.html rebuilt (%d KB), all assets present' % (len(s) // 1024))
PY

# 3. publish
cd site
# --porcelain, not `git diff`: diff only sees tracked files, so a brand-new
# directory (e.g. the first time tools/ was synced) reads as "nothing changed".
if [ -z "$(git status --porcelain)" ]; then
  echo "  nothing changed - not publishing"
  exit 0
fi
git add -A
git commit -qm "$MSG"
git push -q
echo "  pushed. live in ~1 min: https://a87pal.github.io/quebec-2026/"
