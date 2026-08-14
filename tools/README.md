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
placeid.py    resolve each place to a Google Place ID, so links name it exactly
   ↓          → places.json again (place_id only; never a coordinate)
extracoords.py  OSM/Wikidata coordinates for extras.json, for the My Maps export
   ↓          → extras.json again
overlay.py    project lat/lon → SVG, draw routes, place labels, emit fragments
   ↓          → maps/gmap_<map>.html  + maps/.placement.json
boxes.py      re-check the placement: no overlaps, no covered dots, nothing off-map
   ↓
savedlist.py  build the checklist for loading a Google Maps saved list
   ↓          → maps/savedlist.html
maps.py       splice the fragments into guide.html, fill the leg table
   ↓
validate.py   tag balance, duplicate ids, dead anchors, content preservation
   ↓
../check.sh   all of the above as one gate, plus build.py — this is what CI runs
../deploy.sh  check, build, commit, push
```

Five of those touch the network and none of them run in CI: `tiles.py`,
`resolve.py`, `routes.py`, `placeid.py` and `extracoords.py`. Their output —
tiles, `places.json`, `routes.json`, `extras.json` — is committed, which is why
`check.sh` and `build.py` work offline.

`tripmap.py` sits outside the pipeline: it exports the whole trip as KML for
import into Google My Maps, which is a different phone surface from the saved
list and needs no per-place tapping. See **Saved lists** below for which to use.

### Ask before you build a map

**`tiles.py`, `resolve.py`, `routes.py`, `placeid.py` and `extracoords.py` need
explicit approval every time. Do not run them because a rebuild seems tidy.**
They are the expensive third of the pipeline and the cost is not yours to spend:

- `tiles.py` pulls **one HTTP request per tile** from Esri's basemap service.
  A single z16 neighbourhood map is 20–25 tiles; a four-map pass was 294. That
  is someone else's free tier and someone else's bandwidth.
- `resolve.py` hits Nominatim, which asks for **one request per second and no
  bulk geocoding**, and falls through to Wikidata, which needs a search call
  plus a claims call per candidate and throttles hard — 55 places can take half
  an hour.
- `routes.py` hits OSRM's demo server or spends **OpenRouteService API-key
  quota**, both rate-limited.
- `extracoords.py` hits the same Nominatim and Wikidata as `resolve.py`, for
  every entry in `extras.json` rather than every marker.
- `placeid.py` spends **Google Cloud quota on a billable account**. One
  destination fits many times over in the monthly free allowance, but the
  account behind the key is a real one with a card attached to it.

They are also the only stages that can *silently* make the guide worse: a
geocoder hit can overwrite a hand-reasoned pin (see "Things that have bitten
us"), and a re-fetch can move a route under a caption that still describes the
old one.

The free stages — `overlay.py`, `boxes.py`, `savedlist.py`, `maps.py`,
`validate.py`, `check.sh`, `build.py` — are local, offline and idempotent. **Run those freely.
Almost every map change is one of those**: nothing needs re-downloading unless a
bounding box, a zoom, a marker's identity or a leg's endpoints actually changed.

Approval means the person asked for it or agreed to it for this change. It does
not carry over to the next one.

Run order for a full map rebuild — **the first eight lines need approval**:

```sh
D=montreal-quebec                                  # or omit --dest if there is only one
python3 tools/tiles.py    --dest $D                # only when a bbox or zoom changes
python3 tools/resolve.py  --dest $D --seed         # only when markers are added
python3 tools/resolve.py  --dest $D --write        # coordinates from OSM/Wikidata
python3 tools/kml.py      --dest $D --export       # then verify the pins in Google My Maps
python3 tools/kml.py      --dest $D --import out.kml --write
python3 tools/routes.py   --dest $D --fetch        # road geometry + driving times
python3 tools/placeid.py  --dest $D                # dry run - review every delta
python3 tools/placeid.py  --dest $D --write        # Place IDs, for exact Maps links
python3 tools/extracoords.py --dest $D --write     # OSM coords for the extras
python3 tools/overlay.py  --dest $D                # regenerate the fragments
python3 tools/boxes.py    --dest $D                # must report 0 overlaps, 0 dot-covers
python3 tools/savedlist.py --dest $D               # the saved-list checklist
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

**One narrow exception, and why it is not a contradiction.** `placeid.py` does
call a Google API and does commit what it gets back. Both clauses above still
hold, and it clears them rather than ignoring them:

- Place IDs are **explicitly exempt** from the §3.2.3(b) caching restriction —
  Google's own documentation says so and offers a free call to refresh one. The
  30-day cap that rules out `routes.json` does not reach them.
- Nothing Google-derived is ever *drawn*. A Place ID goes into an outbound
  `google.com/maps` link and nowhere else; the pins on the Esri basemap keep
  coming from OSM and Wikidata via `resolve.py`. The non-Google-map clause is
  about Content displayed on the map, and no Content is.

That is also why `placeid.py` stores so little. It sees Google's `displayName`
and `location`, uses them to print a sanity check, and throws them away — those
*are* Content under the 30-day rule. It keeps the ID, the date and the distance
it measured, and it asserts that it has not moved a coordinate before it writes.

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

## Saved lists — the phone surface for driving

The guide's own maps are the offline artifact: Esri tiles and inline SVG, no
network, printable. They are not what you navigate from. That is a **Google Maps
saved list**, which draws on the main Maps map, syncs to the phone and gives you
native turn-by-turn.

**There is no API for saved lists, and no import path.** Not a missing scope, not
a deprecated endpoint — it has never existed, and the open feature request dates
from late 2025. So the list is loaded by hand, and no amount of tooling changes
that. What tooling *can* remove is the part that is actually slow and actually
error-prone: confirming that what Google found is the place you meant.

`placeid.py` resolves each place to a Place ID; `savedlist.py` builds a
checklist whose links carry it:

```
https://www.google.com/maps/search/?api=1&query=<lat>,<lon>&query_place_id=<ID>
```

That opens one exact place instead of a search. The documented `api=1` Search
action takes only `query` and `query_place_id` — there is no location-bias,
viewport or centre parameter — so a Place ID is the only supported way to make
such a link unambiguous. The coordinate stays as `query` because Google falls
back to it when the ID will not resolve, so a stale ID degrades to the right
spot rather than a confident wrong one.

### Towns, and the places inside them

A geocoder's answer for a town is its administrative centre — a road junction
near the middle, not the wharf or the dining street you actually drive to. These
maps deliberately pin the site rather than the town, so `placeid.py` holds any
administrative result to `--max-admin` (250 m) and reports the rest. Without that
cap, `Lincoln` resolved to the town 998 m from the rental it is supposed to be,
and passed a 1 km distance check on its way through.

Two escape hatches, both set by hand because a script cannot tell "the town" from
"a place in the town":

- **`"place_scope": "town"`** on a `places.json` entry says the centroid *is* the
  target — a route-overview label, a border crossing, somewhere you pass through.
  Such an entry is judged against `--max-town` (6 km) instead, which still
  catches the failure that matters: a same-named town in the wrong region.
- **`maps/extras.json`** holds places that belong on the driving list but are not
  map markers, which is how the attraction survives when its town's pin becomes
  the centroid. Each names a `near` place, whose coordinate biases the search and
  measures the answer, so an extra gets the same verification as a marker without
  needing a coordinate of its own:

```json
{"Croisières AML — whale wharf": {
   "query": "Croisières AML 159 Route 138 Baie-Sainte-Catherine Quebec",
   "near": "Baie-Ste-Catherine", "note": "where the whale cruise boards"}}
```

Extras are committed, appear in their anchor's region on the checklist, and fall
back to their `query` text rather than a coordinate they do not have.

### Working the list

The checklist does the sequencing and nothing else: <kbd>Enter</kbd> opens the
next place, you click Save, <kbd>Space</kbd> ticks and advances, <kbd>←</kbd>
steps back and unticks. Progress lives in `localStorage`, so it survives a
reload and can be done in sittings. Load it once on a laptop, then **share the
list** rather than repeating it on a second account.

**No browser automation, deliberately.** Driving a signed-in Google account with
Playwright or an extension means Google's terms, an account worth far more than
the fifteen minutes it saves, and selectors written against a UI that rotates
its class names. The sequencing was the slow part, and sequencing needs no
automation.

### Embedding: My Maps only

A saved list **cannot be embedded**, public or not. `google.com/maps/placelists/`
answers with `x-frame-options: SAMEORIGIN`, so the browser refuses to frame it on
another origin, and sharing changes who may *open* it rather than who may frame
it. The Maps Embed API's five modes — place, view, directions, streetview,
search — have no list mode either.

`google.com/maps/d/embed` sends no such header, so **My Maps is the embeddable
surface**. Put its `mid` in `meta.json` as `mymaps` and every map grows a *Live
map* button; `overlay.py` appends `&ll=` and `&z=` from that map's own bounding
box, so going live keeps you on the same ground rather than the trip's centroid.
The iframe is created by JS on first click and never on load, which is what keeps
the offline guarantee intact.

The custom map has to be shared "anyone with the link". That is a genuine
exposure decision: the pins include where you sleep.

### Saved list or My Maps?

`tripmap.py` exports the whole trip as KML for **Google My Maps**, which imports
in one step with no per-place tapping. The trade is at the other end: My Maps
will not navigate *along* a drawn line and only hands off from a pin tap, and
custom maps cannot be downloaded for offline use from the phone.

Use the saved list for driving. Use `tripmap.py` when you want the whole shape
of the trip on a phone for free, or as a review surface. They are not exclusive.

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
and says so and changes nothing when a leg has not been fetched. It also splices
the saved-list section, matching to the first `</section>` — sections do not nest
here, and it checks that assumption rather than trusting it.

**`maps.py` is the only script that writes `guide.html`.** `savedlist.py` emits a
fragment and stops, so the snapshot-before-rewrite net in `_dest.snapshot_guide`
stays in one place rather than being reimplemented per tool.

**`savedlist.py`** carries its own `<style>` and `<script>` inside the fragment,
so re-splicing replaces them wholesale. That is idempotent by construction,
rather than by the inject-once check `maps.py` needs for the map CSS.

**`_proj.py`** is the web-mercator projection, the tile-range maths and the
geodesic distance, shared by everything that needs them. **`_http.py`** is the
cached backing-off client — a GET for `resolve.py` and `routes.py`, and a POST
with headers for `placeid.py`, whose cache key folds in the request body so two
different searches to one endpoint cannot collide. **`_metrics.py`** is the
text-width table. **`_dest.py`** resolves `--dest` to paths.

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
