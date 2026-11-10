"""Attach the rendered covers to staged posts: reels get cover_url, carousels get the cover as slide 01.
Usage: python covers/attach_covers.py --media-repo ../english-reels-media [--from 2026-11-11 --to 2026-11-18]"""
import argparse, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
COVERS = (ROOT / ".." / ".." / "outputs" / "english-reels-samples" / "covers").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"

ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True)
ap.add_argument("--from", dest="start", default="2026-11-11"); ap.add_argument("--to", dest="end", default="2026-11-18")
a = ap.parse_args(); media = Path(a.media_repo).resolve()
q = json.loads(QUEUE.read_text(encoding="utf-8")); done = 0
for i in q["items"]:
    if i.get("review_status") != "staged" or not (a.start <= i["date"] <= a.end) or i["format"] not in ("REELS", "CAROUSEL"):
        continue
    cover = COVERS / f"{i['id']}.jpg"
    if not cover.exists():
        print("no cover:", i["id"]); continue
    m = i.setdefault("media", {})
    if i["format"] == "REELS":
        folder = media / m["video_url"][len(BASE) + 1:].rsplit("/", 1)[0]
        shutil.copy(cover, folder / "cover.jpg")
        m["cover_url"] = f"{BASE}/{folder.name}/cover.jpg"
    else:
        first = m["slides"][0]
        shutil.copy(cover, media / first[len(BASE) + 1:])
    done += 1
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(done, "covers attached")
