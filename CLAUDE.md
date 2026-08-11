# Working in this repo

A general travel-planner repo: one folder per destination under
`destinations/`, a generated landing page, and a shared map/validation
toolchain in `tools/`. Read `README.md` for the layout.

## The two documents that matter before you write anything

- **`shared/TRAVEL-PREFERENCES.md`** — who is travelling, how they travel, and
  §11's exact spec for the deliverable. Read it in full before planning a trip
  or writing a guide. §14 is the copy-paste prompt for a new destination.
- **`tools/README.md`** — how the maps actually work, where coordinates come
  from, and the failure modes that have already bitten this project.

## Hard rules

**Never hand-edit `lat`/`lon` in `places.json`.** Fix the `query` and re-run
`tools/resolve.py --write`, or pin it as `"source": "manual: <why>"`. The first
version of these maps had coordinates typed from memory and three markers were
300–420 m out. `--seed` preserves hand-written queries, so sharpening one is
safe.

**Nothing in `tools/` may hardcode a slug, a machine path or a map name.** It
is the engine. Trip data lives in `destinations/<slug>/`. Every script takes
`--dest SLUG` and resolves paths through `tools/_dest.py`.

**`tilemeta.json` is a contract.** `tiles.py` writes it and `overlay.py` reads
it, and they implement the same web-mercator projection independently. If
markers are uniformly offset on one map, look there first. It must stay next to
`maps.json` — pointing the two halves at different directories once left
`overlay.py` reading stale metadata while `tiles.py` reported success.

**Run `./check.sh` before committing.** It regenerates the map fragments from
committed inputs, checks label collisions, splices, validates structure, and
fails if a `guide.html` is stale with respect to its `markers.py`. It is what
CI runs. No network.

**Never commit `dist/`** — it is build output. `gmap_*.html` and
`.resolve-cache.json` are artifacts too. `places.json` and `tilemeta.json` *are*
committed, because regenerating them means re-hitting rate-limited services.

**Editing `guide.html` with a script?** Every substitution must assert it
matched exactly once. A string-replace that does not match leaves the file
untouched, and a script that then prints "done" hides the failure. `maps.py`
does this; keep it that way. Then run `tools/validate.py`, which diffs the
prose against `git show HEAD:` to catch content a bad slice dropped silently.

## meta.json

```json
{
  "title": "Québec & Montréal",
  "tagline": "Je me souviens",
  "dates": "Aug 26 – Sep 6, 2026",
  "start": "2026-08-26",
  "end": "2026-09-06",
  "blurb": "Twelve days following the St. Lawrence from the mountains to the sea.",
  "hero": "images/hero_qc.jpg",
  "favicon": "🐋",
  "themeColor": "#1d5540",
  "appleTitle": "Québec 2026",
  "listed": true
}
```

Slug comes from the folder name. `start`/`end` sort the landing page into
Ahead/Been on their own as time passes. `listed: false` builds the guide but
keeps it off the landing page.

## Gates in build.py

1. **Structure** — tag balance, duplicate ids, dead `href="#…"` anchors, shared
   with `tools/validate.py`.
2. **Assets** — every `src="images/…"` resolves, relative to the destination.
3. **Orphans** — files on disk that nothing references. Advisory, not fatal.

The `<head>` injection anchors on a *regex* for the viewport meta, not an exact
byte string. The old `deploy.sh` matched one literal and aborted if a single
attribute was reordered.

## Voice

Match the existing guides: luxury tour operator plus real logistics. Addresses,
hours, prices, booking links, parking, grocery stores. No filler attractions —
if a stop is weak, cut it and say so. Rationale goes in `PLANNING-NOTES.md`,
not the guide.
