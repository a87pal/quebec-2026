# Trip-guide toolchain

Scripts that build the maps and validate the guides. This directory is the
**engine**: it hardcodes no destination, no map name and no machine path. Every
script takes `--dest SLUG` and reads its data from `destinations/<slug>/maps/`.
See **Starting a new city** at the bottom.

Everything here is plain Python 3 with no third-party packages, no API keys and
no build step. The published page has no runtime dependencies at all: the maps
are local JPEG tiles plus inline SVG, so they work offline and cannot break when
a service changes.

---

## The pipeline

```
maps.json     you write this: bounding box, zoom, display width per map
   ↓
tiles.py      download Esri basemap tiles for each map's bounding box
   ↓          → images/tiles/<map>/<x>_<y>.jpg   + maps/tilemeta.json
markers.py    you write this: markers, legs, legends, captions — build(m)
   ↓
resolve.py    look every marker's coordinates up from OSM / Wikidata
   ↓          → maps/places.json
kml.py        export the pins for review in Google My Maps, merge corrections back
   ↓          → maps/places.kml, then places.json again
legs.json     you write this: which places each drivable leg runs through
   ↓
routes.py     fetch real road geometry, distance and driving time from OSRM
   ↓          → maps/routes.json
overlay.py    project lat/lon → SVG, draw routes, place labels, emit fragments
   ↓          → maps/gmap_<map>.html  + maps/.placement.json
boxes.py      re-check the placement: no overlaps, no covered dots, nothing off-map
   ↓
maps.py       splice the fragments into guide.html, fill the leg table
   ↓
validate.py   tag balance, duplicate ids, dead anchors, content preservation
   ↓
../check.sh   all of the above as one gate, plus build.py — this is what CI runs
../deploy.sh  check, build, commit, push
```

Three of those touch the network and none of them run in CI: `tiles.py`,
`resolve.py` and `routes.py`. Their output — tiles, `places.json`, `routes.json` —
is committed, which is why `check.sh` and `build.py` work offline.

Run order for a full map rebuild:

```sh
D=montreal-quebec                                  # or omit --dest if there is only one
python3 tools/tiles.py    --dest $D                # only when a bbox or zoom changes
python3 tools/resolve.py  --dest $D --seed         # only when markers are added
python3 tools/resolve.py  --dest $D --write        # coordinates from OSM/Wikidata
python3 tools/kml.py      --dest $D --export       # then verify the pins in Google My Maps
python3 tools/kml.py      --dest $D --import out.kml --write
python3 tools/routes.py   --dest $D --fetch        # road geometry + driving times
python3 tools/overlay.py  --dest $D                # regenerate the fragments
python3 tools/boxes.py    --dest $D                # must report 0 overlaps, 0 dot-covers
python3 tools/maps.py     --dest $D                # splice into the guide (snapshots it first)
python3 tools/validate.py --dest $D                # must report "all balanced"
./deploy.sh "what changed"
```

`./check.sh` runs the overlay → boxes → maps → validate → build chain for every
destination and additionally fails if a committed `guide.html` is stale with
respect to its `markers.py`. Run it before committing; CI runs the same script.

---

## How the maps actually work

There is no map library. Each map is:

1. **A grid of 256×256 Esri World Topo JPEGs**, absolutely positioned inside a
   container with a fixed `aspect-ratio`. Positions are percentages, so the grid
   scales to any container size.
2. **One inline SVG on top**, `viewBox="0 0 W H"` where W×H is the tile grid's
   pixel size, and `preserveAspectRatio="none"` so it stretches in lockstep with
   the tiles.

Because both layers scale identically, the overlay stays registered at any size —
which is what makes the thumbnail/expand behaviour possible.

`maps/tilemeta.json` is the contract between the two halves, and it must stay
next to `maps.json` where `overlay.py` reads it — the two once pointed at
different directories, and `tiles.py` reported success while `overlay.py` went
on using stale metadata. For each map it records
zoom `z`, the tile range, the composite size `W`/`H`, and the pixel origin
`ox`/`oy` of the top-left tile. A marker's SVG position is just:

```
web-mercator pixel at zoom z, minus (ox, oy)
```

`tiles.py` and `overlay.py` both get that projection from `_proj.py`, so they
cannot disagree. They used to implement it separately, and "markers are
uniformly offset" was the symptom to look for first; that failure mode is now
structurally impossible rather than merely documented.

> Esri's tile URL is `/tile/{z}/{y}/{x}` — row before column. Getting this
> backwards yields a plausible-looking map of somewhere else entirely.

---

## Where coordinates come from — read this before touching a marker

The first version of these maps had coordinates typed from memory. Mount Lincoln
was 420 m north of its summit, Little Haystack 300 m, the Musée de la
civilisation 145 m — sitting in the port basin instead of on rue Dalhousie.
Errors of that size are invisible on the z8 route map and obvious at z13–z15.

**The Esri tiles cannot help.** They are raster JPEGs; the place names printed on
them are pixels, not queryable features. So coordinates come from two passes: an
automated one, then a human one.

### Pass 1 — `resolve.py`

- **OSM Nominatim** first: one request per place.
- **Wikidata** property `P625` as the fallback. It is not first despite covering
  more, because it needs a search call plus a claims call per candidate and
  throttles hard enough that 55 places can take half an hour.

### Pass 2 — `kml.py`, which is where the real verification happens

A geocoder cannot tell you that the coordinate it found is not the place you
meant. It put Château Frontenac in the Dordogne and Hautes-Gorges 8 km from the
sector you drive to, and both answers looked confident. What catches that is
looking at a map, so `kml.py` makes looking cheap:

```sh
python3 tools/kml.py --export             # → maps/places.kml
#   import that as a layer at https://www.google.com/mymaps
#   pins are coloured by confidence: red = typed by hand, amber = manual
#   override, green = geocoder hit not yet eyeballed, blue = already confirmed
#   drag anything wrong, then Export to KML
python3 tools/kml.py --import mine.kml    # dry run: what moved, and by how far
python3 tools/kml.py --import mine.kml --write
```

Every pin that comes back becomes `"source": "gmaps: confirmed"` or
`"gmaps: dragged <N> m on Google basemap"`, with the previous source kept in
`was` so a manual override's reasoning is never destroyed. Both `--seed` and
`resolve.py` skip `gmaps:` sources, so a verified pin stays put.

`--import` refuses to be quiet about anything it will not apply: a placemark
whose name does not match a `places.json` key, or a move beyond `--max-move`,
is printed and the command exits non-zero. A correction dropped in silence is
worse than one refused out loud.

### Rules

- **Never hand-edit a `lat`/`lon` in `places.json`.** Correct the pin in Google
  My Maps and re-import, or fix the `query` and re-run `resolve.py`.
  `--seed` preserves hand-written queries, so sharpening one is safe. (It did
  not always: it used to regenerate the query for every unresolved place, which
  is exactly the set whose queries had been sharpened by hand.)
- If a place genuinely has no good source — a viewpoint, a trailhead, "the spot
  on the ridge where the trees stop" — set `"source": "manual: <why>"`.
  `resolve.py` will leave it alone forever.
- Anything the source places more than `--max-accept` metres (default 2 km) from
  the stored value is **reported, never applied**. A confident wrong search hit
  is worse than a coordinate that is 200 m off, so a human looks at those.
- **`overlay.py` is fatal on a marker with no `places.json` entry**, and on one
  whose coordinate falls outside the bounding box of the map it is drawn on.
  The second check is what would have caught the Dordogne château automatically.
  Pass `allow_unsourced=True` at the call site to draw something deliberately
  schematic.

---

## Routes

Route lines used to be eight to thirteen lat/lon vertices typed by hand into
`markers.py` — the same practice this file forbids for markers, for the same
reason. They were straight lines between towns pretending to be roads, and they
carried no distance and no driving time.

Drivable lines are now declared in `legs.json` by place name, not coordinate:

```json
{"chemin-du-roy": {"map": "route", "cls": "rt",
                   "via": ["MONTRÉAL", "Trois-Rivières", "Deschambault", "QUÉBEC CITY"]}}
```

Each name is a `places.json` key, so a leg follows its pins when they are
corrected. `routes.py` fetches the geometry into `maps/routes.json`, which is
committed, from either of two OpenStreetMap-derived providers:

```sh
python3 tools/routes.py --fetch                    # osrm, keyless, the default

# ors: free key from https://account.heigit.org/signup, stored in the keychain
security add-generic-password -U -a "$USER" -s ORS_API_KEY -w
python3 tools/routes.py --provider ors --fetch     # when osrm is unreachable
```

`osrm` needs nothing. `ors` needs a free key (2,000 requests/day, no card). It is
looked for in three places, first hit wins: `--key`, then `$ORS_API_KEY`, then
the **macOS keychain** under service name `ORS_API_KEY`. The keychain is the one
to use — `security add-generic-password … -w` with no value prompts without
echoing, so the key never reaches your shell history, and it is never in this
repo, which is published to GitHub Pages. The lookup is skipped off macOS, so
this stays portable; CI needs no key at all because `routes.json` is committed.

The key is sent as a request header, so it does not reach the request cache
either. `routes.py` prints where it found the key, never the key itself.

Use `ors` when a network blocks the keyless routers, which many corporate and
school networks do as a whole category. ORS also offers `foot-walking` and
`foot-hiking` profiles, so the city walks and the Franconia ridge could become
real geometry by setting `"profile"` on the leg.

Routing data is ODbL, so a map that draws a fetched leg prints a routing
attribution next to the basemap credit. A map with no fetched legs does not.

### Why not Google

Google's Directions and Routes APIs return exactly the right shape, and are
still not an option — not because of the key, but because of two clauses in the
Maps Platform Service Specific Terms:

- **§4.2 / §19.2** — "Customer must not use Google Maps Content from the
  Directions API in conjunction with a **non-Google map**." These maps are Esri
  tiles.
- **§4.3 / §19.3** — returned coordinates may be cached for at most **30
  consecutive calendar days**. Committing `routes.json` permanently, so CI never
  re-fetches, is the entire point of this file.

Either clause alone rules it out. OSM-derived routing under ODbL has neither
problem: cache it forever, draw it over any basemap, attribute it.

`markers.py` then draws
it with `m.leg(P, "chemin-du-roy", fallback=[...])`; the fallback is the old
schematic vertex list, used only until the leg has been fetched, so a guide
still builds before anyone has run `routes.py`.

Geometry is stored unsimplified and thinned per map at draw time, so one fetch
serves the z8 overview and a z13 detail map. `distance_m` and `duration_s` fill
the Distance and Driving cells of any `<tr data-leg="…">` row in the guide's leg
table — the hand-written Notes column is left alone, because border crossings
and lockbox codes are not things a router knows.

Not every line is routable. The Franconia ridge is a hiking trail and the two
city walks are pedestrian, and OSRM's public server routes cars. Those stay
hand-drawn and their captions say they are schematic, which is what
`TRAVEL-PREFERENCES.md` §8 asks for.

> Both providers want `lon,lat`, the opposite of the convention used everywhere
> else here. OSRM returns `polyline6`; decoding that as `polyline5` yields a
> route ten times too large, off the coast of Africa. ORS is asked for GeoJSON
> instead, so there is no decode step and no precision to get wrong.

> Some corporate and school networks block the keyless routers at the DNS layer —
> `router.project-osrm.org`, `brouter.de`, `*.openstreetmap.de` and friends all
> go, while keyed commercial APIs pass. The symptom is an HTTP 200 that is not
> JSON, which is a filter's block page; `_http.py` detects that and says so
> rather than retrying it six times. Switch to `--provider ors`, or run the fetch
> from another network. Everything else in the toolchain works either way,
> because `routes.json` is committed.

---

## Label placement

Automatic. `marker()` emits nothing when it is called — it records what it was
asked to draw and returns a placeholder — and `wrap()` runs a placement pass once
every dot, route and label on that map is known.

Each label is tried against a series of candidate positions, best first: beside
the dot on either side, then a row up or down, then centred above or below, then
progressively further out on a leader line. A candidate is rejected outright if
it leaves the map, overlaps a label already placed, or reaches another marker's
dot. Crossing a route line is a tie-breaker rather than a veto, because the
labels are drawn with a white halo under the text and stay legible over a road.
Markers are placed in priority order — `base`, `hi`, `ev`, `stop` — so the labels
that matter most get first pick of the space around them.

This replaced roughly a hundred hand-tuned `anchor`/`dx`/`dy`/`lead` arguments in
one destination's `markers.py`. It was previously the weakest part of the
toolchain: every coordinate change could re-break the layout, and the fix was
another round of nudging values against `boxes.py`.

`anchor` / `dx` / `dy` at a call site still win, and are the right tool when the
automatic answer is legal but reads badly. Pass all three to pin a label exactly;
pass one and the search fills in the rest.

**Widths come from real font metrics.** `_metrics.py` reads a table measured by
`metrics.py` out of a font file's `hmtx` table and committed to `metrics.json`.
The old estimate was `len(text) × font_size × 0.56` — a raw character count, off
by up to 44% on these labels, worst on exactly the ones these guides are full of:
`Sainte-Anne-de-Beaupré` is mostly narrow letters, `MONTRÉAL` is all caps, and
the middle dot in `C$4.25 · sunset` is nothing like an average character.

The measured font is a proxy, not an oracle — the guide ships no `@font-face`, so
labels render in Inter where the reader has it and system-ui otherwise, and there
is no single right answer to measure. `_metrics.py` adds a safety margin on top.
The point is to stop labels colliding, not to predict a pixel.

`boxes.py` still runs, and still must report zero. It now reads
`maps/.placement.json` — the boxes the placer actually used — instead of parsing
the generated SVG back out with a regex. That regex was really testing whether
the emitter and the parser still agreed about attribute order: reorder one
attribute in `marker()` and it matched zero markers and reported all clear. It
also cross-checks the marker count against the emitted fragment, so the two
halves cannot drift apart unnoticed.

If a label genuinely cannot be placed, `overlay.py` says so and exits non-zero
rather than emitting a clean-looking map with two labels on top of each other.
The fix is to widen the map's bounding box, raise `dispw`, or cut a marker.

---

## The other scripts

**`maps.py`** replaces each `<div class="gmapwrap">` block in the guide with the
regenerated fragment, using depth-aware `<div>` matching rather than a regex —
the blocks contain nested divs and a regex will silently eat the wrong closing
tag. It is idempotent: the CSS and JS are only injected once. It also fills the
Distance and Driving cells of every `<tr data-leg="…">` row from `routes.json`,
and says so and changes nothing when a leg has not been fetched.

**`_proj.py`** is the web-mercator projection, the tile-range maths and the
geodesic distance, shared by everything that needs them. **`_http.py`** is the
cached backing-off GET that `resolve.py` and `routes.py` both use. **`_metrics.py`**
is the text-width table. **`_dest.py`** resolves `--dest` to paths.

**`validate.py`** is the safety net for any scripted edit of the guide. It checks
tag balance, section order, duplicate ids, that every `href="#…"` resolves, and —
most usefully — diffs the *prose* before and after to catch content silently
dropped by a bad slice. Expect a handful of false positives from sentences whose
neighbours changed; look at the list, do not just read the count.

---

## Things that have bitten us

- **Wikimedia rate-limits scripted bulk downloads** (HTTP 429) and rejects
  arbitrary thumbnail widths (HTTP 400). Use the exact URLs the API returns, send
  a browser User-Agent, and pace the requests.
- **Python buffers stdout.** A long-running script that appears hung is usually
  just sitting in a backoff with nothing flushed. Run with `python3 -u`.
- **String-replace patches fail silently.** A patch that does not match leaves the
  file untouched, and if the script then prints "done" you will not notice. Every
  substitution in these tools asserts `count == 1` first. Keep it that way.
- **Do not verify a git push by reading the remote while it is still in flight.**

---

## Starting a new city

Nothing in this directory needs editing. Everything below is new files under
`destinations/<slug>/maps/`.

1. Write `maps.json` — one entry per map, with a bounding box, a zoom, a display
   width and a `context` string used to disambiguate coordinate lookups. Zoom 8
   suits a multi-day driving route, 10–13 a region, 13 a city, 15 a historic
   core. Run `tiles.py --dest <slug>`; check the printed tile counts are sane
   (a few hundred total, not thousands).
2. Write `markers.py`, defining `build(m)` that returns `{map_name: fragment}`.
   One block per map. Put in approximate coordinates — they are placeholders.
   Do not write `anchor`/`dx`/`dy`; placement is automatic.
3. `resolve.py --dest <slug> --seed`, sharpen the `query` fields, then
   `--write`. Review everything it flags.
4. `kml.py --export`, verify the pins in Google My Maps, `kml.py --import … --write`.
   This is the step that actually catches wrong coordinates. Do not skip it.
5. Write `legs.json` for the drivable lines, then `routes.py --fetch`.
6. `overlay.py` → `boxes.py` → `maps.py` → `validate.py`, or just `./check.sh`.
7. Screenshot each map with headless Chrome and **look at it against the
   basemap**. The printed place names on the tiles are the ground truth that
   caught every error we have had. The gates added since — verified pins,
   bounding-box containment, automatic placement — narrow what looking has to
   catch. They do not replace it.

`TRAVEL-PREFERENCES.md`, kept beside the guide source, holds the trip-planning spec — who is travelling, how
they like to travel, what a good itinerary looks like. Read it first; this file
only covers the machinery.
