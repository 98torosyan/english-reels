"""Add the lessons call to action to every unpublished caption, replace ✕/✓ marks with words,
and schedule the 'Learn with Gayane' story. Safe to run more than once."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
BASE = "https://98torosyan.github.io/english-reels-media"
DM = "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։"
LINK = "Ամբողջական դասերը ձայնով՝ bio-ի հղումով։"

q = json.loads(QUEUE.read_text(encoding="utf-8"))
items = q["items"]
changed = 0
for i in items:
    if i.get("review_status") == "published" or i["format"] == "STORIES" or not i.get("caption"):
        continue
    c = i["caption"]
    c = re.sub(r"^✕ ", "Սխալ՝ ", c, flags=re.M)
    c = re.sub(r"^✓ ", "Ճիշտ՝ ", c, flags=re.M)
    if DM not in c:
        if LINK in c:
            c = c.replace(LINK, f"{DM}\n{LINK}", 1)
        else:
            head, _, tags = c.rpartition("\n\n#")
            c = f"{head}\n\n{DM}\n\n#{tags}" if head else f"{c}\n\n{DM}"
    if c != i["caption"]:
        i["caption"] = c; changed += 1

have = {i["id"] for i in items}
for day in ("11", "13", "15", "17"):
    iid = f"2026-11-{day}-story-dm-lessons"
    if iid not in have:
        items.append({"id": iid, "date": f"2026-11-{day}", "time": "20:30", "timezone": "Asia/Yerevan", "type": "STORY", "format": "STORIES",
                      "kind": "story-image", "content_id": "dm-lessons", "title": "dm-lessons", "caption": "", "review_status": "staged",
                      "media": {"image_url": f"{BASE}/dm-lessons/story-dm-lessons.jpg"}})
# daily word/phrase stories for 15–17 Nov: images are in <date>-stories/
for i in items:
    m = re.fullmatch(r"([wp])-(2026-11-1[567])", i.get("content_id", ""))
    if i["format"] == "STORIES" and m and i.get("review_status") == "approved":
        i["media"] = {"image_url": f"{BASE}/{m[2]}-stories/story-{m[1]}-{m[2]}.jpg"}
        i["review_status"] = "staged"
items.sort(key=lambda i: (i["date"], i["time"], i["id"]))
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{changed} caption(s) updated")
