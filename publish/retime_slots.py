"""Align every unpublished post from 11 Nov to the daily wake-up slots (:30 at 11, 12, 18, 19, 21 Yerevan)
and switch word/phrase stories to their voiced videos."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
BASE = "https://98torosyan.github.io/english-reels-media"
SLOTS = ["11:30", "12:30", "18:30", "19:30", "21:30"]
q = json.loads(QUEUE.read_text(encoding="utf-8")); items = q["items"]
for i in items:
    if i["date"] < "2026-11-11" or i.get("review_status") == "published":
        continue
    t = i["time"]
    if t not in SLOTS:
        h, m = map(int, t.split(":"))
        mins = h * 60 + m
        best = min(SLOTS, key=lambda s: (abs(int(s[:2]) * 60 + int(s[3:]) - mins), -int(s[:2])))
        i["time"] = best
    m = re.fullmatch(r"([wp])-(2026-11-1[1-7])", i.get("content_id", ""))
    if i["format"] == "STORIES" and m:
        i["media"] = {"video_url": f"{BASE}/{m[2]}-stories/story-{m[1]}-{m[2]}.mp4"}
        i["review_status"] = "staged"
items.sort(key=lambda i: (i["date"], i["time"], i["id"]))
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ok")
