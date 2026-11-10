"""Fetch film/series metadata from Wookieepedia (starwars.fandom.com) into data/raw/*.json.

Usage: python3 -I scripts/fetch.py
Text from Wookieepedia is CC BY-SA 3.0 — keep attribution on the page.
"""

import json
import pathlib
import time
import urllib.parse
import urllib.request

API = "https://starwars.fandom.com/api.php"
UA = "sw-timeline-prototype/0.1 (personal project)"
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# (id, wookieepedia page title, kind, format, canon)
# kind: film | series   format: live | animated
WORKS = [
    # Skywalker saga
    ("ep1", "Star Wars: Episode I The Phantom Menace", "film", "live", "saga"),
    ("ep2", "Star Wars: Episode II Attack of the Clones", "film", "live", "saga"),
    ("ep3", "Star Wars: Episode III Revenge of the Sith", "film", "live", "saga"),
    ("ep4", "Star Wars: Episode IV A New Hope", "film", "live", "saga"),
    ("ep5", "Star Wars: Episode V The Empire Strikes Back", "film", "live", "saga"),
    ("ep6", "Star Wars: Episode VI Return of the Jedi", "film", "live", "saga"),
    ("ep7", "Star Wars: Episode VII The Force Awakens", "film", "live", "saga"),
    ("ep8", "Star Wars: Episode VIII The Last Jedi", "film", "live", "saga"),
    ("ep9", "Star Wars: Episode IX The Rise of Skywalker", "film", "live", "saga"),
    # Spin-off films
    ("tcw-film", "Star Wars: The Clone Wars (film)", "film", "animated", "canon"),
    ("rogue-one", "Rogue One: A Star Wars Story", "film", "live", "canon"),
    ("solo", "Solo: A Star Wars Story", "film", "live", "canon"),
    ("mando-grogu", "Star Wars: The Mandalorian and Grogu", "film", "live", "canon"),
    # Canon series
    ("tcw", "Star Wars: The Clone Wars", "series", "animated", "canon"),
    ("rebels", "Star Wars Rebels", "series", "animated", "canon"),
    ("resistance", "Star Wars Resistance", "series", "animated", "canon"),
    ("mandalorian", "Star Wars: The Mandalorian", "series", "live", "canon"),
    ("bad-batch", "Star Wars: The Bad Batch", "series", "animated", "canon"),
    ("boba-fett", "Star Wars: The Book of Boba Fett", "series", "live", "canon"),
    ("kenobi", "Star Wars: Obi-Wan Kenobi", "series", "live", "canon"),
    ("andor", "Andor (television series)", "series", "live", "canon"),
    ("tales-jedi", "Star Wars: Tales of the Jedi (television series)", "series", "animated", "canon"),
    ("ahsoka", "Star Wars: Ahsoka", "series", "live", "canon"),
    ("yja", "Star Wars: Young Jedi Adventures", "series", "animated", "canon"),
    ("tales-empire", "Star Wars: Tales of the Empire", "series", "animated", "canon"),
    ("acolyte", "Star Wars: The Acolyte", "series", "live", "canon"),
    ("skeleton-crew", "Star Wars: Skeleton Crew", "series", "live", "canon"),
    ("tales-underworld", "Star Wars: Tales of the Underworld", "series", "animated", "canon"),
    ("maul", "Star Wars: Maul - Shadow Lord", "series", "animated", "canon"),
    # Announced / in production (Wookieepedia "Category:Future films")
    ("starfighter", "Star Wars: Starfighter", "film", "live", "canon"),
    ("rey-film", "Untitled Star Wars film (Sharmeen Obaid-Chinoy)", "film", "live", "canon"),
    ("kinberg", "Untitled Star Wars trilogy (Simon Kinberg)", "film", "live", "canon"),
    ("mangold", "Untitled Star Wars film (James Mangold)", "film", "live", "canon"),
    ("filoni-film", "Untitled Star Wars film (Dave Filoni)", "film", "live", "canon"),
    ("lando", "Lando (film)", "film", "live", "canon"),
    ("rogue-squadron", "Rogue Squadron (film)", "film", "live", "canon"),
    # Legends
    ("holiday-special", "The Star Wars Holiday Special", "film", "live", "legends"),
    ("caravan", "Caravan of Courage: An Ewok Adventure", "film", "live", "legends"),
    ("battle-endor", "Ewoks: The Battle for Endor", "film", "live", "legends"),
    ("droids", "Star Wars: Droids: The Adventures of R2-D2 and C-3PO", "series", "animated", "legends"),
    ("ewoks", "Ewoks (television series)", "series", "animated", "legends"),
    ("clone-wars-2003", "Star Wars: Clone Wars", "series", "animated", "legends"),
]


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for wid, title, kind, fmt, canon in WORKS:
        out = RAW / f"{wid}.json"
        if out.exists():
            continue
        d = api(action="parse", page=title, prop="wikitext", redirects=1)
        if "error" in d:
            print("!!", wid, title, d["error"]["info"])
            continue
        out.write_text(json.dumps({
            "id": wid, "title": d["parse"]["title"], "kind": kind,
            "format": fmt, "canon": canon,
            "wikitext": d["parse"]["wikitext"]["*"],
        }, ensure_ascii=False))
        print("ok", wid, d["parse"]["title"])
        time.sleep(0.5)
    fetch_seasons()
    fetch_anthology_episodes()
    fetch_books_and_games()
    fetch_characters()
    fetch_episodes()


# Books and games come from Wookieepedia categories (incl. subcategories) instead of a
# hand-kept list. Novelizations retell the films, so they're left out.
BOOK_CATEGORIES = ["Category:Canon adult novels", "Category:Canon young-adult novels"]
GAME_CATEGORIES = ["Category:Canon console and computer games"]
# series-level only: issues, one-shots and annuals would swamp the lane
COMIC_CATEGORIES = ["Category:Canon ongoing series", "Category:Canon comic miniseries"]
# Legends (pre-2014 Expanded Universe); shown only when the Legends filter is on
LEGENDS_BOOK_CATEGORIES = ["Category:Legends novels"]
LEGENDS_COMIC_CATEGORIES = ["Category:Legends ongoing series", "Category:Legends comic miniseries"]
# pages about a whole series, not a single novel
NOT_A_NOVEL_CATEGORIES = ["Category:Legends novel series", "Category:Legends young-reader series"]
SKIP_TITLES = {
    "Untitled collectible card game",  # filed under games, but not a video game
    "Star Wars: Black, White & Red",  # an umbrella for three miniseries that are listed themselves
    # comics that retell a show or novel already on the timeline
    "Star Wars: Ahsoka (comic series)", "Star Wars: Obi-Wan Kenobi (comic series)",
    "Star Wars: The Book of Boba Fett (comic series)", "Star Wars: The Mandalorian (comic series)",
    "Star Wars: The Mandalorian Season 2", "Star Wars: Thrawn (comic series)",
    "Star Wars: Thrawn: Alliances (comic series)", "Star Wars Adventures: Smuggler's Run",
    "Star Wars Adventures: The Weapon of a Jedi",
    # Legends comics that adapt a film or novel
    "Classic Star Wars: A New Hope (comic series)", "Classic Star Wars: The Empire Strikes Back (comic series)",
    "Classic Star Wars: Return of the Jedi (comic series)", "Star Wars: A New Hope - The Special Edition",
    "Star Wars: Episode I — The Phantom Menace (comic series)",
    "Star Wars: Episode II — Attack of the Clones (comic series)",
    "Star Wars: Episode III — Revenge of the Sith (comic series)", "Star Wars: Return of the Jedi (1983)",
    "Star Wars: Heir to the Empire (comic series)", "Star Wars: Dark Force Rising (comic series)",
    "Star Wars: The Last Command (comic series)", "Star Wars: Splinter of the Mind's Eye (comic series)",
}


def is_adaptation(title):
    """Novelizations and film adaptations retell a film, so they'd only duplicate it."""
    t = title.lower()
    return "novelization" in t or t.endswith(" adaptation")


def category_pages(cat):
    pages, subcats, cont = [], [], {}
    while True:
        d = api(action="query", list="categorymembers", cmtitle=cat, cmlimit=500,
                cmtype="page|subcat", **cont)
        for m in d["query"]["categorymembers"]:
            (subcats if m["ns"] == 14 else pages).append(m["title"])
        if "continue" not in d:
            break
        cont = d["continue"]
    for sub in subcats:
        pages += category_pages(sub)
    return pages


def slug(title):
    import re
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def fetch_books_and_games():
    """Lead section (infobox) of every canon novel, console/PC game and comic series, 50 pages per request."""
    import re
    todo = []
    not_novels = {t for c in NOT_A_NOVEL_CATEGORIES for t in category_pages(c)}
    groups = (("book", "canon", BOOK_CATEGORIES), ("game", "canon", GAME_CATEGORIES),
              ("comic", "canon", COMIC_CATEGORIES), ("book", "legends", LEGENDS_BOOK_CATEGORIES),
              ("comic", "legends", LEGENDS_COMIC_CATEGORIES))
    for kind, canon, cats in groups:
        titles = sorted({t for c in cats for t in category_pages(c)})
        for t in titles:
            if is_adaptation(t) or t in SKIP_TITLES or t in not_novels or t.startswith("Category:"):
                continue
            wid = f"{kind}-{slug(t)}" if canon == "canon" else f"legends-{kind}-{slug(t)}"
            if not (RAW / f"{wid}.json").exists():
                todo.append((wid, t, kind, canon))
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main",
                titles="|".join(t for _, t, _, _ in batch))
        q = d["query"]
        norm = {n["to"]: n["from"] for n in q.get("normalized", [])}
        pages = {norm.get(p["title"], p["title"]): p for p in q["pages"].values()}
        for wid, t, kind, canon in batch:
            p = pages.get(t)
            if not p or "revisions" not in p:
                print("!!", kind, t)
                continue
            w = p["revisions"][0]["slots"]["main"]["*"]
            first_heading = re.search(r"^==[^=]", w, re.M)
            (RAW / f"{wid}.json").write_text(json.dumps({
                "id": wid, "title": p["title"], "kind": kind, "format": kind, "canon": canon,
                "wikitext": w[:first_heading.start()] if first_heading else w,
            }, ensure_ascii=False))
        print(f"books/games/comics {i + len(batch)}/{len(todo)}")
        time.sleep(0.5)


CONFIG = ROOT / "data" / "characters-config.json"
CHAR_RAW = RAW / "characters"
EPISODES_RAW = RAW / "episodes" / "episodes.json"


def appearances_section(w):
    """The level-2 '==Appearances==' list (character pages also have an '===Appearances==='
    sub-heading under 'Behind the scenes', which is prose, not the list)."""
    import re
    m = re.search(r"^==\s*Appearances\s*==\s*$", w, re.M)
    if not m:
        return ""
    nxt = re.search(r"^==[^=]", w[m.end():], re.M)
    return w[m.end():m.end() + nxt.start()] if nxt else w[m.end():]


def fetch_characters():
    """Keep only the infobox (lead section) and the Appearances list of each character."""
    import re
    cfg = json.loads(CONFIG.read_text())
    CHAR_RAW.mkdir(parents=True, exist_ok=True)
    for cid, title in cfg["characters"].items():
        out = CHAR_RAW / f"{cid}.json"
        if out.exists():
            continue
        d = api(action="parse", page=title, prop="wikitext", redirects=1)
        if "error" in d:
            print("!! character", cid, title, d["error"]["info"])
            continue
        w = d["parse"]["wikitext"]["*"]
        first_heading = re.search(r"^==[^=]", w, re.M)
        out.write_text(json.dumps({
            "id": cid, "title": d["parse"]["title"],
            "lead": w[:first_heading.start()] if first_heading else w,
            "appearances": appearances_section(w),
        }, ensure_ascii=False))
        print("character", cid, d["parse"]["title"])
        time.sleep(0.4)


def fetch_episodes():
    """Air date, in-universe year and season of every episode a character appears in,
    fetched 50 pages per request. Cached in data/raw/episodes/episodes.json."""
    import re
    cfg = json.loads(CONFIG.read_text())
    templates = cfg["templates"]
    cache = json.loads(EPISODES_RAW.read_text()) if EPISODES_RAW.exists() else {}
    wanted = set()
    for f in CHAR_RAW.glob("*.json"):
        for m in re.finditer(r"\{\{(\w+)\|([^|}]+)", json.loads(f.read_text())["appearances"]):
            if m[1] in templates:
                wanted.add(m[2].strip())
    missing = sorted(wanted - cache.keys())

    def field(w, name):
        m = re.search(r"^\|\s*" + name + r"\s*=(.*?)(?=^\||^\}\})", w, re.M | re.S)
        return m.group(1).strip() if m else ""

    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main",
                redirects=1, titles="|".join(batch))
        q = d["query"]
        back = {}  # resolved title → requested title
        for n in q.get("normalized", []) + q.get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for page in q["pages"].values():
            req = back.get(page["title"], page["title"])
            if "revisions" not in page:
                cache[req] = None
                continue
            w = page["revisions"][0]["slots"]["main"]["*"]
            # self-closing refs first, or `<ref name="x" />` would be read as an opening tag
            # and everything up to the next </ref> (e.g. the timeline field) deleted
            w = re.sub(r"<ref[^>]*>.*?</ref>", "", re.sub(r"<ref[^>]*/>", "", w), flags=re.S)
            cache[req] = {"title": page["title"], "airdate": field(w, "airdate"),
                          "timeline": field(w, "timeline"), "season": field(w, "season")}
        for t in batch:
            cache.setdefault(t, None)
        print(f"episodes {i + len(batch)}/{len(missing)}")
        time.sleep(0.5)
    EPISODES_RAW.parent.mkdir(parents=True, exist_ok=True)
    EPISODES_RAW.write_text(json.dumps(cache, indent=1, ensure_ascii=False))


NUM_WORDS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"]


def fetch_seasons():
    """Season pages use inconsistent names ("Season 1" / "Season One" / with or
    without the "Star Wars:" prefix), so try the variants and keep the first hit."""
    for f in sorted(RAW.glob("*.json")):
        work = json.loads(f.read_text())
        if work["kind"] != "series" or "seasons" in work:
            continue
        short = work["title"].replace("Star Wars: ", "").replace(" (television series)", "")
        if short == "Star Wars Rebels" or short == "Star Wars Resistance":
            short = short.replace("Star Wars ", "")
        if short == "Clone Wars":  # 2003 Legends series uses "Volume"
            continue
        seasons = []
        for n in range(1, 9):
            hit = None
            for name in (f"{short} Season {n}", f"{short} Season {NUM_WORDS[n - 1]}",
                         f"{work['title']} Season {n}", f"{work['title']} Season {NUM_WORDS[n - 1]}"):
                d = api(action="parse", page=name, prop="wikitext", redirects=1)
                time.sleep(0.3)
                if "error" not in d:
                    hit = {"n": n, "title": d["parse"]["title"], "wikitext": d["parse"]["wikitext"]["*"]}
                    break
            if not hit:
                break
            seasons.append(hit)
        work["seasons"] = seasons
        f.write_text(json.dumps(work, ensure_ascii=False))
        print("seasons", work["id"], len(seasons))


# Anthology series jump across eras, so their in-universe span comes from each episode.
ANTHOLOGIES = {"tales-jedi", "tales-empire", "tales-underworld"}


def fetch_anthology_episodes():
    import re
    for wid in ANTHOLOGIES:
        f = RAW / f"{wid}.json"
        work = json.loads(f.read_text())
        if "episodes" in work:
            continue
        titles = list(dict.fromkeys(re.findall(r'"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]"', work["wikitext"])))
        eps = []
        for t in titles:
            d = api(action="parse", page=t, prop="wikitext", section=0, redirects=1)
            time.sleep(0.3)
            if "error" not in d:
                eps.append({"title": d["parse"]["title"], "wikitext": d["parse"]["wikitext"]["*"]})
        work["episodes"] = eps
        f.write_text(json.dumps(work, ensure_ascii=False))
        print("episodes", wid, len(eps))


if __name__ == "__main__":
    main()
