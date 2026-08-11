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
markers.py    you write this: markers, routes, legends, captions — build(m)
   ↓
resolve.py    look every marker's coordinates up from Wikidata / OSM
   ↓          → maps/places.json
overlay.py    project lat/lon → SVG, draw routes + markers, emit map fragments
   ↓          → maps/gmap_<map>.html
boxes.py      check no two labels overlap and no label covers another dot
   ↓
maps.py       splice the fragments into the destination's guide.html
   ↓
validate.py   tag balance, duplicate ids, dead anchors, content preservation
   ↓
../check.sh   all of the above as one gate, plus build.py — this is what CI runs
../deploy.sh  check, build, commit, push
```

Run order for a full map rebuild:

```sh
D=montreal-quebec                                  # or omit --dest if there is only one
python3 tools/tiles.py    --dest $D                # only when a bbox or zoom changes
python3 tools/resolve.py  --dest $D --seed         # only when markers are added
python3 tools/resolve.py  --dest $D --write        # coordinates from Wikidata/OSM
python3 tools/overlay.py  --dest $D                # regenerate the fragments
python3 tools/boxes.py    --dest $D                # must report 0 overlaps, 0 dot-covers
python3 tools/maps.py     --dest $D                # splice into the guide
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

`tiles.py` and `overlay.py` each implement that projection; **they must agree**.
If markers are uniformly offset, that is the bug to look for first.

> Esri's tile URL is `/tile/{z}/{y}/{x}` — row before column. Getting this
> backwards yields a plausible-looking map of somewhere else entirely.

---

## Where coordinates come from — read this before touching a marker

The first version of these maps had coordinates typed from memory. Mount Lincoln
was 420 m north of its summit, Little Haystack 300 m, the Musée de la
civilisation 145 m — sitting in the port basin instead of on rue Dalhousie.
Errors of that size are invisible on the z8 route map and obvious at z13–z15.

**The Esri tiles cannot help.** They are raster JPEGs; the place names printed on
them are pixels, not queryable features. So coordinates come from `resolve.py`:

- **Wikidata** property `P625`, matched by name search. First choice — it covers
  essentially every named summit, church, museum, market and village.
- **OSM Nominatim**, as a fallback for things Wikidata does not carry.

`places.json` stores the result with its `source` (`wikidata:Q…` / `osm:way/…`)
and the date it was `verified`. Rules:

- **Never hand-edit a `lat`/`lon` in `places.json`.** Fix the `query` and re-run.
  `--seed` preserves hand-written queries, so sharpening one is safe. (It did
  not always: it used to regenerate the query for every unresolved place, which
  is exactly the set whose queries had been sharpened by hand.)
- If a place genuinely has no good source — a viewpoint, a trailhead, "the spot
  on the ridge where the trees stop" — set `"source": "manual: <why>"`.
  `resolve.py` will leave it alone forever.
- Anything the source places more than `--max-accept` metres (default 2 km) from
  the stored value is **reported, never applied**. A confident wrong search hit
  is worse than a coordinate that is 200 m off, so a human looks at those.

---

## Label placement

`boxes.py` parses the generated SVG back out, estimates each label's bounding box
from its text length and font size, and reports two failure modes:

- **OVERLAP** — two label boxes intersect.
- **DOTHIT** — a label box sits on top of a different marker's dot.

Both must be zero before publishing. Adjust with `marker()`'s `anchor`
(`"start"` = label to the right, `"end"` = to the left), `dy` (vertical nudge)
and `dx` (horizontal). When a label has to be pushed well clear of a crowded
cluster, pass `lead=True` to draw a hairline connector back to its dot — that is
how the four Lower Town labels in Québec City are handled.

**This is currently hand-tuned, and it is the weakest part of the toolchain.**
Every coordinate change can re-break the layout, and the fix is another round of
nudging `dy` values against `boxes.py`. The right answer is to fold the detector
into `overlay.py` so `marker()` tries candidate placements and picks the first
that does not collide. Worth doing before the next city.

---

## The other scripts

**`maps.py`** replaces each `<div class="gmapwrap">` block in the guide with the
regenerated fragment, using depth-aware `<div>` matching rather than a regex —
the blocks contain nested divs and a regex will silently eat the wrong closing
tag. It is idempotent: the CSS and JS are only injected once.

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
3. `resolve.py --dest <slug> --seed`, sharpen the `query` fields, then
   `--write`. Review everything it flags.
4. `overlay.py` → `boxes.py` → fix collisions → `maps.py` → `validate.py`,
   or just `./check.sh`.
5. Screenshot each map with headless Chrome and **look at it against the
   basemap**. The printed place names on the tiles are the ground truth that
   caught every error we have had. Automated checks did not find those; looking
   did.

`TRAVEL-PREFERENCES.md`, kept beside the guide source, holds the trip-planning spec — who is travelling, how
they like to travel, what a good itinerary looks like. Read it first; this file
only covers the machinery.
