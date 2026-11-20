"""Give every reel and carousel its own Story half an hour later: the post's picture full screen with a slow camera
move, the gold book frame, the title, a one-line hook (the post's first sentence) and music (tools/story_card.py,
rendered two days ahead by "Render ahead"). Posts that already have their Story are skipped.
Usage: python publish/plan_story_cards.py [--from YYYY-MM-DD] [--dry-run]"""
import argparse, datetime as dt, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
BASE = "https://98torosyan.github.io/english-reels-media"
GAP = 30   # minutes after the post


def data(name):
    d = json.loads((ROOT / "reels" / "data" / f"{name}.json").read_text(encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("stories") or d.get("items") or []
    return {x["id"]: x for x in items if isinstance(x, dict) and "id" in x}


def clean(s): return re.sub(r"\s+", " ", re.sub(r"[\[\]‘’“”]", "", s)).strip()


def hook_of(text):
    """The first sentence (or two short ones), at most ~64 letters, broken into two lines near the middle."""
    parts = re.findall(r"[^.!?]+[.!?]", clean(text)) or [clean(text)]
    h = parts[0].strip()
    if len(h) < 26 and len(parts) > 1 and len(h) + len(parts[1]) < 64: h += " " + parts[1].strip()
    if len(h) > 64: h = h[:64].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    words = h.split(); best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(h) / 2), default=0)
    return " ".join(words[:best]) + "\n" + " ".join(words[best:]) if best else h


def card_for(item, src):
    kind, cid = item.get("kind"), item.get("content_id")
    pic = title = text = None; author = "A STORY IN EASY ENGLISH"; music = (item.get("render") or {}).get("music"); line = None
    if kind == "reading" and cid in src["reading"]:
        r = src["reading"][cid]; title, text = r["title"], r.get("en", ""); author = r.get("series") or "DAILY READING"
        pic = next((p for p in (f"assets/reading/{cid}/1.jpg", r.get("picture") and f"assets/{r['picture']}") if p and (ROOT / p).exists()), None)
        music = music or r.get("music")
    elif kind in ("feelstory", "countries") and cid in src["feelstory"]:
        s = src["feelstory"][cid]; title = s["title"]; text = " ".join(s["scenes"][0]); music = music or s.get("music")
        author = (s.get("series") or ("ANI'S TRAVELS" if kind == "countries" else "A SHORT STORY")).upper()
        pic = f"assets/{s['pics'][0]}" if s.get("pics") else f"assets/{s.get('pics_dir') or 'feelstory/' + cid}/1.jpg"
    elif kind in ("storyvideo", "classic") and cid in src["storyvideo"]:
        s = src["storyvideo"][cid]; title = s["title"]; sc = s["scenes"][0]; text = sc if isinstance(sc, str) else " ".join(sc)
        author = "A CLASSIC STORY" if kind == "classic" or s.get("classic") else "A STORY IN EASY ENGLISH"; music = music or s.get("music")
        pic = f"assets/storyvideo/{cid}/1.jpg"
        if item["format"] == "CAROUSEL": line = "SWIPE AND READ IN EASY ENGLISH"
    if not (pic and title and text and (ROOT / pic).exists()): return None
    music = "music/" + (music or "new/piano-glow.m4a").removeprefix("music/")
    if not (ROOT / music).exists(): music = "music/new/piano-glow.m4a"
    card = {"picture": pic, "title": clean(title), "author": author, "hook": hook_of(text), "music": music}
    if line: card["line"] = line
    return card


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="start"); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    start = a.start or dt.date.today().isoformat()
    q = json.loads(QUEUE.read_text(encoding="utf-8")); items = q["items"]
    src = {k: data(k) for k in ("reading", "feelstory", "storyvideo")}
    have = {(i.get("content_id"), i["date"]) for i in items if i["format"] == "STORIES" and i.get("kind") == "story-video"}
    taken = {(i["date"], i["time"]) for i in items}
    added = []
    for it in sorted(items, key=lambda x: (x["date"], x["time"])):
        if it["date"] < start or it["format"] not in ("REELS", "CAROUSEL") or it.get("review_status") not in ("staged", "draft"): continue
        if it.get("kind") == "motion" or (it.get("content_id"), it["date"]) in have: continue
        card = card_for(it, src)
        if not card: print("no picture/text for", it["id"]); continue
        t = dt.datetime.strptime(it["time"], "%H:%M") + dt.timedelta(minutes=GAP)
        while (it["date"], t.strftime("%H:%M")) in taken: t += dt.timedelta(minutes=5)
        sid = f"{it['date']}-story-{it['content_id']}"
        new = {"id": sid, "date": it["date"], "time": t.strftime("%H:%M"), "timezone": it.get("timezone", "Asia/Yerevan"), "type": "STORY",
               "format": "STORIES", "kind": "story-video", "content_id": it["content_id"], "title": f"{card['title']} story", "caption": "",
               "review_status": "staged", "render": {"story_card": card}, "media": {"video_url": f"{BASE}/{sid}/story.mp4"}}
        items.append(new); taken.add((new["date"], new["time"])); added.append(new)
        print(new["date"], new["time"], card["title"], "|", card["hook"].replace("\n", " / "))
    if a.dry_run or not added: return
    items.sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(added), "stories added")


if __name__ == "__main__":
    main()
