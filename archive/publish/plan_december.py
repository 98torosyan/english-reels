"""December plan (approved by the owner on 2026-11-18): one post a day from Dec 8, rendered just in time by the
"Render ahead" workflow (tools/render_ahead.py), so the media site stays small and no computer is needed.
Usage: python publish/plan_december.py"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publish"))
from plan_feelstory import caption as reel_caption, TAIL   # noqa: E402

BASE = "https://98torosyan.github.io/english-reels-media"
QUEUE = ROOT / "queue.json"
PLAN = [  # date, kind, id, time
    ("2026-12-08", "reel", "rooftop-painter", "22:00"), ("2026-12-09", "reel", "country-uk", "21:00"),
    ("2026-12-10", "reel", "tiny-bakery", "22:00"), ("2026-12-11", "reel", "country-france", "21:00"),
    ("2026-12-12", "reel", "rabbit-maps", "22:00"), ("2026-12-13", "reel", "country-italy", "21:00"),
    ("2026-12-14", "reel", "paper-boat", "22:00"), ("2026-12-15", "reel", "country-japan", "21:00"),
    ("2026-12-16", "reel", "red-balloon", "22:00"), ("2026-12-17", "reel", "country-usa", "21:00"),
    ("2026-12-18", "reel", "fox-snow", "22:00"), ("2026-12-19", "reel", "country-armenia", "21:00"),
    ("2026-12-20", "carousel", "uk", "15:00"), ("2026-12-21", "carousel", "france", "15:00"),
    ("2026-12-22", "carousel", "italy", "15:00"), ("2026-12-23", "carousel", "japan", "15:00"),
    ("2026-12-24", "reel", "xmas-train", "20:00"), ("2026-12-25", "reel", "xmas-bear", "20:00"),
    ("2026-12-26", "carousel", "usa", "15:00"), ("2026-12-27", "carousel", "armenia", "15:00"),
]


def carousel_item(day, cid, time, c):
    rid = f"{day}-countries-{cid}"; en = "\n".join(s["en"].replace("[", "").replace("]", "") for s in c["slides"])
    hy = "\n".join(s["hy"] for s in c["slides"]); words = ", ".join(w for s in c["slides"] for w in __import__("re").findall(r"\[([^\]]+)\]", s["en"]))
    cap = (f"{c['name_hy']} · {c['name']} · {c['level']}\n\nՃամփորդում ենք աշխարհով և սովորում անգլերեն։ Թերթի՛ր, լսի՛ր, կարդա՛։\n\n{en}\n\n"
           f"Թարգմանություն՝\n{hy}\n\nԿարևոր բառեր՝ {words}\n\nՎերջին էջում՝ փոքրիկ հարց։ Պատասխանը գրի՛ր մեկնաբանություններում։\n\n" + TAIL)
    slides = [f"{BASE}/{rid}/{n:02d}.mp4" for n in range(1, 8)] + [f"{BASE}/{rid}/08.jpg"]
    alts = [f"Cover: {c['name']}, learn English and travel."] + [s["en"].replace("[", "").replace("]", "") for s in c["slides"]] + [f"Quiz: {c['quiz']['q']}"]
    return {"id": rid, "date": day, "time": time, "timezone": "Asia/Yerevan", "type": "CAROUSEL", "format": "CAROUSEL", "kind": "countries",
            "content_id": cid, "title": f"Countries {c['name']}", "caption": cap, "review_status": "staged",
            "render": {"countries": cid}, "media": {"slides": slides, "alt_texts": alts}}


def reel_item(day, i, time, s):
    rid = f"{day}-{'countries' if i.startswith('country-') else 'feelstory'}-{i}"
    return {"id": rid, "date": day, "time": time, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
            "kind": "countries" if i.startswith("country-") else "feelstory", "content_id": i, "title": f"Story {s['title']}",
            "caption": reel_caption(s), "review_status": "staged", "render": {"reel": i},
            "media": {"video_url": f"{BASE}/{rid}/feelstory-{i}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}}


def main():
    stories = {s["id"]: s for s in json.loads((ROOT / "reels/data/feelstory.json").read_text(encoding="utf-8"))["stories"]}
    countries = {c["id"]: c for c in json.loads((ROOT / "carousels/data/countries.json").read_text(encoding="utf-8"))["countries"]}
    new = [reel_item(d, i, t, stories[i]) if k == "reel" else carousel_item(d, i, t, countries[i]) for d, k, i, t in PLAN]
    q = json.loads(QUEUE.read_text(encoding="utf-8")); ids = {x["id"] for x in new}
    q["items"] = [x for x in q["items"] if x["id"] not in ids] + new
    q["items"].sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for x in new: print(x["date"], x["time"], x["id"])


if __name__ == "__main__":
    main()
