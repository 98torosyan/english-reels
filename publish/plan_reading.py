"""Daily reading: render each illustrated story, copy it to the public repo and schedule one a day at 10:30 Asia/Yerevan.
Usage: python publish/plan_reading.py --media-repo ../english-reels-media --start 2026-11-13 [--only id ...] [--ahead]
With --ahead nothing is rendered now: each post carries item["render"] and "Render ahead" makes it two days before."""
import argparse, datetime as dt, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
REEL_AT = "10:30"


def caption(st):
    head = {"DID YOU KNOW?": "Գիտե՞իր · Did you know?", "STORY TIME": "Պատմության ժամ · Story time"}.get(st.get("series"), "Կարդանք միասին · Daily reading")
    return (f"{head}\n{st['title']} · {st['title_hy']} ({st['level']})\n\n{st['en']}\n\n"
            f"Թարգմանություն՝\n{st['hy']}\n\n"
            "Լսի՛ր, հետևի՛ր ընդգծված բառերին, ապա կարդա՛ բարձրաձայն։\n"
            "Պահի՛ր, որ վաղը նորից կարդաս, և ուղարկի՛ր ընկերոջդ։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n"
            "#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր #EnglishReading #Yerevan")


def music(day_index):
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    return str(tracks[(day_index * 7 + 3) % len(tracks)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--start", required=True)
    ap.add_argument("--only", nargs="*"); ap.add_argument("--ahead", action="store_true"); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    lists = json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"]
    start = dt.date.fromisoformat(a.start)
    new = []
    chosen = [l for l in lists if not a.only or l["id"] in a.only]
    if a.only: chosen.sort(key=lambda l: a.only.index(l["id"]))   # the order given on the command line
    for k, l in enumerate(chosen):
        day = (start + dt.timedelta(days=k)).isoformat()
        track = music(k + 2); rid = f"{day}-reading-{l['id']}"
        if not a.ahead:
            subprocess.run(["node", "reels/render_reading.js", l["id"]], cwd=ROOT, check=True, env={**os.environ, "MUSIC_TRACK": track})
            rdir = media / rid; rdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OUT / f"reading-{l['id']}.mp4", rdir / f"reading-{l['id']}.mp4")
            Image.open(OUT / f"reading-{l['id']}.png").convert("RGB").save(rdir / "cover.jpg", "JPEG", quality=92)
        new.append({"id": rid, "date": day, "time": REEL_AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                           "kind": "reading", "content_id": l["id"], "title": f"Daily reading {l['number']:02d}", "caption": caption(l),
                           "review_status": "staged", "thumb_offset": 1400,
                           **({"render": {"reading": l["id"], "music": Path(track).name}} if a.ahead else {}),
                           "media": {"video_url": f"{BASE}/{rid}/reading-{l['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
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
