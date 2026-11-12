"""Weekly review: render each Sunday recap, copy it to the public repo and schedule it (reel only, 12:00 Asia/Yerevan, on its own date).
Usage: python publish/plan_review.py --media-repo ../english-reels-media [--only id ...]"""
import argparse, json, os, shutil, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
REEL_AT = "12:00"


def caption(r, w10):
    rows = "\n".join(f"{i}. {w10[lid]['words'][n]['hy']} → {w10[lid]['words'][n]['en']}" for i, (lid, n) in enumerate(r["picks"], 1))
    return ("Շաբաթվա կրկնություն · Weekly review\n\nՀիշո՞ւմ ես այս շաբաթվա բառերը։ Ասա՛ անգլերեն, մինչև պատասխանը կհայտնվի։\n\n"
            f"Պատասխանները՝\n{rows}\n\nԳրի՛ր մեկնաբանություններում՝ քանի՞սը գուշակեցիր 6-ից։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n"
            "#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր #EnglishVocabulary #Yerevan")


def music(day_index):
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    return str(tracks[(day_index * 7 + 3) % len(tracks)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); 
    ap.add_argument("--only", nargs="*"); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    lists = json.loads((ROOT / "reels/data/reviews.json").read_text(encoding="utf-8"))["reviews"]
    w10 = {l["id"]: l for l in json.loads((ROOT / "reels/data/words10.json").read_text(encoding="utf-8"))["lists"]}
    new = []
    for k, l in enumerate(lists):
        if a.only and l["id"] not in a.only: continue
        day = l["date"]
        env = {**os.environ, "MUSIC_TRACK": music(k + 11)}
        subprocess.run(["node", "reels/render_review.js", l["id"]], cwd=ROOT, check=True, env=env)
        rid = f"{day}-review-{l['id']}"
        rdir = media / rid; rdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"review-{l['id']}.mp4", rdir / f"review-{l['id']}.mp4")
        Image.open(OUT / f"review-{l['id']}.png").convert("RGB").save(rdir / "cover.jpg", "JPEG", quality=92)
        new.append({"id": rid, "date": day, "time": REEL_AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                           "kind": "review", "content_id": l["id"], "title": f"Weekly review {l['number']:02d}", "caption": caption(l, w10),
                           "review_status": "staged", "thumb_offset": 3700,
                           "media": {"video_url": f"{BASE}/{rid}/review-{l['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
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
