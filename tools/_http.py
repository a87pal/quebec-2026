# -*- coding: utf-8 -*-
"""Cached HTTP GET with backoff, for the tools that talk to free public APIs.

Nominatim, Wikidata and OSRM all return 429 under scripted load, and a plain
request loop loses roughly half its lookups. Every caller wants the same three
things: sleep before asking, back off hard on 429/5xx, and never ask twice for
the same URL across runs.

The on-disk cache never expires. That is deliberate: these lookups are slow and
rate-limited, and the answers are coordinates and road geometry that do not
move. Delete the cache file to force a refetch.

Scripts using this touch the network and stay local; their output is committed
so CI never needs to re-fetch. See tools/README.md.
"""
import hashlib, io, json, os, time, urllib.error, urllib.request


class Http(object):
    """A cached, backing-off JSON client bound to one cache file."""

    def __init__(self, cache_path, ua, pause=1.3, tries=6, timeout=30):
        self.path = cache_path
        self.headers = {"User-Agent": ua}
        self.pause = pause
        self.tries = tries
        self.timeout = timeout
        self.hits = self.fetches = 0
        self.cache = json.load(io.open(cache_path)) if os.path.exists(cache_path) else {}

    def save(self):
        json.dump(self.cache, io.open(self.path, "w"))

    def get_json(self, url):
        return self._fetch(url, None, None)

    def post_json(self, url, payload, headers=None):
        """POST a JSON body. Cache key folds in the body, so two different
        requests to the same endpoint do not collide."""
        body = json.dumps(payload, sort_keys=True).encode('utf-8')
        key = '%s#%s' % (url, hashlib.sha256(body).hexdigest()[:16])
        return self._fetch(url, body, headers, key)

    def _fetch(self, url, body, extra, key=None):
        key = key or url
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        delay = self.pause
        headers = dict(self.headers)
        if extra:
            headers.update(extra)
        if body is not None:
            headers.setdefault('Content-Type', 'application/json')
        for _ in range(self.tries):
            time.sleep(delay)                       # before, not after: be polite first
            try:
                req = urllib.request.Request(url, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.load(r)
                self.cache[key] = out
                self.fetches += 1
                if self.fetches % 10 == 0:
                    self.save()
                return out
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    delay = min(delay * 2.2, 45)    # 1.3, 2.9, 6.3, 14, 31, 45
                    continue
                # An auth or quota failure is worth reading, not just counting.
                detail = ''
                try:
                    detail = e.read().decode('utf-8', 'replace')[:300]
                except Exception:
                    pass
                raise RuntimeError('%s returned HTTP %d%s'
                                   % (_host(url), e.code, ': ' + detail if detail else ''))
            except ValueError:
                # A 200 that is not JSON is a captive portal or a DNS filter's
                # block page, not load. Retrying it six times with backoff wastes
                # a couple of minutes per URL and still fails, so say so instead.
                raise RuntimeError(
                    "%s returned a 200 that is not JSON - this is usually a "
                    "network filter or captive portal intercepting the request, "
                    "not the API. Try from a different network." % _host(url))
            except Exception:
                delay = min(delay * 2.2, 45)
        raise RuntimeError("gave up after %d attempts: %s" % (self.tries, url[:80]))


def _host(url):
    return url.split('/')[2] if '://' in url else url[:40]
