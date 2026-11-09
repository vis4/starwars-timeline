# Star Wars timeline

Interactive timeline of Star Wars films and TV series, toggleable between
real-world release dates and in-universe years (BBY/ABY).

## Data pipeline

```
python3 -I scripts/fetch.py   # Wookieepedia API → data/raw/*.json (cached; delete a file to refetch)
python3 -I scripts/build.py   # raw wikitext → data/works.json
```

- The list of works lives in `WORKS` in `scripts/fetch.py` (id, exact page title, kind, format, canon/saga/legends).
- `fetch.py` also pulls season pages (per-season air dates) and, for the anthology
  series (`ANTHOLOGIES`), each episode page, since those jump across eras.
- `data/overrides.json` holds short display labels and facts the infoboxes lack
  (the Episode I–VI and Clone Wars film infoboxes have no `timeline` field).
- Missing "last aired" dates fall back to the newest date in the page's episode table.
- Planned works come from Wookieepedia's `Category:Future films` (check it for new
  announcements and add them to `WORKS`). A release date of "Future" becomes
  `status: "tba"`; works without a year on an axis are drawn in the "TBA"/"Unknown"
  row at the bottom, and years before 1000 BBY (the Dawn of the Jedi film, 25,000 BBY)
  get a separate slot above the axis. "After N ABY" is placed at N+1.
- Posters: `poster` in `overrides.json` > first season page's infobox image (a series'
  own infobox image is usually a logo) > the infobox image. `build.py` resolves the
  file names to 240px thumbnail URLs via the API and caches them in
  `data/poster-cache.json`. Images are hotlinked from Wookieepedia, not copied; they
  are © Lucasfilm, so check usage rights before publishing the page.

Text from Wookieepedia is CC BY-SA 3.0, so the page must keep its attribution.

## Font

The title uses Star Jedi by Boba Fonts (freeware, `fonts/info.txt`). The original
`StarJedi-DGRW.ttf` has a broken `post` table that Chrome rejects, so the page loads
`StarJedi-web.ttf`, made with `python3 -I scripts/fix_font.py fonts/StarJedi-DGRW.ttf fonts/StarJedi-web.ttf`
(replaces `post` with a names-free v3 table; all glyphs unchanged).

## Run

Serve the folder (it fetches `data/works.json`), e.g. `python3 -m http.server 8765`.

## Next: characters

Character pages (e.g. `Ahsoka_Tano`) list `==Appearances==` in in-universe order.
Filtering those links against the work titles in `WORKS` gives each character's arc
across the timeline.
