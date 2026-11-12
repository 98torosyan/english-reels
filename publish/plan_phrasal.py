"""Phrasal verbs: render every set, copy the media to the public repo and schedule a reel + story every other day.
Usage: python publish/plan_phrasal.py --media-repo ../english-reels-media --start 2026-11-14 [--only id ...]
Reel at 13:30, story (the same cards as a still image) at 17:30, Asia/Yerevan."""
import argparse, datetime as dt, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
REEL_AT, STORY_AT = "13:30", "17:30"


def caption(l):
    rows = "\n\n".join(f"{it['en']} — {it['hy']}\n{it['example']}\n{it['example_hy']}" for it in l["items"])
    return (f"Phrasal verbs · {l['verb'].lower()}\n4 դարձված՝ «{l['verb'].lower()}» բայով ({l['level']})\n\n{rows}\n\n"
            "Լսի՛ր, ապա բարձրաձայն կրկնի՛ր յուրաքանչյուր նախադասությունը։\n"
            "Պահի՛ր, որ չկորցնես, և ուղարկի՛ր ընկերոջդ, ով անգլերեն է սովորում։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\n\n"
            "#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր #PhrasalVerbs #Yerevan")


def music(day_index):
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    return str(tracks[(day_index * 7 + 3) % len(tracks)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--start", required=True)
    ap.add_argument("--only", nargs="*"); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    lists = json.loads((ROOT / "reels/data/phrasal.json").read_text(encoding="utf-8"))["sets"]
    new = []
    start = dt.date.fromisoformat(a.start)
    for k, l in enumerate(lists):
        if a.only and l["id"] not in a.only: continue
        day = (start + dt.timedelta(days=2 * k)).isoformat()
        env = {**os.environ, "MUSIC_TRACK": music(k + 5)}
        subprocess.run(["node", "reels/render_phrasal.js", l["id"]], cwd=ROOT, check=True, env=env)
        rid, sid = f"{day}-phrasal-{l['id']}", f"{day}-story-phrasal-{l['id']}"
        rdir, sdir = media / rid, media / sid
        rdir.mkdir(parents=True, exist_ok=True); sdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"phrasal-{l['id']}.mp4", rdir / f"phrasal-{l['id']}.mp4")
        Image.open(OUT / f"phrasal-{l['id']}.png").convert("RGB").save(rdir / "cover.jpg", "JPEG", quality=92)
        shutil.copy2(OUT / f"phrasal-{l['id']}-story.jpg", sdir / "story.jpg")
        new.append({"id": rid, "date": day, "time": REEL_AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                           "kind": "phrasal", "content_id": l["id"], "title": f"Phrasal verbs {l['number']:02d}", "caption": caption(l),
                           "review_status": "staged", "thumb_offset": 1900,
                           "media": {"video_url": f"{BASE}/{rid}/phrasal-{l['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
        new.append({"id": sid, "date": day, "time": STORY_AT, "timezone": "Asia/Yerevan", "type": "STORY", "format": "STORIES",
                           "kind": "story-image", "content_id": f"phrasal-{l['id']}", "title": f"Phrasal verbs {l['number']:02d} story", "caption": "",
                           "review_status": "staged", "media": {"image_url": f"{BASE}/{sid}/story.jpg"}})
        print("scheduled", day, l["id"])
    # re-read the queue just before writing: the publisher may have updated it while we rendered
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=ROOT, check=False)
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    ids = {i["id"] for i in new}
    q["items"] = [i for i in q["items"] if i["id"] not in ids] + new
    q["items"].sort(key=lambda i: (i["date"], i["time"], i["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
