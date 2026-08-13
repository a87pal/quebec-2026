# -*- coding: utf-8 -*-
"""Markers, routes, legends and captions for Québec & Montréal.

Drawn by tools/overlay.py, which passes in the drawing context `m`.

The lat/lon at each m.marker() call is a FALLBACK ONLY. If the label appears in
places.json, that coordinate wins. Never fix a marker's position by editing the
literal here - correct the pin in Google My Maps and re-run tools/kml.py, fix
the query and re-run tools/resolve.py, or pin it as "manual: <why>".

Label placement is automatic: overlay.py tries positions around each dot and
takes the first that collides with nothing. Pass anchor / dx / dy only to
override a placement that is legal but reads badly, and expect to justify it.

Drivable lines are m.leg(), declared in legs.json and fetched from OSRM by
tools/routes.py, so they follow real roads and carry real distances. The
fallback= vertices are the old hand-drawn approximations, used only until
routes.py has run. The Franconia ridge and the two city walks stay hand-drawn
on purpose - they are a hiking trail and pedestrian routes, and their captions
say they are schematic.
"""


def build(m):
    frag = {}

    # ---------------- ROUTE ----------------
    P, _ = m.mk('route')
    b = []
    b.append(m.leg(P, 'ct-franconia', fallback=[(41.499, -72.900), (41.76, -72.68), (42.10, -72.59), (42.62, -72.58), (43.13, -72.49), (43.65, -72.32), (44.02, -72.02), (44.046, -71.678)]))
    b.append(m.leg(P, 'franconia-abbey', fallback=[(44.046, -71.678), (44.42, -71.85), (44.65, -72.02), (44.80, -72.10), (45.005, -72.100), (45.15, -72.15), (45.281, -72.248)]))
    b.append(m.leg(P, 'abbey-montreal', fallback=[(45.281, -72.248), (45.40, -72.60), (45.47, -73.10), (45.508, -73.567)]))
    b.append(m.leg(P, 'chemin-du-roy', fallback=[(45.508, -73.567), (45.75, -73.30), (46.05, -72.90), (46.343, -72.542), (46.55, -72.15), (46.652, -71.921), (46.75, -71.55), (46.813, -71.208)]))
    b.append(m.leg(P, 'quebec-tadoussac', fallback=[(46.813, -71.208), (47.02, -70.93), (47.25, -70.70), (47.443, -70.501), (47.483, -70.343), (47.573, -70.212), (47.653, -70.152), (47.85, -69.95), (48.02, -69.79), (48.107, -69.731)]))
    b.append(m.leg(P, 'gorge-spur', fallback=[(47.443, -70.501), (47.60, -70.50), (47.75, -70.46), (47.868, -70.421)]))
    b.append(m.leg(P, 'run-home', fallback=[(47.443, -70.501), (46.813, -71.208), (46.343, -72.542), (45.508, -73.567), (45.00, -73.37), (44.70, -73.45), (43.30, -73.60), (42.65, -73.76), (42.10, -73.35), (41.499, -72.900)]))
    b.append(m.marker(P, 41.499, -72.900, "Cheshire, CT", "start · finish", "home", r=10, day=0, daytext="0 · 11"))
    b.append(m.marker(P, 44.046, -71.678, "Lincoln, NH", "2 nights · Franconia", "base", r=11, day=1, daytext="0–1"))
    b.append(m.marker(P, 45.281, -72.248, "St-Benoît-du-Lac", "the abbey", "stop", day=2, daytext="2"))
    b.append(m.marker(P, 45.005, -72.100, "Derby Line", "border", "stop", r=6))
    b.append(m.marker(P, 45.508, -73.567, "MONTRÉAL", "3 nights", "base", r=13, day=2, daytext="2–4"))
    b.append(m.marker(P, 46.343, -72.542, "Trois-Rivières", "", "stop", r=6, day=5, daytext="5"))
    b.append(m.marker(P, 46.652, -71.921, "Deschambault", "", "stop", r=6))
    b.append(m.marker(P, 46.813, -71.208, "QUÉBEC CITY", "4 nights", "base", r=13, day=5, daytext="5–8"))
    b.append(m.marker(P, 47.443, -70.501, "Baie-Saint-Paul", "2 nights", "base", r=11, day=9, daytext="9–10"))
    b.append(m.marker(P, 47.868, -70.421, "Hautes-Gorges", "", "hi", day=10, daytext="10"))
    b.append(m.marker(P, 48.107, -69.731, "Baie-Ste-Catherine", "whales", "ev", day=9, daytext="9"))
    frag['route'] = m.wrap('route', ''.join(b),
        '<span><i class="lg base"></i>Base</span><span><i class="lg hi"></i>Marquee</span><span><i class="lg ev"></i>Whales</span>'
        '<span><i class="lg ln"></i>Outbound</span><span><i class="lg ln bk"></i>Direct run home</span>',
        '<b>The numbered badges are day numbers — click one to jump to that day below.</b> The full loop: Cheshire → Franconia Notch → the abbey → Montréal → the Chemin du Roy → Québec City → Charlevoix → the whales, then straight home.',
        'https://www.google.com/maps/dir/Cheshire,+CT/Lincoln,+NH/Saint-Beno%C3%AEt-du-Lac,+QC/Montreal,+QC/Trois-Rivi%C3%A8res,+QC/Quebec+City,+QC/Baie-Saint-Paul,+QC/Baie-Sainte-Catherine,+QC')

    # ---------------- FRANCONIA ----------------
    # The trail lines are schematic: they are a hiking route, and the public
    # routing service these maps use routes cars.
    P, _ = m.mk('franconia')
    b = []
    b.append(m.route(P, [(44.1417, -71.6816), (44.1401, -71.6757), (44.1387, -71.6688), (44.1392, -71.6598), (44.1402, -71.6508), (44.1413, -71.6437)], w=6))
    b.append(m.route(P, [(44.1413, -71.6437), (44.1445, -71.6440), (44.1483, -71.6444), (44.1545, -71.6449), (44.1605, -71.6446)], "ridge", w=8))
    b.append(m.route(P, [(44.1605, -71.6446), (44.1610, -71.6553), (44.1580, -71.6641), (44.1516, -71.6725), (44.1450, -71.6789), (44.1417, -71.6816)], w=6))
    b.append(m.marker(P, 44.1417, -71.6816, "Lafayette Place trailhead", "park by 7:15 a.m. · free", "base", r=10))
    b.append(m.marker(P, 44.1413, -71.6437, "Little Haystack ≈4,760 ft", "treeline · not on the NH48", "stop"))
    b.append(m.marker(P, 44.1483, -71.6444, "Mt. Lincoln 5,089 ft", "", "stop"))
    b.append(m.marker(P, 44.1605, -71.6446, "Mt. Lafayette 5,249 ft", "high point", "hi", r=11))
    b.append(m.marker(P, 44.1610, -71.6553, "Greenleaf Hut", "water · soup · bail-out", "stop"))
    b.append(m.marker(P, 44.0975, -71.6796, "Flume Gorge Visitor Center", "storm-day plan", "stop"))
    b.append(m.marker(P, 44.1216, -71.6829, "The Basin", "free · 5 min", "stop", r=6))
    b.append(m.marker(P, 44.1786, -71.6897, "Artist's Bluff", "sunrise, Day 2", "stop"))
    b.append(m.marker(P, 44.1719, -71.6976, "Cannon Mtn Tramway", "closed for 2026", "stop", r=6))
    b.append(m.marker(P, 44.0488, -71.6576, "Lincoln", "your base · 36 Lodge Road", "base", r=11))
    frag['franconia'] = m.wrap('franconia', ''.join(b),
        '<span><i class="lg base"></i>Base / trailhead</span><span><i class="lg hi"></i>High point</span>'
        '<span><i class="lg ln"></i>Trail</span><span><i class="lg ln rg"></i>Above treeline</span>',
        'The loop runs clockwise: up Falling Waters, 1.7 miles along the open crest, down Greenleaf and the Old Bridle Path. The trail lines are schematic — follow the AMC map on the ground, not this.',
        'https://www.google.com/maps/dir/Lincoln,+NH/Lafayette+Place+Campground,+Franconia,+NH')

    # ---------------- MONTREAL ----------------
    P, _ = m.mk('montreal')
    b = []
    b.append(m.dash('walk', P, [(45.5227, -73.6031), (45.5300, -73.6100), (45.5366, -73.6152)], 5))
    b.append(m.dash('walk', P, [(45.5152, -73.5849), (45.5090, -73.5880), (45.5039, -73.5877), (45.4990, -73.6020), (45.4923, -73.6180)], 5))
    b.append(m.marker(P, 45.5230, -73.5960, "YOUR BASE — Plateau / Mile End", "nights 3–5", "base", r=12))
    b.append(m.marker(P, 45.5227, -73.6020, "St-Viateur Bagel", "24 h · Mile End", "stop", r=7))
    b.append(m.marker(P, 45.5229, -73.5952, "Fairmount Bagel", "24 h · 5 min from St-Viateur", "stop", r=7))
    b.append(m.marker(P, 45.5366, -73.6152, "Marché Jean-Talon", "peak harvest", "hi"))
    b.append(m.marker(P, 45.5152, -73.5849, "Tam-Tams", "Sun 12–6 · free", "ev"))
    b.append(m.marker(P, 45.5039, -73.5877, "Kondiaronk Belvédère", "the view", "stop"))
    b.append(m.marker(P, 45.4923, -73.6180, "Saint Joseph's Oratory", "largest dome in Canada", "hi"))
    b.append(m.marker(P, 45.5045, -73.5560, "Notre-Dame Basilica + AURA", "", "hi"))
    b.append(m.marker(P, 45.5024, -73.5541, "Pointe-à-Callière", "", "stop", r=7))
    b.append(m.marker(P, 45.5085, -73.5654, "Esplanade Tranquille", "MUTEK free stage, 5 p.m.", "ev"))
    b.append(m.marker(P, 45.5590, -73.5620, "Botanical Garden", "Gardens of Light", "ev"))
    b.append(m.marker(P, 45.4790, -73.5793, "Atwater Market", "Lachine Canal", "stop", r=6))
    frag['montreal'] = m.wrap('montreal', ''.join(b),
        '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Marquee</span>'
        '<span><i class="lg ev"></i>Evening</span><span><i class="lg ln wk"></i>Suggested walk</span>',
        'Everything here is Métro or foot. The dotted lines are the two walks worth doing end to end, drawn schematically: bagels to Jean-Talon, and Tam-Tams over the mountain to the Oratory.',
        'https://www.google.com/maps/dir/Mile+End,+Montreal/March%C3%A9+Jean-Talon/Mont+Royal+Chalet/Saint+Joseph%27s+Oratory')

    # ---------------- QUEBEC ----------------
    P, _ = m.mk('quebec')
    b = []
    b.append(m.dash('walk', P, [(46.8108, -71.2247), (46.8112, -71.2188), (46.8109, -71.2117), (46.8078, -71.2065), (46.8030, -71.2192), (46.8072, -71.2150), (46.8120, -71.2052), (46.8144, -71.2076), (46.8137, -71.2049), (46.8123, -71.2028), (46.8135, -71.2033), (46.8135, -71.2003)], 5))
    b.append(m.marker(P, 46.8108, -71.2247, "YOUR BASE — St-Jean-Baptiste", "nights 6–9", "base", r=12))
    b.append(m.marker(P, 46.8109, -71.2117, "Porte Saint-Louis", "start the ramparts", "stop", r=7))
    b.append(m.marker(P, 46.8078, -71.2065, "La Citadelle", "star fort", "hi"))
    b.append(m.marker(P, 46.8030, -71.2192, "Plains of Abraham", "1759 battlefield", "hi"))
    b.append(m.marker(P, 46.8120, -71.2052, "Château Frontenac", "Dufferin Terrace", "hi"))
    b.append(m.marker(P, 46.8144, -71.2076, "Notre-Dame de Québec", "the Holy Door", "hi"))
    b.append(m.marker(P, 46.8139, -71.2086, "Morrin Centre", "jail → library", "stop", r=7))
    b.append(m.marker(P, 46.8135, -71.2033, "Place Royale", "Champlain, 1608", "hi"))
    b.append(m.marker(P, 46.8123, -71.2028, "Petit-Champlain", "Escalier Casse-Cou", "stop", r=7))
    b.append(m.marker(P, 46.8145, -71.2013, "Musée de la civilisation", "closed Mondays", "stop", r=7))
    b.append(m.marker(P, 46.8135, -71.2003, "Lévis ferry", "C$4.25 · sunset", "ev"))
    frag['quebec'] = m.wrap('quebec', ''.join(b),
        '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Marquee</span>'
        '<span><i class="lg ev"></i>Evening</span><span><i class="lg ln wk"></i>Day 6 walking route</span>',
        'The dotted line is the whole of Day 6, in order — walls, Citadelle, Plains, cathedral, Dufferin Terrace, down the Breakneck Steps, out on the ferry. Under four miles, drawn schematically.',
        'https://www.google.com/maps/dir/Porte+Saint-Louis,+Quebec+City/Citadelle+of+Quebec/Plains+of+Abraham/Ch%C3%A2teau+Frontenac/Place+Royale,+Quebec+City/Quebec+City+ferry+terminal')

    # ---------------- BEAUPRE ----------------
    P, _ = m.mk('beaupre')
    b = []
    b.append(m.leg(P, 'cote-de-beaupre', fallback=[(46.8135, -71.2160), (46.8500, -71.1800), (46.8905, -71.1475), (46.9200, -71.1000), (46.9600, -71.0200), (47.0000, -70.9600), (47.0225, -70.9310), (47.0450, -70.8800), (47.0570, -70.8560)]))
    b.append(m.leg(P, 'chemin-royal', fallback=[(46.8930, -71.1450), (46.8700, -71.1420), (46.8530, -71.1370), (46.8570, -71.0900), (46.8620, -71.0250), (46.8900, -70.9500), (46.9150, -70.9050), (46.9550, -70.8400), (46.9700, -70.8600), (46.9600, -70.9600), (46.9300, -71.0300), (46.9060, -71.0790), (46.8930, -71.1450)]))
    b.append(m.marker(P, 46.8135, -71.2160, "Québec City", "your base", "base", r=11))
    b.append(m.marker(P, 46.8905, -71.1475, "Montmorency Falls", "83 m · taller than Niagara", "hi", r=11))
    b.append(m.marker(P, 46.8530, -71.1370, "Sainte-Pétronille", "best view back to the city", "stop"))
    b.append(m.marker(P, 46.9060, -71.0790, "Cassis Monna & Filles", "", "stop", r=7))
    b.append(m.marker(P, 46.9611, -70.9586, "Sainte-Famille", "1743 church", "stop", r=7))
    b.append(m.marker(P, 46.9145, -70.9036, "Saint-Jean", "Manoir Mauvide-Genest, 1734", "stop", r=7))
    b.append(m.marker(P, 47.0225, -70.9310, "Sainte-Anne-de-Beaupré", "1 M pilgrims a year", "hi", r=11))
    b.append(m.marker(P, 47.0570, -70.8560, "Canyon Sainte-Anne", "74 m falls · 3 bridges", "stop"))
    frag['beaupre'] = m.wrap('beaupre', ''.join(b),
        '<span><i class="lg base"></i>Base</span><span><i class="lg hi"></i>Marquee</span>'
        '<span><i class="lg ln"></i>Route 138 out</span><span><i class="lg ln lp"></i>Chemin Royal, 67 km</span>',
        'Day 7 in one picture: out along the Côte-de-Beaupré on Route 138, then the island loop anticlockwise, finishing at Sainte-Pétronille for sunset.',
        'https://www.google.com/maps/dir/Quebec+City/Montmorency+Falls/Basilica+of+Sainte-Anne-de-Beaupr%C3%A9/Canyon+Sainte-Anne/Sainte-P%C3%A9tronille,+QC')

    # ---------------- CHARLEVOIX ----------------
    P, _ = m.mk('charlevoix')
    b = []
    b.append(m.leg(P, 'rte-138-out', fallback=[(47.443, -70.501), (47.520, -70.420), (47.600, -70.290), (47.653, -70.152), (47.760, -70.010), (47.900, -69.870), (48.020, -69.790), (48.107, -69.731)]))
    b.append(m.leg(P, 'rte-362-back', fallback=[(47.443, -70.501), (47.483, -70.343), (47.530, -70.270), (47.573, -70.212), (47.620, -70.175), (47.653, -70.152)]))
    b.append(m.leg(P, 'gorge-from-malbaie', fallback=[(47.653, -70.152), (47.720, -70.270), (47.790, -70.370), (47.868, -70.421)]))
    b.append(m.marker(P, 47.443, -70.501, "Baie-Saint-Paul", "the town", "stop", r=10))
    b.append(m.marker(P, 47.396, -70.645, "YOUR BASE — Rang Saint-Placide", "nights 9–10 · 12 km out of town", "base", r=12))
    b.append(m.marker(P, 47.483, -70.343, "Les Éboulements", "centre of the crater", "stop"))
    b.append(m.marker(P, 47.573, -70.212, "Saint-Irénée", "beach · Domaine Forget", "stop", r=7))
    b.append(m.marker(P, 47.653, -70.152, "La Malbaie", "Manoir Richelieu", "stop"))
    b.append(m.marker(P, 47.868, -70.421, "Hautes-Gorges", "800 m walls · Acropole", "hi", r=12))
    b.append(m.marker(P, 48.107, -69.731, "Baie-Ste-Catherine", "whale cruises, 10:15 a.m.", "ev", r=11))
    b.append(m.marker(P, 48.1391, -69.7194, "Tadoussac", "free ferry, 10 min", "stop"))
    frag['charlevoix'] = m.wrap('charlevoix', ''.join(b),
        '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Hautes-Gorges</span>'
        '<span><i class="lg ev"></i>Whales</span><span><i class="lg ln"></i>Rte 138 out</span><span><i class="lg ln sc"></i>Rte 362 back</span>',
        'Day 9 goes out on Route 138 in the morning and comes back on Route 362 — the balcony road — in the evening light. Day 10 is the gold spur up to the gorge.',
        'https://www.google.com/maps/dir/Baie-Saint-Paul,+QC/Baie-Sainte-Catherine,+QC/La+Malbaie,+QC/Les+%C3%89boulements,+QC/Baie-Saint-Paul,+QC')

    return frag
