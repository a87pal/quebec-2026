# Planning Notes — Québec & Montréal, Aug 26 – Sep 6, 2026

Everything that shaped the itinerary but doesn't belong in the guide: reasoning, trade-offs, what got cut, what we're missing, and how this compares to what the big operators sell.

---

## 0. The copy rewrite — the through line, and the fact-check log

### Why the old through line went

The guide asserted that the trip's *argument* was **la survivance**, and then bent
every day to it. Franconia Ridge — a New Hampshire alpine day in the Merrimack
watershed — was press-ganged into a story about French Canada surviving the
Conquest, and a tick-list item under a Benedictine abbey read "Your first proof
that the Church is why the language survived." The claim was unfalsifiable, the
reader had to carry it, and it earned nothing. The Act I–IV headers ("The land,
before anybody was on it", "Where the argument stops mattering") were the same
problem in the table of contents.

### What replaced it

**The river, stated as geography rather than argued as a thesis.** Every base is
one step further down the St. Lawrence, and each one is where it is because of
something the river does at that point:

| Base | What the river does there |
|---|---|
| Montréal | Island at the foot of the Lachine Rapids — the first place boats had to stop |
| Québec City | The *kebec*: under 1 km wide beneath a 90 m cliff, so cannon could close it |
| Île d'Orléans | Tidal and brackish; farms run in ribbons back from the water |
| Charlevoix | 20 km across and fully salt |
| Tadoussac | A 270 m fjord empties in, forcing up the cold water the whales feed in |

This is verifiable at every stop, it explains why the days run in this order, and
it never has to be accepted — only noticed. And *Je me souviens* is now a single factual card —
Eugène-Étienne Taché carved it under the Parliament Building's arms in 1883 and
never explained it; it has been on the plates since 1978 — rather than the
organising claim of the whole document.

### The ice, added as a prologue — and why it is not the through line

Franconia was the hole in the river: a Merrimack-watershed day in a St. Lawrence
document, previously handled by admitting it did not fit. The Laurentide Ice
Sheet closes it — it carved Franconia Notch *and* made the river, so the ridge on
Day 1 and the whales on Day 9 are the same event 800 km apart.

It was deliberately **not** promoted to the through line. The river is an axis of
travel: it has a direction, so it orders the days and explains why the whales are
last. The ice is a time story with no such axis, and running the trip on it would
mean asking the reader to read a 20,000-year retreat as a twelve-day drive —
which is the *la survivance* failure mode above, rebuilt.

So it appears exactly once, as one paragraph opening part one, and never again as
a theme. It earns that paragraph because the copy was already leaning on it
unnamed in six places: the Flume "since the ice left", the Basin's glacial
pothole, Canyon Sainte-Anne "since the ice left", "Ice deepened it" at Charlevoix,
the glacial trough at Hautes-Gorges, and the 270 m fjord driving the Tadoussac
upwelling. Naming the agent once costs a paragraph and pays off six times.

**Guard:** if the ice starts appearing in tick lists or day ledes, it has become
la survivance and should be cut back to the one paragraph.

The hero one-liner also swapped "three nights in Montréal" — logistics already in
the itinerary table — for Mount Royal standing out of the Champlain Sea as an
island, which pays off on Day 4 when they climb it.

**From `.tmp/throughline.md`, deliberately not used** (unsupported or wrong, held
to the same standard as the fact-check log below): puffins nesting and sharks
swimming at Montréal; the crust depressed "over a kilometre" (far too much for
the St. Lawrence lowland — the guide says only that the land went below sea
level); the named beluga skeleton "Felix"; rebound "a few millimetres per
century" (the units are off by ~1000×); the St. Lawrence as "one of the youngest
rivers in the world" at 6,000 years; and cold-based ice preserving the Franconia
crest specifically (genuine research, but contested and studied on Mount
Washington, not Franconia).

**Open, not actioned:** §2's Charlevoix lede dates the impact to 350 Ma, matching
the older 342 ± 15 Ma figure; more recent work puts it near 450 Ma. Worth a check
since it anchors the whole Charlevoix section.

### Structural changes to the copy

- Every one of the **41 attraction blocks** now runs name → highlights (a new
  `.hl` strip of three concrete facts) → description → logistics → full detail.
- The **same 11-word layer-3 label** ("Full detail — what you walk through, and
  every reason it earns the time") appeared on 35 stops. All are now specific.
  Replaced by script with an exact-once assertion per substitution, per
  `CLAUDE.md`.
- **Part five was called "Stats"** and contains no stats. It is now "Why it's
  worth it", with the nav updated.
- Tick lists were carrying logistics ("Costs nothing and takes ninety minutes",
  "Air-conditioned and indoors", "Lunch here is half Montréal prices"). Those
  moved to `.logi` or went.
- Cut: the goat rank joke, "a fairly precise metaphor for the province", "which
  tells you everything about this city", "and honestly, maybe do this anyway",
  "sore quads on day two become sore quads on day six", "the third-best waterfall
  in the region", "this is not a footnote". Bota Bota was pitched twice; the Old
  Montréal duplicate is gone. "Almost no Americans" appeared four times and now
  appears once, where it is genuinely surprising.

### Corrections forced by the repo's own measured data

`routes.json` now carries real OSRM/ORS distances and times, and three prose
figures contradicted them:

| Was | Now | Source |
|---|---|---|
| Run home ≈870 km, 8 h 30 – 9 h 30 | **915 km, 10 h 53 measured** — an hour and a half longer | `routes.json: run-home` |
| Day 9 depart 6:45, pier by 9:15 | Drive is **2 h 55**, so 6:45 arrives ~9:40 with boarding open. **Departure moved to 6:15** | `routes.json: quebec-tadoussac` |
| Day 0 ≈230 mi | **≈245 mi / 395 km, 4 h 28** | `routes.json: ct-franconia` |

The lodging comparison table's "Sunday drive home" row was updated to match
(≈915 vs ≈975 km) even though that section was otherwise out of scope, because
leaving a known-wrong number in place is worse than the scope line.

### Corrections forced by the real Airbnb addresses

The bases are booked and are not all where the prose assumed:

- **Montréal — 3613 bd Saint-Laurent** is the lower Main, not Mile End. Day 4
  opened with a bagel run "walk Mile End for an hour"; it is now a Métro ride up,
  with the walking saved for Mount Royal.
- **Québec — 735 bd Charest Est** is Saint-Roch, below the cliff. Day 6's route
  chip said "Base → Porte Saint-Jean 6 min"; it is 15 minutes and a climb up the
  côte d'Abraham. The act lede now says you sleep below the cliff.
- **Baie-Saint-Paul — 352 Rang de Saint-Placide Sud** is a farmhouse ~10 min up
  the valley, not the gallery street. Day 10's "shower, then walk rue
  Saint-Jean-Baptiste end to end" now says drive down first, and settle who is
  driving before the wine list arrives.

**Closed in §12:** the two stale marker labels (`YOUR BASE — Plateau / Mile
End`, `YOUR BASE — St-Jean-Baptiste`) were renamed to `YOUR BASE — The Main` and
`YOUR BASE — Saint-Roch` when the neighbourhood maps were built.

### Fact-check log

Every claim checked against a source. Verdicts:

| Claim | Verdict | Source |
|---|---|---|
| Cyclorama of Jerusalem, visitable next to the basilica | **WRONG — closed to the public since Oct 2018**, building for sale. It was sold three times as a stop, including as a rain plan. Replaced with Atelier Paré; the closure is now stated in red. | National Trust for Canada; CBC |
| Manoir Montmorency "a 1780s villa built by the future King William IV's brother, the Duke of Kent" | **WRONG.** Built **1781 by Governor Frederick Haldimand**; the Duke of Kent was a tenant 1791–94, and is worth naming as **Queen Victoria's father**. Also burned 1993, rebuilt 1994. | Canadian Encyclopedia; Sépaq |
| Sainte-Anne-de-Beaupré basilica "finished in 1926", "fifth church" | **WRONG.** Begun **1923**, interior finished **1946**, consecrated **1976**; sources give it as the **fourth** church on the site. | Wikipedia; Canadian Encyclopedia |
| Île d'Orléans "the first historic district in Québec", 1970 | **WRONG** — Vieux-Québec was protected in 1963/64. Now "first **rural** historic district". | RPCQ; MRC de l'Île-d'Orléans |
| Bonsecours Market "once Canada's parliament building's neighbour" | **WRONG and weaker than the truth** — it *housed* the Parliament of the Canadas in 1849 after the previous one was burned by rioters, then was city hall 1852–78. | Canadian Encyclopedia; HistoricPlaces.ca |
| Flume Gorge walls "close to twelve feet apart" | **Imprecise** — 12 **to 20** ft apart, 70–90 ft high, 800 ft long. Added the 1808 discovery and the boulder swept away in 1883. | NH State Parks; Wikipedia |
| Old Québec "first **urban site** in North America" listed by UNESCO | **Overclaim** (Antigua Guatemala, 1979). Softened to "the first **city** on the continent", which is how Québec itself puts it. | Ville de Québec; UNESCO |
| Notre-Dame-des-Victoires "the oldest stone church on the continent, 1688" | **Softened** to "begun 1687 … generally called the oldest stone church in North America — certainly the oldest to have kept its original walls". | Parks Canada; Lonely Planet |
| Onhwa' Lumina "nightly Aug 28 – Sep 6, the only ten days all season it isn't weekends-only" | **WRONG** — it runs nightly from **26 June**; weekends-only starts **Sep 11**. Price confirmed at C$33.75 + tax, parking C$10.50, entries 8:00/8:20/8:40. | Tourisme Wendake |
| Haskell Free Library "access rules have changed — check before detouring" | **Vague, now specific.** The restriction applies to **Canadians** (US checkpoint required from Oct 2025; a Canadian-side door opened June 2026). Approaching from Derby Line before crossing, the front door is on US soil and there is nothing to arrange. | VTDigger; CBC; Seven Days |
| Canada Strong Pass, Parks Canada free to Sep 7 | **CORRECT** — free **June 19 – Sep 7, 2026**. Leaned on six times; all hold. | canada.ca |
| Citadelle ceremonial season ends Aug 30, 2026 | **CORRECT** — musical performances run to **Aug 30**, the day before arrival. | lacitadelle.qc.ca; quebec-cite.com |
| MUTEK Aug 25–30, 27th edition, free stage 5 p.m.–midnight | **CORRECT.** ~120 artists from 28 countries. The named line-up ("Jeff Mills and Rival Consoles") was **cut** — unverified. | montreal.mutek.org |
| Gardens of Light 13th edition, *Shan Hai Jing*, opens Aug 29 | **CORRECT**, and sharpened with Xiwangmu and the Jianmu tree. | espacepourlavie.ca |
| AML whale cruise: 10:15/1:30/4:30, ≈C$135, guarantee excludes Zodiac | **CORRECT** — C$134.99 adult 2026, **3:00–3:30** duration (guide said a flat 3 h), season May 9 – Nov 1. | croisieresaml.com |
| JOAT Sep 1–7; Envol et Macadam Sep 10–12 with free opening night | **CORRECT** — Envol's free night is Thursday Sep 10 at the Agora du Port de Québec. | joatfestival.com; envoletmacadam.com |

**Not verified, left standing with their existing hedges:** J.A. Moisan "plausible
claim to being the oldest grocery store in North America" (already hedged in the
copy), Morrin Centre "oldest learned society in Canada", Tadoussac Petite
Chapelle, Olmsted's road to the summit, and the MNBAQ's Riopelle holdings during
the Espace Riopelle move (already carries a verify-first warning).

---

## 1. What changed from the previous version, and why

| Change | Reason |
|---|---|
| **Departure moved to Wednesday 6 p.m.** | Kills the 4 a.m. drive. Franconia Ridge now gets a rested full day with a 7:30 a.m. trail start, *and* Friday morning survives as a genuine weather backup. This is the single highest-value change to the whole plan. |
| **Added whale watching** (Baie-Sainte-Catherine, Sep 4) | The Saguenay–St. Lawrence confluence is widely called the best whale-watching site on earth, and early September is peak. Blue whales — the largest animals that have ever existed — feed here. This is the strongest once-in-a-lifetime candidate available on this route and it was missing entirely. |
| **Added Onhwa' Lumina** (Wendake, Sep 3) | Moment Factory night-walk. Runs **Aug 28 – Sep 6, 2026 only** — the trip window sits exactly inside it. Pure luck; would have been criminal to miss. |
| **Added AURA** (Notre-Dame, Aug 29) | The most spectacular 30 minutes available in Montréal, and it pairs with the daytime basilica visit rather than duplicating it. |
| **Added Gardens of Light** (Botanical Garden) | Opens **Aug 29, 2026**. Night two is opening weekend. |
| **Added Tam-Tams** (Mount Royal, Aug 30) | Free, Sundays only, and Aug 30 is a Sunday. Unrepeatable if the days were ordered differently. |
| **MUTEK promoted from footnote to daily fixture** | Free outdoor stage, 5 p.m.–midnight, Aug 25–30. Covers **all three** Montréal nights. It was buried in a logistics box before. |
| **Added Saint Joseph's Oratory** | Largest church dome in Canada, free, open till 9 p.m. Its absence was the biggest omission in Montréal. |
| **Added Sainte-Anne-de-Beaupré + Canyon Sainte-Anne** | Combining these with Montmorency and Île d'Orléans turns a half-empty day into the best-value day of the trip. |
| **Added Musée de la civilisation** | The best museum in Québec City, previously absent. |
| **Added the Holy Door** at Notre-Dame de Québec | Only one in the Americas, one of eight in the world, free. A genuine "only place on earth" item that was missing. |
| **Replaced Magog with Abbaye Saint-Benoît-du-Lac** | Magog waterfront was a weak, generic stop. The abbey delivers history, architecture (Dom Bellot), unique food (monastery blue cheese) and a live cultural event (Gregorian chant) in ninety free minutes. Strictly better on all four axes. |
| **Cut Parc national de la Jacques-Cartier** | A third glacial valley between Franconia and Hautes-Gorges. Redundant, and it was already marked "optional" — which is a sign a stop shouldn't be there. The day became Wendake + museums instead. |
| **Added Trois-Rivières Old Prison + Deschambault** | Turns the Montréal→Québec transfer into the Chemin du Roy rather than three hours of autoroute. |

---

## 2. The shape: why four bases and not fewer

Eleven nights, four beds, three moves. Eight of twelve days start and end in the same bed.

**Could we base only in Québec City and skip Charlevoix?**
No. Hautes-Gorges is 2 h 15 each way from Québec City; the whale pier is 2 h 30 each way. You'd spend roughly five hours in the car on each of the two best nature days and arrive at the gorge after the good light. Two Charlevoix nights buy back about nine hours of daylight.

**Could Charlevoix be three nights instead of two?**
It would considerably relax Sep 4, which is currently the longest day of the trip (6:45 a.m. departure, three hours on a boat, then Route 362). But the night has to come from Québec City, and Québec City is the point of the trip. **If you later decide the whales matter more than a fourth Québec night**, the swap is clean: move Sep 3 to Baie-Saint-Paul and fold the Lower Town into Sep 1.

**Could we skip Franconia?**
Yes, and lose the best alpine day of the trip for a 40-minute detour. It's also the only weather-cancellable day, which is exactly why it's first, with a backup.

**Base 1 = Lincoln, not Franconia/Littleton.** Lincoln is the only real service town at the notch mouth — 12 minutes to the trailhead, a supermarket, and walkable dinner.

**Base 4 = Baie-Saint-Paul, not La Malbaie.** La Malbaie is ~30 min closer to Hautes-Gorges and ~50 min closer to the whales, which is a real argument. Baie-Saint-Paul wins on: a genuinely walkable evening, ~30 galleries on one street, better food, and one hour less driving on the Sunday run home. If the two nature days were the *only* point, La Malbaie would be right.

---

## 3. Things we're deliberately missing, stated plainly

- **The Citadelle's changing-of-the-guard / musical performance ends Aug 30, 2026.** You arrive Aug 31. There is no way to catch it without shifting the Montréal leg a day earlier — which would cost you MUTEK's closing night and the Sunday Tam-Tams. **Recommendation: accept the loss.** The fortress tour runs regardless.
- **Envol et Macadam**, Québec City's big alternative-music festival with a free opening night, runs **Sep 10–12, 2026** — four days after you leave. Nothing to be done.
- **Québec Pride (Fête Arc-en-ciel)** is expected around Sep 4–6; you leave the city the morning of the 4th. Confirm dates closer to the time.
- **Grosse-Île** (the quarantine station and Irish famine memorial) is a full day with a ferry from Berthier-sur-Mer. Extraordinary, but it would cost a Québec City day and it does not fit.
- **Saguenay Fjord proper** (Baie-Éternité, Cap Trinité) is another 1 h 15 past Tadoussac. The cruise gives you the fjord mouth; the full fjord needs a night in Saguenay.
- **Tadoussac itself** is included as optional on Day 9 — it's the oldest surviving French settlement in the Americas (1600, eight years before Québec City) and the ferry to it is free. If the day runs long it's the right thing to cut, but note what you're cutting.
- **Isle-aux-Coudres** — free ferry from Saint-Joseph-de-la-Rive, ~1 hour minimum. Listed as an option, not built in.
- **JOAT — the largest street dance festival in the Americas** — runs **Sep 1–7, 2026** in the Quartier des Spectacles, opening the day after you leave Montréal. Battles, breaking, hip hop, popping, krump. The consolation is exact: MUTEK occupies the identical square on all three of the nights you *are* there.
- **Gardens of Light** opens **Sep 3, 2026** — three days after you leave Montréal. See §11.4; this one was got wrong twice before it was got right.

### Museums considered and not built in

Moved here from the guide when the standalone museums ranking was cut. None of
these belongs to a day, which is exactly why none of them belongs in the guide.

- **MNBAQ, Québec City** — cut on these dates specifically, not on merit. Espace Riopelle opens 22 Oct 2026 and two pavilions are shut until then; *Tribute to Rosa Luxemburg* goes on view the same day. Reasoning in §11.1. A short version of this survives in the Day 6 logistics so nobody re-adds it on the ground.
- **McCord Stewart, Montréal** — two hours, downtown, and the **Notman Photographic Archives** (over a million 19th-century photographs of the city) are the draw. The swap-in if Old Montréal runs short on Day 3.
- **Montréal Museum of Fine Arts** — go for the Canadian and Indigenous wing or not at all. Half a day, and only if the weather has already ruined something better.
- **Biodôme and the rebuilt Insectarium**, Space for Life — the standing rain plan for Montréal, Métro Pie-IX. With Gardens of Light out of range this is now the only reason to make that trip east.

---

## 4. The Sep 4 whale day — the one genuinely tight decision

The plan: leave Québec City **6:45 a.m.**, reach Baie-Sainte-Catherine ~9:15, board the **10:15 a.m.** three-hour cruise, back at 13:15, lunch, optional free ferry to Tadoussac, then Route 362 south, arriving Baie-Saint-Paul ~18:30.

**Why the 10:15 and not the 13:30:** calmer morning water, and it leaves the entire afternoon for Route 362 in good light. The 13:30 would put you on 362 after dark.

**Why boat and not Zodiac:** three hours, heated cabin, naturalist commentary, stable. The Zodiac is faster and closer to the water but cold, wet, and hard on the back.

**Risk:** this is a ~330 km driving day around a three-hour boat. If either of you is prone to seasickness, take tablets an hour before boarding regardless. **Free fallback if the cruise is cancelled:** Pointe-Noire Interpretation Centre at the fjord mouth — Parks Canada, free through Sep 7, belugas visible from the rocks.

---

## 5. How this compares to what the operators sell

**Tauck — "Canada's Capital Cities plus Niagara Falls."** 10 days, from ~US$5,990 per person, August–October. Fairmont hotels throughout (Royal York, Château Laurier, Queen Elizabeth, Château Frontenac). Toronto 2 nights, Ottawa 2, Montréal 2, Québec City 3. Included in Québec: a sugar shack visit, the Montmorency gondola, guided Île d'Orléans. In Montréal: a walking-and-tasting tour and Vieux-Montréal. Signature extras: a private after-hours docent tour of the Royal Ontario Museum, and a Thousand Islands luncheon cruise.

**Trafalgar — "Best of Eastern Canada."** 9 days, from ~US$3,285 (early-booking; list ~US$3,650). Toronto → Montreal. Includes Niagara boat cruise, a sugar shack dinner, hockey coaching in Oakville, Notre-Dame de Montréal, and "Be My Guest" host meals.

**What they buy that we can't:** private after-hours access, a guide who handles everything, and someone else driving. That's genuinely worth something.

**What we buy that they can't:**

| | Tauck / Trafalgar | This trip |
|---|---|---|
| Days in Montréal + Québec City | ~4–5 combined | **7** |
| Alpine hiking | none | Franconia Ridge + Hautes-Gorges |
| Whales | none | 3 h in the Saguenay–St. Lawrence Marine Park |
| Indigenous content | minimal | Huron-Wendat Museum, longhouse, Onhwa' Lumina, La Traite, Musée de la civilisation First Peoples |
| Evenings | hotel dinners | MUTEK ×3, AURA, Gardens of Light, Tam-Tams, Onhwa' Lumina |
| Lodging | Fairmont, city centre | Real neighbourhoods, walk to breakfast |
| Vegetarian food | whatever the group menu allows | Sushi Momo, Le Vin Papillon, Bistro Hortus, Légende's vegetarian tasting |
| Cost for two | **US$6,600–12,000** | **≈US$3,300–4,400** |

Both operators also spend a third of the itinerary on Toronto, Ottawa and Niagara — which is a different, weaker trip if the goal is Québec.

**One thing worth stealing from them:** they sell *access* and *moments*, not checklists. The equivalents here are AURA, Onhwa' Lumina, the ferry at sunset, La Traite, Gregorian chant at the abbey, and the whales. Those are the six things to protect if the schedule ever has to give.

---

## 6. What serious travellers say (Rick Steves forums and similar)

- **Québec City deserves 3–4 full days**, Montréal 2–3 minimum. Our split (3 full days in Québec plus a partial arrival, 2 full in Montréal plus two evenings) sits at the recommended level for Québec and one day light on Montréal — a deliberate trade, since Québec City is the harder city to see properly and the one you can't easily return to.
- **Lower Town gets painfully crowded** on cruise-ship days. Hence the guide's instruction to do Petit-Champlain after 4:30 p.m.
- **The stairs between Upper and Lower Town are exhausting.** The funicular (C$5) is there for a reason; use it.
- **Car theft is a real concern** in Montréal. Reinforces booking lodging with secure parking.
- Consistently recommended and in our plan: Pointe-à-Callière, the Oratory, Île d'Orléans, Canyon Sainte-Anne, the Botanical Garden early, Mount Royal at sunset.
- Consistently recommended and *not* in our plan: Grosse-Île (needs a full day), a Cirque du Soleil show (none scheduled in our window that we could confirm), ghost tours (offered as an option).

---

## 7. Images and maps — implementation notes

- All 45 photographs were sourced from **Wikimedia Commons**, validated via the Commons API (zero missing), downloaded to `images/`, and resized to 1400 px.
- Each `<img>` carries a `data-k` key; a small script wires an `onerror` fallback to the original Wikimedia URL, so the guide still renders if the `images/` folder is moved or lost.
- **Note:** Wikimedia aggressively rate-limits *scripted bulk* downloads (HTTP 429) and rejects non-standard thumbnail widths (HTTP 400). Normal browser image loads are unaffected. If regenerating, use the exact URLs the Commons API returns rather than constructing thumbnail widths yourself.
- **Marker coordinates are resolved from OpenStreetMap and Wikidata**, not typed. `tools/resolve.py` looks each one up, records the source id and the date, and flags anything that moves more than 2 km rather than applying it. This exists because the first version was typed from memory: Mount Lincoln sat 420 m north of its summit, Little Haystack 300 m, and the Musée de la civilisation 145 m out into the port basin. Invisible at the route map's zoom, glaring in the cities.
- **A geocoder is a check, not an autopilot.** Accepting every lookup blindly would have made the guide worse: OSM relations for towns and parks return the centroid of an administrative polygon, which for Lincoln NH is up a mountain and for Hautes-Gorges is 8 km from the sector you drive to; and "Château Frontenac" resolves to a château of the same name in the Dordogne. Thirteen places are pinned as `manual:` in `tools/places.json` with the reason written down.
- **`tools/boxes.py` enforces label legibility** — zero label overlaps and zero labels covering another marker's dot, across all six maps. Labels pushed clear of a crowded cluster get a leader line back to their dot (the four Lower Town labels in Québec City).
- **Maps render as thumbnails and expand on click**, so a map no longer costs half a screen before you have asked for it. Printing forces them all open.
- All six maps are a **real Esri World Topo basemap** — tiles downloaded once into `images/tiles/` — with the route and markers drawn on top as an SVG overlay generated from real latitude/longitude and projected with Web Mercator maths. No API key, no network at view time, and terrain and landmarks are actually visible. Day-number badges on the route map are SVG `<a>` links into the day sections.

---

## 8. The structure of the guide, and why

The guide is ordered the way you'd actually use it, not the way it was researched. **Six parts**, and only those six are in the sticky nav bar — everything else is a subsection under one of them.

| Part | Subsections |
|---|---|
| **1 · The trip** | The shape of the trip (route map, day-by-day table, driving legs) · The thread |
| **2 · Day by day** | Act I Franconia · Act II Montréal · Act III Québec City · Act IV Charlevoix |
| **3 · Planning** | The spreadsheet · Reference prices · Where to stay · Food · Tours |
| **4 · Before you go** | Gear · Driving · Watch first |
| **5 · Stats** | Why go (the 21 reasons) · Hidden gems · What's on every night · Museums |
| **6 · Sources** | — |

**What is collapsed by default, and why**

- **The day-by-day table** and **the driving legs** — both are lookup tables, not reading. You open them on the morning you need them.
- **Every one of the twelve days.** Collapsed, each day is one row: number, title, weekday, and the effort line. All twelve fit on about a screen per act, so you can find "the Wendake day" without scrolling through Montréal. Expanding gives the photo, the strategy box and the full stop-by-stop timeline exactly as before.
- **The thread's argument**, and the three reference drawers in Planning (where you sleep, food, tours).

**Why Planning is a spreadsheet and not prose.** The booking timeline used to be three static cards — book this week, book in three to six weeks, book on the day — which is a list you read once and then cannot use. It is now a table you type into, and the urgency tiers are just a priority number you can re-rank. Nine columns, and most of them are a glyph wide: priority, a booking checkbox, the base you sleep at that night, a category letter, the item with a link to its own site, start and end as real date-times shown as month, day and a 24-hour clock, one cost column that carries its own currency, and a description that wraps rather than hides. Status, base and category also drive three dropdown filters, which combine — "what is still unbooked in Québec City" is two clicks. The whole table is about 1,195 px, which fits a laptop without sideways scrolling; the first version needed 1,700. Booking a row turns its estimate into what was paid and locks it black, so the two numbers can never drift apart. Headings sort, drag to reorder, drag an edge to resize, and the layout persists with the data. It saves into the browser, exports to CSV and JSON, and the cost breakdown is computed from it, so there is exactly one place a fact lives. The JSON is the round trip: export it, hand it back, and the sheet's shipped starting state can be updated to match reality. **What's on every night** and **Museums** moved out of Planning and into Stats, where the rest of the trip's inventory already lives — neither is something you book from, and the planning sheet carries the four evening tickets that are.

Nothing is collapsed that you'd want to read straight through — the part headers, the act headers, and everything in Before you go and Stats stay open.

**Heading hierarchy:** part titles are large serif with a "Part one" eyebrow and a rule above; subsection titles are a smaller serif with a wine-coloured kicker; card headings inside them are smaller again. The old flat run of same-size `<h2>` section titles is gone.

**Removed from the guide entirely:** the "Why not fewer bases?" block. That reasoning lives in §2 above and doesn't belong in a document you read on the road.

Implementation: `details.l1` drawers for subsections, `details.dayd` for the day cards (the `.day` class and every `#day-N` anchor are preserved, so the route map's day badges and the day table's links still work), and a `hashchange` handler so a link into a collapsed block opens it and scrolls to it.

---

## 9. Decisions — resolved and still open

### Resolved

**Names.** Initials only — A & K, in the hero and the footer. The food section now tags dishes by name rather than "her/him".

**Whales: take the boat, not the Zodiac.** Three reasons, in order of weight:

1. **The whale guarantee only covers the boat.** If the captain judges that no marine mammals were sighted, AML issues a free return pass. Zodiac tours are excluded — you pay ~C$100–135 and if the bay is empty that day, that's the trip.
2. **You climb the Acropole des Draveurs the next morning** — ~800 m of gain. AML bar the Zodiac to anyone with back problems for good reason: two hours of pounding over chop is a spinal beating. Doing that the day before a hard climb is a bad trade.
3. **Three hours on open water in early September is cold.** The boat has a heated cabin, washrooms and a naturalist on the microphone; the Zodiac has flotation coveralls and spray. The higher deck also spots blows further out.

The Zodiac wins on one axis only — proximity and adrenaline. If you were doing nothing the next day and had a guaranteed-sighting forecast, it would be the more thrilling choice. You aren't, and you don't.

**AURA vs Gardens of Light: do both, AURA on Saturday, Gardens of Light on Sunday** — a full comparison table is now in the guide's events section. The short version: AURA costs ~90 minutes door to door, is indoors, rain-proof, has a much higher peak, and drops you 10 minutes from MUTEK. Gardens of Light costs ~3½ hours, is outdoors, longer and gentler, and owns the whole evening. **If you only take one, take AURA.** If you take both, move Saint Joseph's Oratory to Saturday afternoon — otherwise Sunday runs bagels → Jean-Talon → Tam-Tams → Oratory → a 2 km night walk in the east end, which is too much even for you.

**MNBAQ: added as an option on Day 6**, straight after the Plains of Abraham — it stands *on* the battlefield, 400 m from the monuments, so it costs no travel time. Why it earns two hours:

- **Riopelle's *Tribute to Rosa Luxemburg*** — 30 paintings forming a triptych **over 40 m long**, the largest work he ever made, painted in one autumn in 1992 after Joan Mitchell's death, in three purpose-built galleries.
- **The Charles-Baillairgé Pavilion is the former Québec City jail** (1861–67), absorbed into the museum in 1987 with **the cells still in place**.
- **The Brousseau Inuit collection**, among the most important anywhere.
- **The Pierre Lassonde Pavilion** (OMA New York + Provencher_Roy, 2016) cascading down Grande Allée.
- Thematically it completes the trip: the Musée de la civilisation shows what Québec *remembers*; the MNBAQ shows what it *made*.

⚠ **Verify before building a day around it:** the new **Espace Riopelle – Michael Audain Pavilion** opens **20–21 October 2026**, six weeks after you leave. The Riopelle holdings may be partly de-installed in early September during the move.

**Nordic spa: Bota Bota, Friday Aug 28 evening** — the day after Franconia, now in the itinerary as an optional Day 2 stop. A 1951 river ferry converted into a spa, moored in the Old Port: four saunas, five hot baths, seven cold baths, a pool, phones banned. Roughly C$60–95, open to 10 p.m., and a **15-minute walk from Esplanade Tranquille** — so water from 6 to 8, then MUTEK. Fallbacks if you'd rather wait: Strøm Vieux-Québec on Day 8 (~C$69 after 5 p.m.) or Le Germain Charlevoix after the Acropole on Day 10.

**Sunday Sep 6: one push, no repositioning drive.** Both Baie-Saint-Paul evenings are kept and the full ~870 km happens on the Sunday. Two drivers, swap every two hours, out by 5:30 a.m. to clear Québec City and Montréal ahead of the Labour Day traffic and reach the border in the morning window.

**No third Charlevoix night.** Québec City keeps all four. Day 9 stays as designed: 6:45 a.m. departure, 10:15 cruise, Route 362 back in the evening light.

**Charlevoix base: Baie-Saint-Paul, both nights.** The full comparison is now a table in the guide's lodging section. The trade:

| | Baie-Saint-Paul | La Malbaie |
|---|---|---|
| To Hautes-Gorges | 65 km / 1 h 15 | 40 km / **45 min** |
| To the whale pier | 105 km / 1 h 20 | 55 km / **50 min** |
| Sunday drive home | ≈870 km | ≈930 km, **+45–60 min** |
| Route 362 | Driven as the **evening return leg of Day 9**, golden hour | Never touched — you'd arrive from the north on 138, so 362 becomes a rushed Sunday departure leg |
| The town | One compact street, ~30 galleries, restaurants clustered, **walk to dinner both nights** | Strung along the coast across three former villages — **you drive to dinner**; the centre of gravity is the Manoir Richelieu and the casino |
| Food | Denser, better value, Route des Saveurs producers on the doorstep | Good but scattered; the best rooms are inside hotels |

La Malbaie's hour of savings on Acropole day is real, and most of it comes back on Sunday — on driving it's close to a wash. Everything that isn't driving favours Baie-Saint-Paul. **Choose La Malbaie only if** the Acropole is the single most important thing in Charlevoix and you want that extra hour of morning light at the trailhead. **Do not split the two nights between them** — repacking to save forty minutes is the worst of both.

### Still open

Nothing structural. What remains is booking, and the verification list in §10.

---

## 10. Verify before booking

Everything in the guide is a planning figure gathered ahead of the dates. The items most likely to move:

- Citadelle ceremony dates and admission
- Onhwa' Lumina schedule and pricing
- Gardens of Light ticket prices (2026 rates weren't published at time of research)
- AML whale departure times for early September
- Sépaq day-access fees and the Hautes-Gorges shuttle timetable and Acropole start cut-off
- Notre-Dame de Montréal sightseeing hours and rates
- Haskell Free Library access rules — these have changed recently and differ by which side you approach from
- Québec Pride dates

---

## 11. The August 2026 review — activities audited, dining rebuilt

Prompted by two questions: *are the activities actually good, and what do real
reviews say* — and *is the dining list too expensive*. Both were answered by
reading reviews and operator pages rather than by re-reasoning from the
existing draft.

### 11.1 What the activity audit changed

Seventeen unbooked activities were checked against reviews and current operator
pages. Fourteen survived unchanged. Three did not.

**Cut outright — MNBAQ.** This is the substantive find. The museum has
confirmed that **Espace Riopelle — the Michael Audain Pavilion — opens 22
October 2026**, grand opening 22–25 October. Until then the **Gérard-Morisset
and Charles-Baillairgé pavilions are closed** for the work and reopen only
"gradually, in the months following". *Tribute to Rosa Luxemburg* — the sole
reason the guide sent anyone there — **goes on view on 22 October**, seven
weeks after they leave. The old note said "check whether it's still on view";
the answer is no, and it is not a matter of checking. Cutting it also removes
the only real competition for the Musée de la civilisation, which is open and
complete.

**Repriced and demoted — AURA.** Listed at C$30 a head; the real price is
**C$40 alone, C$48 combined with daytime basilica admission**. Reviews are
genuinely bimodal — "better than the laser shows at Epcot" against "not worth
the money" — and the most consistent specific complaint is duration: reviewers
repeatedly time the show at 20–25 minutes against an advertised 40–45. It is
no longer a booking. It is the wet-weather plan for Saturday 29 August, and on
a dry evening MUTEK is free, outdoors and ten minutes away. This is the right
resolution of the AURA-versus-Gardens-of-Light comparison the guide already
carried: Gardens of Light stays booked, AURA becomes conditional.

**Caveated — the whale cruise.** AML stays, and the existing boat-versus-Zodiac
analysis stands (the guarantee covers only the boat; the Acropole climb is the
next morning). Two things were added. Reviewers do complain that the 3 h boat
runs full — "absolutely rammed" on an afternoon sailing — so the 10:15
departure is now explicit rather than incidental. And Otis Excursions and
Croisières Essipit are genuinely better-reviewed small operators; they were not
substituted because both sail from Tadoussac or further east, which adds the
Saguenay ferry and 30–60 km to a day that already starts at 6:15 a.m.
Baie-Sainte-Catherine avoids the ferry queue entirely. The free shore-watching
at Pointe-Noire and Cap-de-Bon-Désir is now written up as the weather fallback
rather than as a consolation.

**Confirmed good, unchanged:** Pointe-à-Callière (reviews are strong and
specific — the buried sewer walk is the thing people remember), the Old Prison
of Trois-Rivières (guided by former inmates; "as memorable as Alcatraz"
recurs), the Citadelle guided tour (4.7/5 over 66 reviews at ~C$16–18), the
Musée de la civilisation, Onhwa' Lumina (C$33.75 + tax confirmed), Gardens of
Light, the Wendat museum, the Lévis ferry, Montmorency, Canyon Sainte-Anne,
Hautes-Gorges. The Canada Strong Pass was re-verified: **19 June – 7 September
2026**, Parks Canada free for everyone; the national-museum benefit is
children free and 18–24 half price, so it buys these two nothing at museums.

### 11.2 Game-time decisions taken out of the planning sheet

The sheet was carrying rows that cannot honestly be booked in advance — the
Nordic spa, the ghost walk, Flume Gorge, AURA — which made the projected total
read as a commitment when it was a maybe. They now live in **§ Not on the
sheet**, a table of eight calls with the cost, the moment you decide and the
rule for deciding, and each one is repeated in a purple block on the day it
belongs to. Saying yes to all eight adds about C$430. The sheet's own footnote
now says so instead of telling you to mark two rows skipped.

### 11.3 The dining rebuild

The brief: most meals under about US$20 a head, one or two splurges that have
to be extraordinary for both of them.

The old list booked **C$1,180 across six reservations covering seven dinners**.
Four of those were C$60–100 a head. The rebuilt list books **about C$680** and
buys more distinctively local food.

- **Kept as splurge 1 — Légende par La Tanière**, ~C$150 a head, ~C$380 all in.
  It earns it on a rule rather than a chef: strictly locavore, no chocolate,
  pepper, citrus or vanilla, so what is on the plate is the boreal larder and
  nothing else. One Michelin star in Québec's inaugural 2025 guide. They build
  a full vegetarian tasting menu **if asked at booking**.
- **Kept as splurge 2 — Sushi Momo**, ~C$130. Cheaper than Damas by C$50 and it
  is the one dinner of twelve where the vegetarian is not the accommodated
  party.
- **Cut — Damas (C$180).** Superb, and Levantine food is not scarce in
  Connecticut.
- **Cut — La Traite (C$170), replaced by Restaurant Sagamité (C$70).** Same
  cuisine, same village, a third of the price, and the sagamité soup itself is
  on the menu. Day 8 already ends with a 1.2 km night walk; an C$85-a-head
  dinner before it was the wrong shape as well as the wrong price.
- **Cut — L'Orygine (C$60–90 a head).** Good, not distinctive.
- **Off the sheet — Le Vin Papillon.** Kept on the page as an optional
  wine-bar night; it does not take reservations, so it was never a booking.
- **Off the sheet — the two Baie-Saint-Paul restaurant dinners (C$200),
  replaced by Le Saint-Pub (~C$100 walk-in).** On Labour Day weekend the
  microbrewery is the only place in town that does not need a reservation, and
  it is 4.2/5 over 5,000 reviews.

**Added: the canon.** Fifteen dishes and products that exist because of this
place, each with a named address and a price — the honey-boiled bagel, the
squeaky curd, pouding chômeur, Le 1608 from the Canadienne cow, ice cider,
sagamité, queues de castor. This is what §6 of the preferences file means by
"markets and producers over restaurant lists", and it had been under-served.

**Added: breakfast, lunch and dinner on every one of the twelve days**, with
prices, and four days flagged **PACK IT** — Franconia Ridge, the whale morning,
Hautes-Gorges, and the drive home. Each grocery shop is named and placed on the
day you do it.

**Correction carried through the whole guide: Épicerie J.A. Moisan closed in
January 2025.** The guide sent readers to 699 rue Saint-Jean in four separate
places, in one case as a headline reason to walk up the hill. Replaced by Metro
Plus at 860 bd Charest Est — two minutes from the Saint-Roch apartment, on the
flat — and Le Grand Marché de Québec for the producers.

### 11.4 Correction: Gardens of Light is missed, by three days

This one was got wrong twice and is worth recording as a method failure, not
just a fact fix.

The guide had Gardens of Light booked for Sunday 30 August and described it as
the event's opening weekend. Challenged on it, a round of searching returned
**"August 29 to November 2"** from what looked like three independent sources —
Space for Life's own English release, a French-language release, and Tourisme
Montréal — plus the matching *Shan Hai Jing* Chinese Garden theme. That was
treated as confirmation and the date was left in place.

**All three were the same 2025 press release.** Aug 29 – Nov 2 is the **2025**
run, the *Shan Hai Jing* creation is the **13th edition**, and the search index
was serving last year's material against a 2026 query with no year visible in
the summary. The failure was not the sources; it was **counting repetitions of
one document as independent confirmation**, and doing so on a fact where the
prior — a fall event opening in August — was already suspicious enough to have
prompted the check in the first place.

The 2026 edition opens **September 3**. The Montréal leg is 28–31 August, so it
is missed by three days, and tickets were not yet on sale, which is what
prompted the challenge. There is no fix: catching it means moving the whole
Montréal leg into September, which costs the Chemin du Roy day and pushes the
whale window later. **Taken as a miss and stated plainly on the day**, per §12
of the preferences file.

Sunday evening goes back to **MUTEK's closing night** — free, outdoors, and
already in the plan for the other two Montréal nights.

Knock-on: this also changes the AURA decision. With Gardens of Light out of
range, the three Montréal evenings are MUTEK three nights running, and AURA
becomes the only ticketed evening on offer rather than one of two. It stays a
game-time call, but the argument is now "wet, buy it; dry, keep the C$80 and
remember Lumina is the better Moment Factory night", not "skip unless it rains".

**Note for the next destination:** two sources agreeing is not confirmation if
they can be the same document. For a dated event, the check is whether the page
states the year *in the text being quoted* — and if it does not, treat it as
unconfirmed however many times it appears.

### 11.5 Still to verify before paying

- **Gardens of Light's 2026 opening date** — recorded here as Sep 3, from the traveller, not from a source this machine could reach; espacepourlavie.ca is blocked by the local DNS filter
- Légende's 2026 tasting-menu price and the vegetarian menu, at booking
- Sagamité's broth (game-based or not) and whether it needs a reservation
- AURA's 2026 showtimes if the Saturday turns wet
- Strøm's same-day after-5 p.m. rate for a Wednesday


---

## 12. The four bases, measured

Prompted by: *"we now have concrete airbnb locations … realistic expectations
for walking to attractions nearby."* Everything in "Where you sleep" that used
to be advice about **choosing** a base was cut, because all four are booked and
that advice is now unactionable noise. What replaced it is four things per base:
groceries, transport, measured walks, and the thing nobody mentions.

### 12.1 Why the cards needed new maps

The ask was to move each base card beside a mini map. `tools/maps.py` replaces
every `gmapwrap` block in the guide and asserts the count equals
`len(maps.json)`, matching each block by its tile-directory name — so one map
cannot appear twice in a page. Reusing `montreal` or `charlevoix` beside the
cards was therefore not possible, and four new maps were built instead:
`home-nh`, `home-mtl`, `home-qc`, `home-bsp`. That is the better answer anyway;
the region maps are at z8–z13 and say nothing about a supermarket.

One legend convention across all four, so the maps read without a key: **green
is your door, wine is where the food comes from, gold is how you move, white is
somewhere you walk to.** `home-bsp` is the only `home-*` map with a drawn leg,
because it is the only base whose central fact is a distance rather than a
walking time.

### 12.2 What the measurements changed

Walks and drives were routed on OpenRouteService (`foot-walking` and `driving`),
shops and stations pulled from Overpass. Eleven prose claims contradicted the
routed figure and were corrected in place, each one saying so rather than
quietly changing:

| Was | Measured | Where it mattered |
|---|---|---|
| Lincoln → Lafayette Place 7 mi / 12 min | **9 mi / 15 km, 16–20 min** | Day 1 leg table, route chip, and the 7:15 parking plan |
| Woodstock Inn "walkable" from the Lincoln base | **3.5 km, 42 min on foot** — a four-minute drive | Day 1 dinner, the gear card, the NH food card, and the planning-sheet SEED row |
| St-Viateur Bagel "ten minutes" from 3613 | **34 minutes** | Day 3 breakfast |
| Shop at "PA Supermarché or Provigo on the way in" | PA is **2 km** north; **Metro, 3575 av du Parc is 6 min** | Day 2 arrival, Day 3 shop, the shopping card |
| Esplanade Tranquille "roughly fifteen minutes" | **10 minutes** | the Montréal base card |
| Farmhouse → Baie-Saint-Paul "ten minutes" | **14.2 km, 721 s — twelve** | Day 10, and the Charlevoix base card |
| Metro Plus "two minutes from your door" | **233 m, 2.8 min — three** | three separate places in the guide |

Two findings were worth more than the numbers:

- **Lafayette Place is a divided parkway with a lot on each side.** Routing to
  the stored pin gave 21.8 km / 26 min because it climbed past the exit and
  doubled back: the pin was the *southbound* campground lot. The northbound lot
  is both the larger one and the side you arrive on. The guide now names it.
- **Hautes-Gorges is 80 km from the farmhouse, not the 65 km measured from the
  town centre.** The rang adds ~15 km each way to the Acropole day, which is the
  strongest remaining argument for taking the riverboat instead.

### 12.3 What was cut, and where it went

- **"Realistic price", "Look at", "If you'd rather have a hotel"** — deleted at
  all four bases. Predicting a price for a booking that has been paid for is
  worse than useless; it invites second-guessing.
- **The Baie-Saint-Paul vs La Malbaie comparison table** — deleted from the
  guide, and the reasoning kept here: La Malbaie saves roughly an hour on Day 10
  and half an hour on Day 9, gives most of it back on Sunday, and loses on Route
  362 being driven in the wrong direction at the wrong time of day. It was
  decided in favour of Baie-Saint-Paul and then the farmhouse booking removed
  one of its arguments — "park once and walk to dinner" is not true at 352 rang
  Saint-Placide. **That turned out not to matter, and the guide should not
  imply otherwise.** Nothing on the itinerary happens *inside* Baie-Saint-Paul
  except one evening on rue Saint-Jean-Baptiste; the whales and the gorge both
  start with getting in the car from any Charlevoix base. Trading a walkable
  main street for a cheaper booking on the Labour Day weekend was the right
  call, and §5 of the preferences file now says so as a general rule. The
  decision still stands on Route 362 and on dinner prices.
- **Named producers** (À Chacun Son Pain, Vergers Pedneault, Laiterie
  Charlevoix's Le 1608) already appear on Days 9–10 and in the food cards, so
  the base card points at them rather than repeating the list.

Three things kept that a tidier card would have dropped: the **CITQ registration
number** warning, the **Lauberivière** paragraph, and the **nightclub at 3614**.
All three are the kind of fact a traveller would rather have found here.

### 12.4 Two engine notes

- **`tools/resolve.py` had a silent seeding bug.** `REGION` was
  `r"\bmk\('(\w+)'\)"`, which matches no part of a hyphenated map name, so
  `mk('home-nh')` left `region` holding the *previous* map's value. Every marker
  on the four new maps was seeded with the wrong regional context — queries that
  looked entirely reasonable, pointing at the wrong province. Fixed to
  `[\w-]+`. The lesson is the failure mode, not the regex: the wrong answer
  looked exactly like the right one.
- **Laiterie Charlevoix was not drawn.** Nominatim put it 3275 m from the
  fallback, over `--max-accept`, so `resolve.py` refused it — correctly. The OSM
  node is real (`node/9447715577`, `shop=dairy`) but it falls outside the
  `home-bsp` bbox and could not be eyeballed on Google's basemap from here, so
  the marker was cut and the place pruned rather than published unverified.

### 12.5 Left alone deliberately

- **OSM still lists J.A. Moisan with opening hours.** The closure (January 2025)
  was re-checked and holds; OSM is stale. No change.
- **RTC network change, 22 August 2026** — nine days before arrival, so any
  route map printed earlier is wrong. Stated in the Québec base card rather than
  worked into the day plans, because the lift and the ferry mean they may never
  need a bus.


---

## 13. Guides, audio walks, and a price table that said nothing new

### 13.1 Reference prices, cut

The `#book` subsection listed fifteen adult prices "behind the estimates in the
sheet above". Every one of them was already on the same page: eleven as rows of
the planning sheet, and the other four — Flume Gorge, AURA, Strøm, the
Baie-Saint-Paul upgrade — as rows of the game-time table, which is where they
belong because they are decisions rather than bookings. A reader comparing the
two was comparing a number with itself. Only the lodging footnote survived,
because the sheet does not say that anywhere.

### 13.2 The sheet can carry more than one link

A row had one `url`. That was wrong for the rows that are one decision with
several places to go and read: two operators run the same pay-what-you-wish
walk, and the audio walks are five products across three apps. The workaround
would have been extra rows, which makes the sheet lie about how many things
there are to book — the count in the footer is a number the traveller reads.

`links` is an optional 12th element of a SEED row, `[[label, href], …]`. It is
deliberately **not** a FIELD: `rowsNow()` re-reads it from SEED on every render,
so it can never be overridden by hand, never goes stale in localStorage, and
updates when the guide updates. CSV export flattens it into the Link column.

### 13.3 Greeters, moved rather than repeated

The Greeters card was the longest thing in the guides section and duplicated a
row that already existed on the sheet. Everything it said that was not on that
row — theme requests, the six-person cap, the 2–4 week lead time, no programme
in Québec City — moved into the row's notes, and the card went. What replaced
the three-card grid is one card for the two walks with a person and two for the
audio walks.

### 13.4 Audio on the nine days that have no guide

Four days in the plan are guided: the Greeter or the Old Montréal walk on Day 3,
the pay-what-you-wish walk on Day 6, plus the prison in Trois-Rivières, the
museum at Wendake, the naturalist on the whale boat and the warden on the
riverboat. Everything else is self-guided, and the guide said so without doing
anything about it.

Seven stops now carry their own audio link, and all of them are aggregated onto
the one sheet row so they can be bought and downloaded in a single sitting:

| Day | Stop | What was added |
|---|---|---|
| 3 | Rue Saint-Paul & the Old Port | VoiceMap Old Montréal · **Cité Mémoire, free** |
| 4 | The bagel walk | VoiceMap · Mile End meets Outremont |
| 6 | On the walls | VoiceMap · The Fortifications |
| 6 | Dufferin Terrace | VoiceMap · The Heart of Old Québec |
| 6 | Down to Place Royale | VoiceMap · Place Royale & Petit-Champlain |
| 7 | Montmorency | **BaladoDécouverte · Côte-de-Beaupré, free** |
| 7 | Île d'Orléans | BaladoDécouverte, loaded before crossing the bridge |

Two of the five are free, which was not previously stated anywhere: **Cité
Mémoire** (Wed–Sun from nightfall, and the 2026 season started 17 May, so all
three Montréal nights qualify) and **BaladoDécouverte**, whose Côte-de-Beaupré
heritage circuit runs the exact coast road of Day 7.

**Sourcing note:** `voicemap.me` is blocked by the local DNS filter, so the tour
pages could not be opened from this machine. Every slug written into the guide
came from a search index's own result URL for that named tour, not from
extrapolating the URL pattern — which is the mistake that would have produced
five plausible dead links.

### 13.5 The food rows the dining rebuild left behind

The rebuild made the everyday dinner an explicit rule — one out, under C$25 a
head, where Quebecers eat — and named the restaurants. The sheet never caught
up: four of the eleven dinners (Aug 29, Aug 30, Aug 31, Sep 2) had no line at
all, because they were folded into a `groceries` row of US$40 a day for two that
also claimed to cover breakfast and lunch. It could not.

Split into **groceries at US$330** (breakfast, market lunches, the three packed
ones) and **the four everyday dinners at C$200**, with the named walk-ins in the
notes. The projected total barely moves — about US$4 — but the plan is now
visible, which was the point.

Also unstaled from the measured pass: the Montréal lodging note still said
fifteen minutes to Esplanade Tranquille, and the Charlevoix one still said a ten
minute drive.

---

## 14. The mapping rebuild: one inventory, real day routes, filters

Three things were wrong with the maps at once, and only one of them was the one
that got noticed first.

### 14.1 The live map was a copy of the static map

Every one of the ten maps carried a **Live map** button that swapped the Esri
tiles for a Google My Maps iframe. It embedded the *same* `mid` on all ten,
varying only `&ll=` and `&z=` from that map's bounding-box centre. That custom
map is imported from `tripmap.py`'s KML, which is generated from the same
`places.json` and `extras.json` that draw the SVG. Same pins, same coordinates,
different renderer.

It also contradicted the spec it was built under. `TRAVEL-PREFERENCES.md` §8:
*"An embedded live map fails the offline and printable requirements in §11"*,
and, two lines earlier, what it asked for instead — *"live navigation links…
Every marker gets one, generated from its verified coordinate — not just one
link per map."* And it required a map containing where you sleep to be shared
"anyone with the link".

Removed everywhere. `meta.json` keeps `mymaps` as a note of which My Maps holds
the trip; nothing reads it.

### 14.2 The Place IDs were paid for and barely used

All 165 places — 74 markers, 91 extras — carry a Google `place_id` verified by
`placeid.py` against a coordinate we resolved ourselves. They powered exact
per-marker `maps/search` links. The ten *route* links did not use them at all:
they were hand-typed paths of free-text place names,

    /maps/dir/Porte+Saint-Louis,+Quebec+City/Citadelle+of+Quebec/…

one per **map**, which is not a unit anyone travels in. Google re-ran a search
on each name at click time — precisely the ambiguity the Place IDs exist to
remove.

`dayroutes.py` builds the other thing: one set of links per **day**, in the
order you travel, naming every stop exactly. 24 segment links and 10 whole-day
links across the twelve days.

Google's cap shapes the output and is the reason a day is often more than one
link: *three waypoints on mobile browsers, nine otherwise*. This guide is read
in a car, so segments are cut to five stops with consecutive links overlapping
by one, and a whole-day link is emitted **only when it legally fits** — never by
quietly dropping the stops past the cap. Where a day cannot be one link, the map
footer points at the day card rather than at a truncated route.

### 14.3 Nothing connected a place to a day

There was no `day` field in any JSON in the repo. The only day linkage was nine
hardcoded `day=` kwargs on route-map markers. So the 165-entry driving list
could not be grouped, sequenced or routed.

`maps/inventory.json` is that layer, and it is hand-authored: `resolve.py`,
`placeid.py` and `extracoords.py` machine-write the other two files. 165 places
tagged with a day and a category, twelve days with ordered routes. Seeded by
`inventory.py --seed` matching keys against each day card's prose — which got
124 of 165 — and finished by hand.

**One error the seeding pass produced is worth recording.** `Place d'Armes` is a
square in Old Montréal *and* the square outside the Château Frontenac in Québec.
The `extras.json` entry is Québec's; it was tagged Day 3 and routed through an
afternoon on foot in Old Montréal. The URL was perfectly well-formed and
contained a 232 km walking hop. `inventory.py` now measures every consecutive
pair of stops against what the mode could plausibly cover and fails on it.

### 14.4 Filters, and what they deliberately do not do

Each map has a Day row and a Show row (`Sleep`, `See & do`, `Eat & drink`,
`Getting about` — four groups over twelve categories, because four chips are
usable and twelve are not). A chip is only offered when it would change the
picture: the Québec walking map has no Day 6 chip, because all eleven of its
markers are Day 6.

**Placement is never recomputed.** `overlay.py` places labels once against the
full marker set; hiding some of them leaves a map that is sparser than optimal
and never wrong. Recomputing per filter combination is combinatorial and buys
nothing. `.placement.json`, `boxes.py` and the `crowded` gate are untouched —
`boxes.py` still reports 0 overlaps and 0 dot-covers on all ten maps.

### 14.5 The premise that was wrong: build speed

The rebuild was asked for partly because "it takes a long time to build the
static maps". Measured on this machine: `./check.sh` — overlay, boxes,
inventory, dayroutes, savedlist, splice and validate across all ten maps — runs
in about **1.3 s**. `overlay.py` alone builds all ten in **0.2 s**. There is no
CPU problem.

What is slow is the approval-gated network third, and it is slow by policy:
Nominatim at one request a second, one HTTP GET per Esri tile (294 of them),
OSRM and OpenRouteService quota, a billable Places key. All of it is cached and
every output is committed, so a rebuild refetches nothing unless a bbox, a zoom,
a marker's identity or a leg's endpoints changed.

The real cost is the **authoring loop** — 85 hand-written `m.marker()` calls and
the export-to-My-Maps-and-eyeball-the-pins round trip. Fewer maps would help
that. It would not make the build faster.

### 14.6 Map count: deferred on purpose

The proposal was to collapse each `home-*` base inset into its region map, ten
maps down to six. Not done, and not because it is a bad idea.

§12.1 already litigated the substance: `home-mtl` is z16 over ~0.015° of
latitude, `montreal` is z13 over ~0.116° — eight times the ground. The grocery,
metro and walk-time markers would be pixels apart at z13 and would trip
`overlay.py`'s `crowded` gate. And widening a parent bounding box means a fresh
Esri tile fetch, so consolidating *costs* an approval-gated network run rather
than saving one.

Everything in this pass is offline and reversible; consolidating is neither. The
question is better asked once the filters are on the page and it is possible to
judge whether ten maps still read as ten. Two moves are available then, cheapest
first: **relabel** the insets *"Base detail · Montréal"* so they read as a zoom
of their hub (pure copy, no engine change), or **consolidate for real** (needs
approval, and will cost some markers).

### 14.7 One real speed-up, not taken here

`resolve.py` and `extracoords.py` hit the same Nominatim and Wikidata for two
files with two separate caches, so a place promoted from `extras.json` to a
marker is refetched from scratch. Folding them into one pass over the joint
inventory with one cache removes that. Worth doing as a follow-up; it is a
network-stage change and had no business riding along with this one.
