"""Emotional stories (feelstory): one reel a day at 22:00 from --start, approved by the owner.
Same URLs on re-runs; the queue is re-read just before writing.
Usage: python publish/plan_feelstory.py --media-repo ../english-reels-media [--render] [--start 2026-11-18]"""
import argparse, datetime as dt, json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
ORDER = ["dog-window", "teacher", "old-coat", "lunchbox", "grandma"]
TAGS = "#learnenglish #անգլերեն #անգլերենիդասեր #EnglishStories #Yerevan"
TAIL = ("Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n" + TAGS)


def caption(s):
    en = "\n".join(" ".join(sc).replace("[", "").replace("]", "") for sc in s["scenes"])
    hy = "\n".join(" ".join(sc) for sc in s["scenes_hy"])
    words = sorted({m for sc in s["scenes"] for l in sc for m in re.findall(r"\[([^\]]+)\]", l)}, key=str.lower)
    return (f"{s['title_hy']} · {s['title']} · {s['level']}\n\nՄի կարճ պատմություն, որ կարդում ենք անգլերեն։\n\n{en}\n\n"
            f"Թարգմանություն՝\n{hy}\n\nԸնդգծված արտահայտություններ՝ {', '.join(words)}\n\n"
            "Լսի՛ր, հետևի՛ր բառերին, ապա կարդա՛ բարձրաձայն։\nՈւղարկի՛ր մեկին, ում այսօր պետք է այս պատմությունը։\n\n" + TAIL)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--render", action="store_true")
    ap.add_argument("--start", default="2026-11-18"); ap.add_argument("--time", default="22:00"); ap.add_argument("--only", nargs="*")
    ap.add_argument("--hold", action="store_true", help="queue as draft: nothing is published until the owner approves"); a = ap.parse_args()
    mrepo = Path(a.media_repo).resolve()
    data = {s["id"]: s for s in json.loads((ROOT / "reels/data/feelstory.json").read_text(encoding="utf-8"))["stories"]}
    new = []
    for k, i in enumerate(a.only or ORDER):   # --only keeps the given order (any story id, e.g. minute-...)
        day = (dt.date.fromisoformat(a.start) + dt.timedelta(days=k)).isoformat()
        if a.render: subprocess.run(["node", "reels/render_feelstory.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        rid = f"{day}-feelstory-{i}"; folder = mrepo / rid; folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"feelstory-{i}.mp4", folder / f"feelstory-{i}.mp4")
        media = {"video_url": f"{BASE}/{rid}/feelstory-{i}.mp4"}
        if (OUT / f"feelstory-{i}-cover.jpg").exists():   # a designed cover keeps the profile grid beautiful
            shutil.copy2(OUT / f"feelstory-{i}-cover.jpg", folder / "cover.jpg"); media["cover_url"] = f"{BASE}/{rid}/cover.jpg"
        new.append({"id": rid, "date": day, "time": a.time, "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS", "kind": "feelstory",
                    "content_id": i, "title": f"Story {data[i]['title']}", "caption": caption(data[i]), "review_status": "draft" if a.hold else "staged",
                    **({} if "cover_url" in media else {"thumb_offset": 4000}), "media": media})
        print("feelstory", day, i, flush=True)
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=ROOT, check=False)
    q = json.loads(QUEUE.read_text(encoding="utf-8")); ids = {x["id"] for x in new}
    q["items"] = [x for x in q["items"] if x["id"] not in ids] + new
    q["items"].sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
