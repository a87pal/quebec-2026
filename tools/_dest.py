# -*- coding: utf-8 -*-
"""Destination resolution shared by every script in tools/.

The scripts here are the engine; everything trip-specific lives under
destinations/<slug>/. Nothing in tools/ may hardcode a slug, a machine path
or a map name.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DESTDIR = os.path.join(ROOT, 'destinations')


def slugs():
    if not os.path.isdir(DESTDIR):
        return []
    return sorted(d for d in os.listdir(DESTDIR)
                  if os.path.isdir(os.path.join(DESTDIR, d)) and not d.startswith('.'))


class Dest(object):
    def __init__(self, slug):
        self.slug = slug
        self.dir = os.path.join(DESTDIR, slug)
        self.guide = os.path.join(self.dir, 'guide.html')
        self.images = os.path.join(self.dir, 'images')
        self.tiles = os.path.join(self.images, 'tiles')
        self.mapdir = os.path.join(self.dir, 'maps')

    def _path(self, name):
        return os.path.join(self.mapdir, name)

    def load(self, name, default=None):
        """Read a JSON file from maps/, or return default if absent."""
        p = self._path(name)
        if not os.path.exists(p):
            if default is None:
                sys.exit('error: %s missing for "%s" (expected %s)' % (name, self.slug, p))
            return default
        with open(p, encoding='utf-8') as f:
            return json.load(f)

    def meta(self):
        p = os.path.join(self.dir, 'meta.json')
        if not os.path.exists(p):
            sys.exit('error: meta.json missing for "%s"' % self.slug)
        with open(p, encoding='utf-8') as f:
            return json.load(f)

    def fragment(self, name):
        return self._path('gmap_%s.html' % name)

    def __repr__(self):
        return '<Dest %s>' % self.slug


def add_arg(ap):
    ap.add_argument('--dest', metavar='SLUG',
                    help='destination folder under destinations/ '
                         '(optional when there is only one)')
    return ap


def resolve(slug=None):
    """Resolve a slug to a Dest. Falls back to the only destination if unambiguous."""
    have = slugs()
    if not have:
        sys.exit('error: no destinations found under %s' % DESTDIR)
    if slug is None:
        if len(have) == 1:
            return Dest(have[0])
        sys.exit('error: --dest is required; available: %s' % ', '.join(have))
    if slug not in have:
        sys.exit('error: unknown destination "%s"; available: %s' % (slug, ', '.join(have)))
    return Dest(slug)


def from_args(description, extra=None):
    """Standard entry point: parse --dest (plus any extra args) and resolve it."""
    ap = argparse.ArgumentParser(description=description)
    add_arg(ap)
    if extra:
        extra(ap)
    args = ap.parse_args()
    return resolve(args.dest), args
