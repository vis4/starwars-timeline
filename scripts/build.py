"""Parse data/raw/*.json (Wookieepedia wikitext) into data/works.json.

Usage: python3 -I scripts/build.py
"""

import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TODAY = dt.date.today()
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONTH_RE = "|".join(MONTHS)


def strip_refs(w):
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*/>", "", w)
    return re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)


def field(w, name):
    m = re.search(r"^\|\s*" + re.escape(name) + r"\s*=(.*?)(?=^\||^\}\})", w, re.M | re.S)
    return m.group(1).strip() if m else ""


def delink(s):
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    return s.replace("&ndash;", "–").replace("&dash;", "–")


def lines(value):
    """Split a bulleted infobox value into (text, note) pairs."""
    out = []
    for ln in re.split(r"\n|(?=\*)", value):
        ln = ln.strip().lstrip("*").strip()
        if not ln:
            continue
        note = " ".join(delink(n) for n in re.findall(r"\{\{C\|((?:[^{}]|\{\{[^{}]*\}\})*)\}\}", ln))
        text = re.sub(r"\{\{C\|(?:[^{}]|\{\{[^{}]*\}\})*\}\}", "", ln)
        out.append((text, note))
    return out


def parse_dates(value):
    """Return list of (iso_date, precision) found in a value. Year-only dates → Jan 1, 'year'."""
    s = delink(value)
    found = []
    for m in re.finditer(rf"({MONTH_RE}) (\d{{1,2}}),? (\d{{4}})", s):
        found.append((dt.date(int(m[3]), MONTHS.index(m[1]) + 1, int(m[2])), "day"))
    if not found:
        for m in re.finditer(r"\b(19|20)\d\d\b", s):
            found.append((dt.date(int(m[0]), 1, 1), "year"))
    return found


def years(text):
    """In-universe years from wikilinks like [[22 BBY]], [[3 ABY/Legends|3.5 ABY]], [[22 BBY|22]]."""
    out = []
    for m in re.finditer(r"\[\[(\d[\d,]*) (BBY|ABY)(?:/Legends)?(?:\|[^\]]*)?\]\]", text):
        n = int(m[1].replace(",", ""))
        out.append(-n if m[2] == "BBY" else n)
    return out


def parse_timeline(value):
    """Main in-universe range plus prologue/epilogue markers."""
    main, extras, approx = [], [], False
    for text, note in lines(value):
        ys = years(text)
        if not ys:
            continue
        if re.search(r"\bc\.|Between|During|after", text, re.I):
            approx = True
        if re.search(r"Prologue|Epilogue|Opening", note, re.I):
            extras.append({"year": ys[0], "label": note})
        else:
            main.extend(ys)
    if not main:
        return None, extras
    return {"start": min(main), "end": max(main), "approx": approx}, extras


def episode_table_dates(w):
    """All air dates found in wikitable(s) whose header mentions 'Airdate'."""
    dates = []
    for tbl in re.findall(r"\{\|.*?\n\|\}", w, flags=re.S):
        if "irdate" in tbl.split("|-")[0]:
            dates += [d for d, p in parse_dates(strip_refs(tbl)) if p == "day"]
    return dates


def release_span(w):
    """(start, end, precision) for a series or season page."""
    info = strip_refs(w)
    first = parse_dates(field(info, "first aired"))
    last = parse_dates(field(info, "last aired"))
    table = episode_table_dates(w)
    if not first:
        return None
    start, prec = min(first)
    end = max(d for d, _ in last) if last else (max(table) if table else None)
    return start, end, prec


def status_for(start, end):
    if start > TODAY:
        return "upcoming"
    if end is None or end > TODAY:
        return "airing"
    return "ended"


def iso(d):
    return d.isoformat() if d else None


def build_work(raw, overrides):
    w = raw["wikitext"]
    info = strip_refs(w)
    o = overrides.get(raw["id"], {})
    work = {
        "id": raw["id"],
        "title": raw["title"],
        "label": o.get("label", short_label(raw)),
        "url": "https://starwars.fandom.com/wiki/" + raw["title"].replace(" ", "_"),
        "kind": raw["kind"],
        "format": raw["format"],
        "canon": raw["canon"],
    }

    # --- real-world release ---
    if raw["kind"] in ("film", "book", "game"):  # one release date
        dates = parse_dates(field(info, "release date"))
        if dates:
            d, prec = min(dates)  # earliest = original/premiere release
            work["release"] = {"start": iso(d), "end": iso(d), "precision": prec,
                               "status": "upcoming" if d > TODAY else "released"}
        else:  # announced, release date "Future"
            work["release"] = {"start": None, "end": None, "status": "tba"}
    else:
        seasons = []
        for s in raw.get("seasons", []):
            span = release_span(s["wikitext"])
            if not span:
                continue  # e.g. "Future" — no date announced
            start, end, prec = span
            seasons.append({"n": s["n"], "start": iso(start), "end": iso(end), "precision": prec,
                            "status": status_for(start, end), "url": "https://starwars.fandom.com/wiki/" + s["title"].replace(" ", "_")})
        if not seasons:
            start, end, prec = release_span(w)
            seasons = [{"n": 1, "start": iso(start), "end": iso(end), "precision": prec,
                        "status": status_for(start, end)}]
        work["seasons"] = seasons
        aired = [s for s in seasons if s["status"] != "upcoming"]
        work["release"] = {
            "start": seasons[0]["start"],
            "end": max((s["end"] or s["start"]) for s in aired) if aired else seasons[0]["start"],
            "status": "upcoming" if not aired else
                      ("ongoing" if any(s["status"] != "ended" for s in seasons) else "ended"),
        }
        n_eps = field(info, "num episodes")
        if n_eps.strip().isdigit():
            work["episodes"] = int(n_eps)

    # --- in-universe ---
    if raw.get("episodes"):
        segments, extras = [], []
        for ep in raw["episodes"]:
            rng, ex = parse_timeline(field(strip_refs(ep["wikitext"]), "timeline"))
            name = re.sub(r" \(episode\)$", "", ep["title"])
            if rng:
                segments.append({**rng, "label": name})
            extras += [{**m, "label": f"{name} ({m['label'].lower()})"} for m in ex]
        work["universe"] = {"start": min(s["start"] for s in segments),
                            "end": max(s["end"] for s in segments), "approx": True}
        work["segments"] = segments
        work["markers"] = extras
    else:
        tl = field(info, "timeline")
        rng, extras = parse_timeline(tl)
        if rng:
            work["universe"] = rng
        if extras:
            work["markers"] = extras
        # keep the wording when it says more than a year ("After 35 ABY", "New Republic Era")
        main = [t for t, note in lines(tl) if not re.search(r"Prologue|Epilogue|Opening", note, re.I)]
        text = re.sub(r"\s+", " ", re.sub(r"\{\{[^{}]*\}\}", "", delink(main[0]))).replace("''", "").strip(" ,") if main else ""
        if text and not re.fullmatch(r"\d[\d,]* [AB]BY", text):
            work["timeline_text"] = text
        # "After 35 ABY" → place it in the following year, not on top of 35 ABY
        if rng and re.match(r"After\b", text):
            work["universe"] = {**rng, "start": rng["start"] + 1, "end": rng["end"] + 1, "approx": True}
        # Books and games that list separate periods ("19 BBY {{C|Past}}", "2 BBY {{C|Present}}",
        # flashbacks, chapters) become segments, like anthology episodes.
        if raw["kind"] in ("book", "game"):
            segs = period_segments(tl)
            if len(segs) > 1:
                work["segments"] = segs
    if raw["kind"] in ("book", "game"):
        series = series_name(field(info, "series"))
        if series:
            work["series"] = series
    if "segments" in o:  # hand-curated periods (e.g. a game's campaign vs. multiplayer eras)
        work["segments"] = [{"approx": False, **s} for s in o["segments"]]
    if work.get("segments") and raw["kind"] in ("book", "game"):
        segs = work["segments"]
        main = next((s for s in segs if s.get("main")), None) \
            or next((s for s in segs if re.fullmatch(r"(main.*|present|)", s["label"], re.I)), segs[0])
        work["universe"] = {"start": min(s["start"] for s in segs), "end": max(s["end"] for s in segs),
                            "approx": True, "main": main["start"]}
    if "universe" in o:
        work["universe"] = {**work.get("universe", {"approx": False}), **o["universe"]}
    if "universe" not in work:
        print("!! no in-universe date for", raw["id"])

    # --- poster: hand pick > first season's infobox image (series' own is usually a logo) > infobox image
    poster = o.get("poster")
    if not poster:
        for s in raw.get("seasons", []):
            poster = infobox_image(s["wikitext"])
            if poster:
                break
    work["poster_file"] = poster or infobox_image(w)
    return work


def series_name(value):
    """'[[Star Wars: The High Republic|...]]' → 'The High Republic'; first entry only."""
    v = re.sub(r"\{\{[^{}]*\}\}", "", delink(value)).replace("''", "").strip()
    v = v.split("\n")[0].lstrip("*").strip()
    v = re.sub(r"^Star Wars:? ", "", v)
    v = re.sub(r"Star Wars: ", "", v)  # "Journey to Star Wars: The Last Jedi"
    v = re.sub(r" (series|media project|publishing program)$", "", v)
    return v or None


def period_segments(value):
    """One segment per dated line of a timeline field, labelled with its note ("Past",
    "flashbacks", "Chapter 7"). Prologue/epilogue lines are left to the markers."""
    segs = []
    for text, note in lines(value):
        ys = years(text)
        if not ys or re.search(r"Prologue|Epilogue|Opening", note, re.I):
            continue
        label = note[:1].upper() + note[1:] if note else "Main story"
        segs.append({"start": min(ys), "end": max(ys), "label": label,
                     "approx": bool(re.search(r"\bc\.|Between|During|after", text, re.I))})
    return segs


def short_label(raw):
    """Books and games: drop disambiguation suffixes and the 'Star Wars' prefix."""
    t = raw["title"]
    if raw["kind"] in ("book", "game"):
        t = re.sub(r" \((?:[\w-]+ )?novel\)$", "", t)
        t = re.sub(r"^Star Wars:? ", "", t)
    return t


def infobox_image(w):
    m = re.search(r"^\|image\s*=\s*\[\[(?:File:|Image:)?([^|\]]+)", w, re.M)
    return m.group(1).strip().replace("_", " ") if m else None


POSTER_CACHE = ROOT / "data" / "poster-cache.json"


def resolve_posters(works, width=240):
    """File name → thumbnail URL on Wookieepedia's image server (cached)."""
    import time
    import urllib.parse
    import urllib.request
    cache = json.loads(POSTER_CACHE.read_text()) if POSTER_CACHE.exists() else {}
    missing = sorted({w["poster_file"] for w in works if w.get("poster_file")} - cache.keys())
    for i in range(0, len(missing), 40):  # API accepts up to 50 titles per request
        batch = missing[i:i + 40]
        url = "https://starwars.fandom.com/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size",
            "iiurlwidth": width, "titles": "|".join("File:" + f for f in batch)})
        req = urllib.request.Request(url, headers={"User-Agent": "sw-timeline-prototype/0.1 (personal project)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        for page in d["query"]["pages"].values():
            name = norm.get(page["title"], page["title"]).removeprefix("File:")
            info = (page.get("imageinfo") or [None])[0]
            cache[name] = info and {"url": info["thumburl"], "w": info["thumbwidth"], "h": info["thumbheight"]}
        time.sleep(0.5)
    POSTER_CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    for w in works:
        f = w.pop("poster_file", None)
        if f and cache.get(f):
            w["poster"] = cache[f]
        elif f:
            print("!! poster not found:", w["id"], f)


# ---------------------------------------------------------------- characters

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9}
NUMBER_WORDS = {w: i + 1 for i, w in enumerate(
    ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"])}
# appearance flags on Wookieepedia → our kinds ("onscreen" when none of these is present)
KIND_FLAGS = [("Mo", "mention"), ("1stm", "mention"), ("Imo", "mention"), ("Flash", "flashback"),
              ("Hologram", "hologram"), ("Voice", "voice"), ("Ghost", "ghost"),
              ("Vision", "vision"), ("Dream", "vision"), ("Corpse", "mention")]


def episode_index(raws):
    """Episode page title → work id, from the episode tables of series and season pages."""
    idx = {}
    for raw in raws:
        if raw["kind"] != "series":
            continue
        for w in [raw["wikitext"]] + [s["wikitext"] for s in raw.get("seasons", [])]:
            for t in re.findall(r'"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]"', w):
                idx.setdefault(t.strip(), raw["id"])
    return idx


def season_ranges(raws):
    """(work id, season number) → in-universe range of that season."""
    out = {}
    for raw in raws:
        for s in raw.get("seasons", []):
            rng, _ = parse_timeline(field(strip_refs(s["wikitext"]), "timeline"))
            if rng:
                out[(raw["id"], s["n"])] = rng
    return out


def build_characters(raws, works):
    cfg = json.loads((ROOT / "data" / "characters-config.json").read_text())
    templates = cfg["templates"]
    by_title = {w["title"]: w["id"] for w in works}
    work_by_id = {w["id"]: w for w in works}
    ep_work = episode_index(raws)
    seasons = season_ranges(raws)
    episodes = json.loads((RAW / "episodes" / "episodes.json").read_text())

    chars = []
    for cid in cfg["characters"]:
        f = RAW / "characters" / f"{cid}.json"
        if not f.exists():
            print("!! character not fetched:", cid)
            continue
        raw = json.loads(f.read_text())
        lead = strip_refs(raw["lead"])
        name = field(lead, "name").split("<br")[0]  # alternate names follow after <br />
        name = delink(re.sub(r"\{\{[^{}]*\}\}", "", name)).strip() or raw["title"]
        birth = years(field(lead, "birth"))

        entries = []
        for line in raw["appearances"].split("\n"):
            if not line.startswith("*"):
                continue
            wid, ep = None, None
            m = re.match(r"\*\s*\{\{(\w+)\|([^|}]+)", line)
            if m and m[1] == "Film":
                n = ROMAN.get(m[2].strip())
                wid = f"ep{n}" if n else None
            elif m and m[1] in templates:
                wid, ep = templates[m[1]], m[2].strip()
            else:
                link = re.match(r"\*\s*(?:'')?\[\[([^\]|]+)", line)
                if link:
                    t = link[1].strip()
                    wid = by_title.get(t) or ep_work.get(t)
                    ep = t if ep_work.get(t) else None
            if wid not in work_by_id:
                continue
            flags = re.findall(r"\{\{(\w+)\}\}", line)
            kind = next((k for flag, k in KIND_FLAGS if flag in flags), "onscreen")
            entries.append({"work": wid, "ep": ep, "kind": kind})

        place_entries(entries, work_by_id, episodes, seasons)
        chars.append({
            "id": cid, "name": name, "label": cfg.get("labels", {}).get(cid, name.split()[0]), "title": raw["title"],
            "url": "https://starwars.fandom.com/wiki/" + raw["title"].replace(" ", "_"),
            # death years aren't drawn: Wookieepedia lists temporary deaths too (Ahsoka, 20 BBY)
            "birth": birth[0] if birth else None,
            "poster_file": infobox_image(lead), "appearances": entries,
        })
    resolve_posters(chars)
    for c in chars:
        works_in = {e["work"] for e in c["appearances"]}
        on = {e["work"] for e in c["appearances"] if e["kind"] == "onscreen"}
        print(f"{c['id']:12} {len(c['appearances']):4} entries · {len(works_in):2} works · {len(on):2} on screen")
    return chars


def place_entries(entries, work_by_id, episodes, seasons):
    """Give every appearance an in-universe year (float) and an air date.
    Episode year comes from the episode infobox, else from its season's range: episodes that
    share a season range are spread through it in list order (the list is chronological)."""
    pending = []  # (entry, range) waiting to be spread within a season range
    for e in entries:
        w = work_by_id[e["work"]]
        u = w.get("universe")
        info = episodes.get(e["ep"]) if e["ep"] else None
        e["air"] = None
        if info:
            ds = parse_dates(info["airdate"])
            e["air"] = min(ds)[0].isoformat() if ds else None
        if not e["air"]:
            e["air"] = w["release"]["start"]
        e["year"] = None
        if info:
            rng, _ = parse_timeline(info["timeline"])
            if rng:
                e["year"] = (rng["start"] + rng["end"] + 1) / 2
            else:
                sm = re.search(r"\|\s*([\w]+)\s*\]\]", info["season"]) or re.search(r"\[\[[^\]]*?(\d+)\]\]", info["season"])
                n = sm and (NUMBER_WORDS.get(sm[1]) or (int(sm[1]) if sm[1].isdigit() else None))
                srng = seasons.get((e["work"], n))
                if srng:
                    pending.append((e, (srng["start"], srng["end"] + 1)))
                    continue
        if e["year"] is None and u:
            e["year"] = (u["start"] + u["end"] + 1) / 2 if w["kind"] == "series" and not w.get("segments") \
                else u.get("main", u["start"]) + 0.5  # books/games: their main period, not a flashback
    # spread runs of episodes that only know their season range
    i = 0
    while i < len(pending):
        j = i
        while j + 1 < len(pending) and pending[j + 1][1] == pending[i][1]:
            j += 1
        a, b = pending[i][1]
        run = pending[i:j + 1]
        for k, (e, _) in enumerate(run):
            e["year"] = round(a + (b - a) * (k + 0.5) / len(run), 3)
        i = j + 1


def main():
    overrides = json.loads((ROOT / "data" / "overrides.json").read_text())
    raws = [json.loads(f.read_text()) for f in sorted(RAW.glob("*.json"))]
    works = [build_work(raw, overrides) for raw in raws]
    works.sort(key=lambda x: x["release"]["start"] or "9999")
    resolve_posters(works)
    chars = build_characters(raws, works)
    (ROOT / "data" / "characters.json").write_text(json.dumps(
        {"generated": TODAY.isoformat(), "characters": chars}, ensure_ascii=False, separators=(",", ":")))
    out = {
        "generated": TODAY.isoformat(),
        "source": "Wookieepedia (starwars.fandom.com), CC BY-SA 3.0",
        "works": works,
    }
    (ROOT / "data" / "works.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for x in works:
        u = x.get("universe", {})
        print(f"{x['id']:18} {x['release']['start']} → {x['release']['end']}  {x['release']['status']:9}"
              f" | {u.get('start')}..{u.get('end')}{' ~' if u.get('approx') else ''}"
              f"  seasons={len(x.get('seasons', []))} markers={len(x.get('markers', []))}")


if __name__ == "__main__":
    main()
