# -*- coding: utf-8 -*-
"""Web-mercator projection and geodesic distance, in one place.

tiles.py and overlay.py used to implement this projection independently, and
tools/README.md carried a warning to check them against each other first
whenever markers came out uniformly offset. They now share this module, so the
two halves cannot drift apart.

tilemeta.json is still the contract between them: tiles.py records the zoom,
the tile range, the composite size W/H and the pixel origin ox/oy of the
top-left tile; overlay.py turns that back into a projector. A marker's SVG
position is the web-mercator pixel at zoom z minus (ox, oy).
"""
import math

TILE = 256


def px(lat, lon, z):
    """Absolute web-mercator pixel coordinate at zoom z, in 256 px tiles."""
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n * TILE
    lr = math.radians(lat)
    y = (1.0 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2.0 * n * TILE
    return x, y


def tilemeta(z, lat, lon):
    """Tile range and composite geometry covering a [min,max] lat/lon box.

    The composite is always a whole number of tiles, so it covers at least the
    requested box and usually a little more.
    """
    x0, y1 = px(lat[0], lon[0], z)      # SW -> min x, max y
    x1, y0 = px(lat[1], lon[1], z)      # NE -> max x, min y
    tx0, tx1 = int(x0 // TILE), int(x1 // TILE)
    ty0, ty1 = int(y0 // TILE), int(y1 // TILE)
    nw, nh = tx1 - tx0 + 1, ty1 - ty0 + 1
    return dict(z=z, tx0=tx0, tx1=tx1, ty0=ty0, ty1=ty1,
                W=nw * TILE, H=nh * TILE, ox=tx0 * TILE, oy=ty0 * TILE)


def projector(m):
    """Build P(lat, lon) -> (x, y) in composite pixels for one tilemeta entry."""
    z, ox, oy = m['z'], m['ox'], m['oy']

    def P(lat, lon):
        x, y = px(lat, lon, z)
        return round(x - ox, 1), round(y - oy, 1)

    return P


def metres_per_px(lat, z):
    """Ground resolution at a latitude. Used to size simplification tolerances."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)


def metres(a, b):
    """Great-circle distance between two (lat, lon) pairs."""
    (la1, lo1), (la2, lo2) = a, b
    R = 6371000.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def simplify(pts, tol):
    """Douglas-Peucker on a list of (x, y), tolerance in the same units.

    Callers project first and thin in pixel space, so the tolerance means what
    it looks like: sub-pixel detail. Route geometry is stored at full OSRM
    resolution and thinned per map, which is how one routes.json serves a z8
    overview and a z13 detail map without refetching.
    """
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        den = math.hypot(dx, dy)
        best, bi = -1.0, None
        for k in range(i + 1, j):
            x, y = pts[k]
            if den == 0:
                d = math.hypot(x - x1, y - y1)
            else:
                d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / den
            if d > best:
                best, bi = d, k
        if best > tol:
            keep[bi] = True
            stack.append((i, bi))
            stack.append((bi, j))
    return [p for p, k in zip(pts, keep) if k]
