"""10 words: render every list, copy the media to the public repo and schedule one reel + one story a day.
Usage: python publish/plan_words10.py --media-repo ../english-reels-media --start 2026-11-12 [--only id ...]
Reel at 20:30, story (the same list as a still image) at 14:30, Asia/Yerevan."""
import argparse, datetime as dt, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
REEL_AT, STORY_AT = "20:30", "14:30"


def caption(l):
    rows = "\n".join(f"{w['en']} {w['ipa']} — {w['hy']}" for w in l["words"])
    return (f"10 բառ · {l['theme_hy']}\n10 words · {l['theme']} ({l['level']})\n\n{rows}\n\n"
            "Լսի՛ր և կրկնի՛ր յուրաքանչյուր բառը։\n"
            "Պահի՛ր, որ չկորցնես, և ուղարկի՛ր ընկերոջդ, ով անգլերեն է սովորում։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\n\n"
            "#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր #EnglishVocabulary #Yerevan")


def music(day_index):
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    return str(tracks[(day_index * 7 + 3) % len(tracks)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--start", required=True)
    ap.add_argument("--only", nargs="*"); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    lists = json.loads((ROOT / "reels/data/words10.json").read_text(encoding="utf-8"))["lists"]
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    start = dt.date.fromisoformat(a.start)
    for k, l in enumerate(lists):
        if a.only and l["id"] not in a.only: continue
        day = (start + dt.timedelta(days=k)).isoformat()
        env = {**os.environ, "MUSIC_TRACK": music(k)}
        subprocess.run(["node", "reels/render_words10.js", l["id"]], cwd=ROOT, check=True, env=env)
        rid, sid = f"{day}-words10-{l['id']}", f"{day}-story-words10-{l['id']}"
        rdir, sdir = media / rid, media / sid
        rdir.mkdir(parents=True, exist_ok=True); sdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"words10-{l['id']}.mp4", rdir / f"words10-{l['id']}.mp4")
        Image.open(OUT / f"words10-{l['id']}.png").convert("RGB").save(rdir / "cover.jpg", "JPEG", quality=92)
        shutil.copy2(OUT / f"words10-{l['id']}-story.jpg", sdir / "story.jpg")
        q["items"] = [i for i in q["items"] if i["id"] not in (rid, sid)]
        q["items"].append({"id": rid, "date": day, "time": REEL_AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                           "kind": "words10", "content_id": l["id"], "title": f"10 words {l['number']:02d}", "caption": caption(l),
                           "review_status": "staged", "thumb_offset": 1900,
                           "media": {"video_url": f"{BASE}/{rid}/words10-{l['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
        q["items"].append({"id": sid, "date": day, "time": STORY_AT, "timezone": "Asia/Yerevan", "type": "STORY", "format": "STORIES",
                           "kind": "story-image", "content_id": f"words10-{l['id']}", "title": f"10 words {l['number']:02d} story", "caption": "",
                           "review_status": "staged", "media": {"image_url": f"{BASE}/{sid}/story.jpg"}})
        print("scheduled", day, l["id"])
    q["items"].sort(key=lambda i: (i["date"], i["time"], i["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
