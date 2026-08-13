# Travel guides

Self-contained trip guides for two, plus the toolchain that builds them.

Each destination is a folder under `destinations/`. A landing page is generated
from their `meta.json` files, and GitHub Actions publishes the lot to Pages on
every push to `main`.

**Live:** https://a87pal.github.io/travel/

## Layout

```
shared/TRAVEL-PREFERENCES.md    who we are, how we travel, the deliverable spec
shared/landing.template.html    landing page shell ({{CARDS}} is filled in)

tools/                          the engine - no trip data, no machine paths
                                every script takes --dest SLUG

destinations/<slug>/
  meta.json                     title, dates, blurb, hero -> landing card + <head>
  guide.html                    the guide itself, self-contained
  PLANNING-NOTES.md             reasoning, trade-offs, what was cut and why
  images/                       photos + images/tiles/<map>/ basemap tiles
  maps/
    maps.json                   bounding box, zoom, display width, query context
    markers.py                  markers, legs, legends, captions - build(m)
    places.json                 verified coordinates, with source and date
    legs.json                   which places each drivable leg runs through
    routes.json                 road geometry, distance and driving time, from OSRM
    tilemeta.json               the tiles <-> overlay contract
    gmap_*.html                 generated, gitignored
    places.kml                  pin review surface for Google My Maps, gitignored

build.py                        -> dist/   (never committed)
check.sh                        everything CI checks; run it locally too
preview.sh                      build + serve dist/ on localhost
deploy.sh                       check, build, commit, push
```

## Everyday use

```sh
./preview.sh          # build and look at it on localhost:8000
./check.sh            # exactly what CI runs; no network
./deploy.sh "why"     # check, build, commit, push - CI publishes
```

`build.py` and `check.sh` touch no network, which is why CI can run them.
`tools/tiles.py` (bulk Esri downloads), `tools/resolve.py` (OSM/Wikidata) and
`tools/routes.py` (OSRM, or OpenRouteService with a free key) hit rate-limited
third parties and stay local; their outputs are committed so CI never needs to
re-fetch them. No API key is ever committed, and neither the published page nor
CI needs one — the OpenRouteService key lives in the macOS keychain:

```sh
security add-generic-password -U -a "$USER" -s ORS_API_KEY -w
```

## Adding a destination

```sh
mkdir -p destinations/germany/maps
```

Hand Claude `shared/TRAVEL-PREFERENCES.md` and the prompt in its §14. That file
is the spec for the guide; `tools/README.md` covers the map machinery. Then
write `meta.json` and `maps/maps.json`, and run the pipeline:

```sh
python3 tools/tiles.py    --dest germany                 # basemap tiles
python3 tools/resolve.py  --dest germany --seed
python3 tools/resolve.py  --dest germany --write         # coordinates, automatically
python3 tools/kml.py      --dest germany --export        # then check the pins in Google My Maps
python3 tools/kml.py      --dest germany --import out.kml --write
python3 tools/routes.py   --dest germany --fetch         # road geometry + driving times
python3 tools/overlay.py  --dest germany                 # draw the maps, place the labels
python3 tools/boxes.py    --dest germany                 # 0 overlaps required
python3 tools/maps.py     --dest germany                 # splice into the guide
./check.sh && ./deploy.sh "germany"
```

The landing page picks it up automatically. Set `"listed": false` in
`meta.json` to build a guide without linking it from the landing page.

## Publishing

GitHub Actions builds and deploys on every push to `main`; pull requests run
the same gates without publishing. This needs **Settings → Pages → Source =
"GitHub Actions"**. Public repo, so Actions minutes are unlimited and Pages is
free. The guides carry `robots: noindex, nofollow` — they are not secret, but
they are not meant to be found either.

## Credits

Photography from Wikimedia Commons, under the respective licences.
Basemaps: Esri World Topo (Esri, HERE, Garmin, USGS, NGA, OpenStreetMap
contributors).
