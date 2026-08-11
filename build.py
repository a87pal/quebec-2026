#!/usr/bin/env python3
"""Build the whole site into dist/.

For each destination: inject the hosted-only <head> tags, run the gates, and
copy the guide and its images. Then render the landing page from every
destination's meta.json.

Nothing here touches the network, so it is safe to run in CI. Downloading
tiles (tools/tiles.py) and resolving coordinates (tools/resolve.py) hit
rate-limited third parties and stay local; their outputs are committed.

  python3 build.py                 build everything into dist/
  python3 build.py --dest SLUG     build one destination
  python3 build.py --check         run the gates, write nothing

Exits non-zero if any gate fails, so CI can gate a merge on it.
"""
import argparse, html, json, os, re, shutil, sys, urllib.parse
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import _dest
import validate

ROOT = _dest.ROOT
DIST = os.path.join(ROOT, 'dist')
TEMPLATE = os.path.join(ROOT, 'shared', 'landing.template.html')

# Matches the viewport meta whatever order its attributes are in. The old
# deploy.sh matched one exact byte string, so reordering a single attribute
# aborted the deploy.
VIEWPORT = re.compile(r'<meta\b[^>]*\bname=["\']viewport["\'][^>]*>', re.I)
ASSET = re.compile(r'src="(images/[^"]+)"')


def favicon_uri(emoji):
    """Emoji -> an inline SVG data: URI. No file, no request."""
    return ('data:image/svg+xml,'
            '%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E'
            '%3Ctext y=%22.9em%22 font-size=%2290%22%3E' + urllib.parse.quote(emoji) +
            '%3C/text%3E%3C/svg%3E')


def head_tags(meta):
    """The tags that only make sense on the hosted copy, built from meta.json."""
    e = lambda s: html.escape(s, quote=True)
    og_title = '%s — %s, %s' % (meta['tagline'], meta['title'], meta['dates'])
    return ('<meta name="theme-color" content="%s"/>\n'
            '<meta name="robots" content="noindex, nofollow"/>\n'
            '<meta property="og:title" content="%s"/>\n'
            '<meta property="og:description" content="%s"/>\n'
            '<meta name="apple-mobile-web-app-title" content="%s"/>\n'
            '<link rel="icon" href="%s"/>\n'
            % (e(meta.get('themeColor', '#1d5540')), e(og_title), e(meta['blurb']),
               e(meta.get('appleTitle', meta['title'])), favicon_uri(meta.get('favicon', '🌍'))))


def build_one(dest, write=True):
    """Returns (meta, problems). Problems non-empty means a gate failed."""
    meta = dest.meta()
    problems = []
    if not os.path.exists(dest.guide):
        return meta, ['%s missing' % dest.guide]
    s = open(dest.guide, encoding='utf-8').read()

    # --- head injection ----------------------------------------------------
    m = VIEWPORT.search(s)
    if not m:
        return meta, ['no <meta name="viewport"> in %s - cannot inject head tags' % dest.guide]
    s = s[:m.end()] + '\n' + head_tags(meta) + s[m.end():]

    # --- Gate A: structure (shared with tools/validate.py) ------------------
    problems += validate.structural_problems(s)

    # --- Gate B: every referenced asset exists -----------------------------
    refs = set(ASSET.findall(s))
    missing = sorted(r for r in refs if not os.path.exists(os.path.join(dest.dir, r)))
    for r in missing[:5]:
        problems.append('missing asset %s' % r)
    if len(missing) > 5:
        problems.append('...and %d more missing assets' % (len(missing) - 5))

    # --- Gate C: orphans on disk (advisory) --------------------------------
    orphans = []
    if os.path.isdir(dest.images):
        for dirpath, _, files in os.walk(dest.images):
            for f in files:
                if f.startswith('.'):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), dest.dir).replace(os.sep, '/')
                if rel not in refs:
                    orphans.append(rel)

    hero = meta.get('hero')
    if hero and not os.path.exists(os.path.join(dest.dir, hero)):
        problems.append('hero image %s not found' % hero)

    if problems or not write:
        return meta, problems

    # --- emit --------------------------------------------------------------
    out = os.path.join(DIST, dest.slug)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(s)
    if os.path.isdir(dest.images):
        shutil.copytree(dest.images, os.path.join(out, 'images'), dirs_exist_ok=True)

    print('  %-18s %d KB · %d assets · %d orphan%s'
          % (dest.slug, len(s.encode('utf-8')) // 1024, len(refs),
             len(orphans), '' if len(orphans) == 1 else 's'))
    for o in sorted(orphans):
        print('       orphan (on disk, never referenced): %s' % o)
    return meta, []


def card(slug, meta):
    e = lambda s: html.escape(str(s), quote=True)
    hero = '%s/%s' % (slug, meta['hero']) if meta.get('hero') else ''
    img = ('<div class="dthumb"><img src="%s" alt="" loading="lazy"/></div>' % e(hero)) if hero else ''
    return ('<a class="dcard" href="%s/">%s<div class="dbody">'
            '<div class="dkick">%s</div><h3>%s</h3>'
            '<p class="dtag">%s</p><p class="dblurb">%s</p>'
            '<span class="dgo">Open the guide →</span></div></a>'
            % (e(slug), img, e(meta['dates']), e(meta['title']),
               e(meta.get('tagline', '')), e(meta['blurb'])))


def build_landing(built):
    if not os.path.exists(TEMPLATE):
        sys.exit('error: %s missing' % TEMPLATE)
    tpl = open(TEMPLATE, encoding='utf-8').read()
    today = date.today().isoformat()

    listed = [(s, m) for s, m in built if m.get('listed', True)]
    upcoming = sorted([x for x in listed if x[1].get('end', '9999') >= today],
                      key=lambda x: x[1].get('start', ''))
    past = sorted([x for x in listed if x[1].get('end', '9999') < today],
                  key=lambda x: x[1].get('start', ''), reverse=True)

    chunks = []
    if upcoming:
        chunks.append('<h2>Ahead</h2>\n<div class="dgrid">%s</div>'
                      % ''.join(card(s, m) for s, m in upcoming))
    if past:
        chunks.append('<h2>Been</h2>\n<div class="dgrid">%s</div>'
                      % ''.join(card(s, m) for s, m in past))
    if not chunks:
        chunks.append('<p class="empty">No guides yet.</p>')

    page = tpl.replace('{{CARDS}}', '\n'.join(chunks)).replace('{{COUNT}}', str(len(listed)))
    with open(os.path.join(DIST, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)

    # every card must point at something we actually built
    for s, _ in listed:
        if not os.path.isdir(os.path.join(DIST, s)):
            sys.exit('error: landing links to %s/ but it was not built' % s)
    hidden = len(built) - len(listed)
    print('  landing            %d guide%s%s'
          % (len(listed), '' if len(listed) == 1 else 's',
             ' (%d unlisted)' % hidden if hidden else ''))


def main():
    ap = argparse.ArgumentParser(description='Build the travel guide site into dist/.')
    _dest.add_arg(ap)
    ap.add_argument('--check', action='store_true', help='run the gates, write nothing')
    args = ap.parse_args()

    targets = [_dest.Dest(args.dest)] if args.dest else [_dest.Dest(s) for s in _dest.slugs()]
    if not targets:
        sys.exit('error: no destinations found')

    write = not args.check
    if write:
        shutil.rmtree(DIST, ignore_errors=True)
        os.makedirs(DIST, exist_ok=True)

    print('%s %d destination%s' % ('checking' if args.check else 'building',
                                   len(targets), '' if len(targets) == 1 else 's'))
    built, failed = [], []
    for d in targets:
        meta, problems = build_one(d, write=write)
        if problems:
            failed.append((d.slug, problems))
        else:
            built.append((d.slug, meta))

    if failed:
        print('\nFAILED:')
        for slug, problems in failed:
            for p in problems:
                print('  %-18s %s' % (slug, p))
        sys.exit(1)

    if args.check:
        print('all gates pass')
        return

    # A landing page listing only some destinations would quietly hide the rest.
    if args.dest:
        print('  (single destination - landing page not rebuilt)')
    else:
        build_landing(built)
        open(os.path.join(DIST, '.nojekyll'), 'w').close()
    print('-> %s' % DIST)


if __name__ == '__main__':
    main()
