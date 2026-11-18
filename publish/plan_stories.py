"""Put the finished, held story reels (reels/data/stories_ready.json, status "held") into the queue, one per evening at
21:00 Yerevan on the first free evenings. The video itself stays on the motion-clips branch until two days before the
post, when "Render ahead" copies it to the public media site (item["render"] = {"motion": id}).
Usage: python publish/plan_stories.py [--start YYYY-MM-DD] [--only id ...] [--dry-run]"""
import argparse, datetime as dt, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE, READY, TALK = ROOT / "queue.json", ROOT / "reels/data/stories_ready.json", ROOT / "reels/data/talk.json"
BASE = "https://98torosyan.github.io/english-reels-media"
AT = "21:00"
DEFAULT_TAGS = ["learnenglish", "englishstories", "englishreading", "readinenglish", "englishlearning"]


def caption(t):
    lines = [l for sc in t["scenes"] for _, l in sc["lines"]][1:]   # the first line is the spoken title
    q = t.get("question") or "Did you like the ending? Tell us in English!"
    tags = " ".join("#" + h for h in (t.get("hashtags") or DEFAULT_TAGS))
    return f"{t['title']} · A story in English · {t.get('level', 'A2')}\n\nRead and listen.\n\n" + "\n".join(lines) + \
           f"\n\n{q}\nSave this reel and read it again tomorrow.\n\n{tags}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--start"); ap.add_argument("--only", nargs="*"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ready = json.loads(READY.read_text()) if READY.exists() else []
    talks = {t["id"]: t for t in json.loads(TALK.read_text(encoding="utf-8"))["talks"]}
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    busy = {i["date"] for i in q["items"] if i["time"] == AT and i.get("review_status") in ("staged", "published", "draft")}
    day = dt.date.fromisoformat(a.start) if a.start else dt.date.today() + dt.timedelta(days=1)
    planned = []
    for r in ready:
        if r.get("status") != "held" or (a.only and r["id"] not in a.only) or r["id"] not in talks: continue
        while day.isoformat() in busy: day += dt.timedelta(days=1)
        t = talks[r["id"]]; rid = f"{day.isoformat()}-motion-{r['id']}"
        q["items"].append({"id": rid, "date": day.isoformat(), "time": AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                           "kind": "motion", "content_id": r["id"], "title": t["title"], "caption": caption(t), "review_status": "staged",
                           "render": {"motion": r["id"]},
                           "media": {"video_url": f"{BASE}/{rid}/motion-{r['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
        r["status"] = "queued"; r["post"] = rid; busy.add(day.isoformat()); planned.append((day.isoformat(), t["title"]))
    for d, title in planned: print(d, AT, title)
    if a.dry_run or not planned: return
    q["items"].sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    READY.write_text(json.dumps(ready, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
