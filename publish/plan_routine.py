"""My day: render each daily-routine reel, copy it to the public repo and schedule one a day at 17:45 Asia/Yerevan.
Usage: python publish/plan_routine.py --media-repo ../english-reels-media --start 2026-11-14 [--only id ...]"""
import argparse, datetime as dt, json, os, re, shutil, subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
AT = "17:45"


def music(day_index):
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    return str(tracks[(day_index * 5 + 4) % len(tracks)])


def caption(st):
    rows = "\n".join(f"{re.sub(r'[\[\]]', '', en)} — {hy}" for en, hy in zip(st["lines"], st["lines_hy"]))
    phrases = ", ".join(re.findall(r"\[([^\]]+)\]", " ".join(st["lines"])))
    return (f"Անգլերեն ամեն օր · {st['title_hy']}\nMy day · {st['title']} ({st['level']})\n\n{st['question']}\n{st['question_hy']}\n\n{rows}\n\n"
            f"Կարևոր արտահայտություններ՝ {phrases}\n\n"
            "Լսի՛ր, կրկնի՛ր յուրաքանչյուր նախադասությունը, ապա պատմի՛ր քո օրվա մասին։\n"
            "Պահի՛ր, որ չկորցնես, և ուղարկի՛ր ընկերոջդ։\n\n"
            f"{st['question']} Պատասխանի՛ր անգլերեն մեկնաբանություններում։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n"
            "#learnenglish #անգլերեն #անգլերենիդասեր #SpokenEnglish #Yerevan")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--start", required=True)
    ap.add_argument("--only", nargs="*"); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); start = dt.date.fromisoformat(a.start)
    stories = json.loads((ROOT / "reels/data/routine.json").read_text(encoding="utf-8"))["stories"]
    new = []
    for k, st in enumerate(stories):
        if a.only and st["id"] not in a.only: continue
        day = (start + dt.timedelta(days=k)).isoformat()
        subprocess.run(["node", "reels/render_routine.js", st["id"]], cwd=ROOT, check=True, env={**os.environ, "MUSIC_TRACK": music(k)})
        rid = f"{day}-routine-{st['id']}"; rdir = media / rid; rdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"routine-{st['id']}.mp4", rdir / f"routine-{st['id']}.mp4")
        Image.open(OUT / f"routine-{st['id']}.png").convert("RGB").save(rdir / "cover.jpg", "JPEG", quality=92)
        new.append({"id": rid, "date": day, "time": AT, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS", "kind": "routine",
                    "content_id": st["id"], "title": f"My day {st['number']:02d}", "caption": caption(st), "review_status": "staged",
                    "media": {"video_url": f"{BASE}/{rid}/routine-{st['id']}.mp4", "cover_url": f"{BASE}/{rid}/cover.jpg"}})
        print("scheduled", day, st["id"])
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=ROOT, check=False)
    q = json.loads(QUEUE.read_text(encoding="utf-8")); ids = {i["id"] for i in new}
    q["items"] = [i for i in q["items"] if i["id"] not in ids] + new
    q["items"].sort(key=lambda i: (i["date"], i["time"], i["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
