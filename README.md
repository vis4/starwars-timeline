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

## Books, games and comics

Canon novels (adult and young-adult, incl. The High Republic; novelizations, "Expanded Editions",
audiobook editions and reprints or box sets are left out, see `is_adaptation()` in `fetch.py`),
console/PC games and comic series come from Wookieepedia categories (`BOOK_CATEGORIES`,
`GAME_CATEGORIES`, `COMIC_CATEGORIES` in `fetch.py`), so new releases are picked up by
`npm run data`. Only their infobox is cached. They're off by default; in their lanes, labels
that would land far from their mark are dropped (the tooltip still names them). Character
arcs pass through them when they're switched on.

Legends novels (`LEGENDS_BOOK_CATEGORIES`, incl. the young-reader series; pages about a whole
series are skipped) and Legends comic series (`LEGENDS_COMIC_CATEGORIES`) are fetched too, with
ids prefixed `legends-`. They share the lanes of their canon counterparts but are drawn gray, and
show only when both "Legends" and their own filter ("Books", "Comics") are on. Likewise the Legends
films and shows sit in the live-action spin-offs and Animated lanes. With Legends the in-universe axis
reaches back to ~5,000 BBY (Old Republic) and forward to ~140 ABY (Legacy); only years before
10,000 BBY collapse into the far-past slot. The dense print lanes get a column budget from the
width that's left; past it, marks overlap instead of widening the chart.

Comics are counted per series (ongoing series and miniseries), not per issue, one-shot or
annual. Film adaptations, and series that retell a show or novel already on the timeline
(`SKIP_TITLES`), are left out. On the release axis a comic is a bar from its first to its last
issue. Few comic infoboxes name a series, so titles sharing a prefix ("The High Republic
Adventures – …") are grouped. Character pages list comic appearances per issue
("Darth Vader (2017) 10"); `build.py` maps them to their series, and the arc visits each
comic once.

## Font

The title uses Star Jedi by Boba Fonts (freeware, `fonts/info.txt`). The original
`StarJedi-DGRW.ttf` has a broken `post` table that Chrome rejects, so the page loads
`StarJedi-web.ttf`, made with `python3 -I scripts/fix_font.py fonts/StarJedi-DGRW.ttf fonts/StarJedi-web.ttf`
(replaces `post` with a names-free v3 table; all glyphs unchanged).

## Run

- `npm run dev`: serve the folder at http://localhost:8765 (the page fetches `data/works.json`)
- `npm run data`: refetch from Wookieepedia (only pages not yet in `data/raw/`) and rebuild `data/works.json`
- `npm run deploy`: copy the files the page needs (`index.html`, `data/works.json`, `data/characters.json`,
  `fonts/StarJedi-web.ttf`) to `vis4.net:vis4/starwars/` for https://vis4.net/starwars/

## Characters

`data/characters-config.json` lists the characters in the picker (id → Wookieepedia page,
plus short labels) and maps Wookieepedia's episode citation templates (`{{TCW|…}}`,
`{{Rebels|…}}`, …) to work ids. `fetch.py` keeps each character's infobox and
`==Appearances==` list (in-universe order) and every referenced episode's air date,
year and season. `build.py` writes `data/characters.json`: one entry per appearance
with its work, kind (on screen, flashback, hologram, voice, Force ghost, vision,
mention), in-universe year and air date. Episodes without their own year are spread
through their season's range in list order.

In the page, picking a character dims the works they're not in and draws a line
through their on-screen appearances in story order.

## Links

The URL hash holds the view, leaving out whatever is at its default:
`#axis=release&show=live,animated,comics,upcoming&c=ahsoka` (`axis`: `release`; `show`: the
filters that are on, or `none`; `c`: a character id). Older `#ahsoka` links still work. The
controls are set from the hash on load, so checkboxes a browser restores after a reload can't
disagree with the chart.
