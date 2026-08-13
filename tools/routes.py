#!/usr/bin/env python3
"""Fetch real road geometry and driving times for each declared leg.

The route lines on these maps used to be eight to thirteen lat/lon vertices
typed by hand into markers.py - the same practice CLAUDE.md forbids for
markers, for the same reason. They were straight lines between towns pretending
to be roads, and they carried no distance and no driving time, so the leg table
TRAVEL-PREFERENCES.md section 8 asks for had to be written by hand and could
drift from the map beside it.

Legs are declared in maps/legs.json by place name, not coordinate:

  {"ct-nh": {"map": "route", "cls": "rt", "via": ["Cheshire, CT", "Lincoln, NH"]}}

Each name is a places.json key, so a leg follows a pin when it is corrected in
Google My Maps. A literal "45.508,-73.567" also works for a via point that is
not a marker.

Output is maps/routes.json: full-resolution geometry plus distance and duration.
It is COMMITTED, like the tiles and places.json, so check.sh and CI never touch
the network. Geometry is stored unsimplified; overlay.py thins it per map, which
is how one fetch serves the z8 overview and a z13 detail map.

  python3 tools/routes.py                 report what is declared and what is stale
  python3 tools/routes.py --fetch         fetch missing legs
  python3 tools/routes.py --fetch --force refetch everything

Two providers, both OpenStreetMap-derived:

  osrm  (default)  keyless, nothing to sign up for. Some corporate and school
                   networks block router.project-osrm.org at the DNS layer.
  ors              OpenRouteService. Needs a free key, no card, 2000 requests a
                   day. Use it when osrm is unreachable.

The key is looked for in three places, first hit wins:

  1. --key on the command line
  2. $ORS_API_KEY
  3. the macOS keychain, service name ORS_API_KEY

The keychain is the one worth using, because it keeps the key out of your shell
history and out of this repo - which is published to GitHub Pages:

    security add-generic-password -U -a "$USER" -s ORS_API_KEY -w
    python3 tools/routes.py --provider ors --fetch

-w with no value prompts for the key without echoing it. The keychain lookup is
skipped anywhere that is not macOS, so this stays portable; CI never needs a key
at all, because routes.json is committed.

Google's Directions and Routes APIs are deliberately not an option here, and
not because of the key. Maps Platform Service Specific Terms section 4.2 and
19.2: "Customer must not use Google Maps Content from the Directions API in
conjunction with a non-Google map" - these maps are Esri tiles. Sections 4.3 and
19.3 cap caching of returned coordinates at 30 days, and this file's whole
purpose is to commit route geometry permanently so CI never re-fetches it. Both
clauses hit the design head on. OSM-derived routing under ODbL has neither
problem: cache it forever, draw it over any basemap, just attribute it.

Not every line is routable by car. The Franconia ridge is a hiking trail and the
city walks are pedestrian; they stay hand-drawn and labelled schematic, which is
what section 8 asks for. (ORS does offer foot-walking and foot-hiking profiles,
so those lines could become real geometry later - set "profile" on the leg.)

Usage:  python3 tools/routes.py [--dest SLUG] [--fetch] [--provider osrm|ors]
"""
import argparse, io, json, os, subprocess, sys, time

import _dest, _http
from _proj import metres

UA = "travel-guide-toolchain/1.0 (personal itinerary; contact via github.com/a87pal)"

SERVER = "https://router.project-osrm.org"
ORS_SERVER = "https://api.openrouteservice.org"

# Profile names differ per provider; legs.json speaks in plain words.
PROFILES = {
    'osrm': {'driving': 'driving', 'walking': 'foot', 'cycling': 'bike'},
    'ors': {'driving': 'driving-car', 'walking': 'foot-walking',
            'hiking': 'foot-hiking', 'cycling': 'cycling-regular'},
}


def fetch_osrm(http, server, profile, pts, key):
    """OSRM: coordinates in the URL, geometry as an encoded polyline."""
    # OSRM wants lon,lat - the opposite order to everything else in this repo.
    coords = ';'.join('%.6f,%.6f' % (lon, lat) for lat, lon in pts)
    url = ('%s/route/v1/%s/%s?overview=full&geometries=polyline6&annotations=false'
           % (server, profile, coords))
    r = http.get_json(url)
    if r.get('code') != 'Ok' or not r.get('routes'):
        raise RuntimeError('%s %s' % (r.get('code', '?'), r.get('message', '')[:60]))
    route = r['routes'][0]
    return decode(route['geometry'], 6), route['distance'], route['duration']


def fetch_ors(http, server, profile, pts, key):
    """OpenRouteService: POST the waypoints, get GeoJSON back.

    Asking for GeoJSON rather than the default encoded polyline means no
    decoding step and no chance of a precision mismatch.
    """
    url = '%s/v2/directions/%s/geojson' % (server, profile)
    # ORS also wants lon,lat.
    body = {'coordinates': [[round(lon, 6), round(lat, 6)] for lat, lon in pts]}
    r = http.post_json(url, body, {'Authorization': key})
    feats = r.get('features') or []
    if not feats:
        raise RuntimeError(str(r.get('error', r))[:80])
    f = feats[0]
    summary = f['properties'].get('summary', {})
    if not summary:
        raise RuntimeError('no summary in response (unroutable waypoints?)')
    # GeoJSON is lon,lat[,elevation]; store lat,lon like everything else here.
    geom = [(c[1], c[0]) for c in f['geometry']['coordinates']]
    return geom, summary['distance'], summary['duration']


FETCHERS = {'osrm': fetch_osrm, 'ors': fetch_ors}
SERVERS = {'osrm': SERVER, 'ors': ORS_SERVER}

# Providers that need a key, and the one name that identifies it everywhere:
# the environment variable, the macOS keychain item, and the documentation.
KEY_ENV = {'ors': 'ORS_API_KEY'}


def keychain(name):
    """Read a generic password from the macOS keychain, or None.

    Keyed on the service name only, so it does not matter which account added
    it. Silent on every failure - not a Mac, no such item, user cancelled the
    access prompt - because this is the last resort in a chain of three and the
    caller prints a single actionable message if all of them come up empty.
    """
    if sys.platform != 'darwin':
        return None
    try:
        out = subprocess.check_output(
            ['security', 'find-generic-password', '-s', name, '-w'],
            stderr=subprocess.DEVNULL, text=True, timeout=30)
    except Exception:
        return None
    return out.strip() or None


def api_key(provider, explicit):
    """Resolve a provider's key. Returns (key, where_it_came_from)."""
    name = KEY_ENV.get(provider)
    if not name:
        return None, None
    if explicit:
        return explicit, '--key'
    if os.environ.get(name):
        return os.environ[name], '$' + name
    got = keychain(name)
    if got:
        return got, 'macOS keychain (%s)' % name
    return None, None


def key_help(provider):
    name = KEY_ENV.get(provider, 'API_KEY')
    return ('error: --provider %s needs a key. Get a free one (no card) at\n'
            '  https://account.heigit.org/signup\n\n'
            'Then store it in the macOS keychain, which keeps it out of your\n'
            'shell history and out of this repo:\n\n'
            '  security add-generic-password -U -a "$USER" -s %s -w\n\n'
            '(-w with no value prompts for it, hidden, and confirms it twice.)\n'
            'Or set $%s for one command, or pass --key.'
            % (provider, name, name))


def decode(s, precision=6):
    """Decode an encoded polyline into [(lat, lon)].

    OSRM is asked for polyline6, so the scale is 1e6 rather than the 1e5 that
    Google's original format and most copies of this function assume. Decoding
    polyline6 as polyline5 yields a route ten times too large, somewhere off the
    coast of Africa.
    """
    scale = float(10 ** precision)
    pts, lat, lon, i = [], 0, 0, 0
    while i < len(s):
        for is_lon in (False, True):
            shift = result = 0
            while True:
                if i >= len(s):
                    raise ValueError("truncated polyline at %d" % i)
                b = ord(s[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if result & 1 else (result >> 1)
            if is_lon:
                lon += d
            else:
                lat += d
        pts.append((lat / scale, lon / scale))
    return pts


def waypoint(name, places):
    """Resolve a via entry to (lat, lon): a places.json key or a literal."""
    if name in places:
        p = places[name]
        return p['lat'], p['lon']
    if ',' in name:
        try:
            lat, lon = (float(x) for x in name.split(',', 1))
            return lat, lon
        except ValueError:
            pass
    sys.exit('error: leg via point "%s" is not a places.json key or a "lat,lon" literal' % name)


def fetch(dest, do_fetch, force, server, provider, key):
    legs = dest.load('legs.json', default={})
    if not legs:
        sys.exit('no maps/legs.json for "%s" - nothing to route.\n'
                 'Declare legs as {"id": {"map": ..., "cls": ..., "via": [...]}}' % dest.slug)
    places = dest.load('places.json', default={})
    out = dest.load('routes.json', default={})
    path = os.path.join(dest.mapdir, 'routes.json')
    http = _http.Http(os.path.join(dest.mapdir, '.routes-cache.json'), UA, pause=1.0)
    today = time.strftime('%Y-%m-%d')

    todo, ok, failed = [], [], []
    for rid in sorted(k for k in legs if not k.startswith('_')):   # _comment etc.
        leg = legs[rid]
        pts = [waypoint(v, places) for v in leg['via']]
        if len(pts) < 2:
            sys.exit('error: leg "%s" needs at least two via points' % rid)
        have = out.get(rid)
        # A leg is stale when its endpoints have moved since it was fetched -
        # which is exactly what happens after a Google My Maps correction.
        stale = False
        if have:
            drift = max(metres(a, b) for a, b in zip(pts, have.get('via_at', pts)))
            stale = drift > 50 or len(have.get('via_at', [])) != len(pts)
            have['drift_m'] = drift
        if have and not stale and not force:
            ok.append(rid)
            continue
        todo.append((rid, leg, pts, bool(have)))

    print('%d legs declared, %d current, %d to fetch' % (len(ok) + len(todo), len(ok), len(todo)))
    for rid in ok:
        r = out[rid]
        print('  ok      %-16s %6.1f km  %4.1f h  fetched %s'
              % (rid, r['distance_m'] / 1000.0, r['duration_s'] / 3600.0, r.get('fetched', '?')))
    for rid, leg, pts, had in todo:
        print('  %-7s %-16s %s' % ('stale' if had else 'missing', rid, ' -> '.join(leg['via'])))

    if not todo:
        print('\nroutes.json is current.')
        return 0
    if not do_fetch:
        print('\n(pass --fetch to hit the router; nothing else here touches the network)')
        return 0

    key, source = api_key(provider, key)
    if provider in KEY_ENV and not key:
        sys.exit('\n' + key_help(provider))

    fetcher = FETCHERS[provider]
    profiles = PROFILES[provider]
    print('\nfetching from %s (%s)%s'
          % (provider, server, '  key from %s' % source if source else ''))
    for rid, leg, pts, _ in todo:
        want = leg.get('profile', 'driving')
        profile = profiles.get(want)
        if profile is None:
            failed.append((rid, 'profile "%s" not available on %s' % (want, provider)))
            print('  FAIL %-16s profile "%s" not offered by %s (has: %s)'
                  % (rid, want, provider, ', '.join(sorted(profiles))))
            continue
        try:
            geom, dist, dur = fetcher(http, server, profile, pts, key)
        except Exception as e:
            failed.append((rid, str(e)[:70]))
            print('  FAIL %-16s %s' % (rid, str(e)[:70]))
            continue
        out[rid] = {'geometry': [[round(a, 6), round(b, 6)] for a, b in geom],
                    'distance_m': round(dist),
                    'duration_s': round(dur),
                    'via': leg['via'],
                    'via_at': [[round(a, 6), round(b, 6)] for a, b in pts],
                    'profile': want,
                    'source': provider,
                    'fetched': today}
        print('  got  %-16s %6.1f km  %4.1f h  %4d points'
              % (rid, dist / 1000.0, dur / 3600.0, len(geom)))
    http.save()

    if not out:
        # Every leg failed. Writing an empty routes.json would look like a
        # successful run that found nothing, so leave the file absent instead:
        # overlay.py falls back to the schematic geometry in markers.py.
        print('\nnothing fetched, routes.json not written.')
        return 1

    for r in out.values():
        r.pop('drift_m', None)
    json.dump(out, io.open(path, 'w'), indent=1, ensure_ascii=False, sort_keys=True)
    print('\nwrote %d legs -> %s' % (len(out), path))
    if failed:
        print('%d leg(s) failed. A leg OSRM cannot route can be pinned by hand in\n'
              'routes.json with "source": "manual: <why>" - routes.py leaves those alone.'
              % len(failed))
    return 1 if failed else 0


def selftest():
    """The polyline decoder is the one piece here that can be wrong silently."""
    # Reference vector from the Google polyline spec, at its native 1e5.
    got = decode('_p~iF~ps|U_ulLnnqC_mqNvxq`@', 5)
    want = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    assert len(got) == len(want), got
    for (a, b), (c, d) in zip(got, want):
        assert abs(a - c) < 1e-6 and abs(b - d) < 1e-6, (got, want)
    # Same path at polyline6 must round-trip to the same coordinates, and
    # decoding it at the wrong precision must not quietly look plausible.
    wrong = decode('_p~iF~ps|U_ulLnnqC_mqNvxq`@', 6)
    assert abs(wrong[0][0] - 3.85) < 1e-6, wrong[0]
    print('polyline decoder ok (%d points, precision guard ok)' % len(got))
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Fetch road geometry and driving times for declared legs.')
    _dest.add_arg(ap)
    ap.add_argument('--fetch', action='store_true', help='hit the router for missing or stale legs')
    ap.add_argument('--force', action='store_true', help='refetch every leg, not just stale ones')
    ap.add_argument('--provider', default='osrm', choices=sorted(FETCHERS),
                    help='osrm (keyless) or ors (needs ORS_API_KEY)')
    ap.add_argument('--server', default=None, help='override the provider base URL')
    ap.add_argument('--key', default=None,
                    help='API key; otherwise $ORS_API_KEY, otherwise the macOS keychain')
    ap.add_argument('--selftest', action='store_true', help='check the polyline decoder, no network')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    server = (a.server or SERVERS[a.provider]).rstrip('/')
    sys.exit(fetch(_dest.resolve(a.dest), a.fetch, a.force, server, a.provider, a.key))
