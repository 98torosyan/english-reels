"""Ani's travels: seven city stories in English only, one every two days at 15:00 Asia/Yerevan.
Media is rendered just in time (item["render"], tools/render_ahead.py), so nothing waits on a computer.
Usage: python publish/plan_cities.py --start 2026-11-20"""
import argparse, datetime as dt, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
BASE = "https://98torosyan.github.io/english-reels-media"
ORDER = ["london", "paris", "new-york", "venice", "tokyo", "prague", "dubai"]
AT = "15:00"


def caption(s):
    lines = [l.replace("[", "").replace("]", "") for sc in s["scenes"] for l in sc]
    phrases = [p for sc in s["scenes"] for l in sc for p in re.findall(r"\[([^\]]+)\]", l)]
    useful = [p for p in phrases if p[:1].isupper() and (" " in p) and any(w in p.lower() for w in ("please", "how much", "could", "can i", "it's"))]
    text = "\n".join(lines)
    out = f"{s['title']} · Ani's travels · {s['level']}\n\nRead, listen and travel with Ani.\n\n{text}"
    if useful: out += "\n\nUseful phrases:\n" + "\n".join(f"• {p}" for p in useful)
    return out + "\n\nWhere should Ani go next? Tell us in the comments!\nSave this reel and read it again tomorrow."


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--start", required=True); a = ap.parse_args()
    stories = {s["id"]: s for s in json.loads((ROOT / "reels/data/feelstory.json").read_text(encoding="utf-8"))["stories"]}
    q = json.loads(QUEUE.read_text(encoding="utf-8")); start = dt.date.fromisoformat(a.start); new = []
    for k, c in enumerate(ORDER):
        i = f"city-{c}"; s = stories[i]; day = (start + dt.timedelta(days=2 * k)).isoformat(); rid = f"{day}-cities-{c}"
        new.append({"id": rid, "date": day, "time": AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS", "kind": "countries",
                    "content_id": i, "title": f"Story {s['title']}", "caption": caption(s), "review_status": "staged", "render": {"reel": i},
                    "media": {"video_url": f"{BASE}/{rid}/feelstory-{i}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
    ids = {x["id"] for x in new}; cids = {x["content_id"] for x in new}
    q["items"] = [x for x in q["items"] if x["id"] not in ids and not (x.get("content_id") in cids and x.get("review_status") == "staged")] + new
    q["items"].sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for x in new: print(x["date"], x["time"], x["id"])


if __name__ == "__main__":
    main()
