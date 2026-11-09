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
