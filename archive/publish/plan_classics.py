"""Classics made easy: stage the classic story reels and the classic carousels, approved by the owner.
Reels daily at 17:30 from --reels-start; carousels daily at 14:00 from --carousels-start (at least a week after the reel of
the same story, never on the same day). Same URLs on re-runs; the queue is re-read just before writing.
Usage: python publish/plan_classics.py --media-repo ../english-reels-media [--render]"""
import argparse, datetime as dt, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
REELS = ["alice", "sherlock", "treasure-island", "happy-prince", "eighty-days", "little-women", "jack-beanstalk", "ali-baba",
         "selfish-giant", "don-quixote", "wizard-oz", "emperor-clothes", "christmas-carol"]
CAROUSELS = ["alice", "red-headed-league", "sherlock", "treasure-island", "happy-prince", "baskervilles", "eighty-days", "little-women",
             "jack-beanstalk", "ali-baba", "selfish-giant", "don-quixote", "wizard-oz", "emperor-clothes", "christmas-carol", "blue-carbuncle"]
TAGS = "#learnenglish #անգլերեն #անգլերենիդասեր #EnglishStories #Yerevan"
TAIL = ("Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n" + TAGS)


def reel_caption(s):
    c = s["classic"]
    return (f"Դասական գրականություն՝ պարզ անգլերենով · {s['title_hy']}\nClassics made easy · {s['title']} ({c['author']}, {c['year']}) · {s['level']}\n\n"
            f"{' '.join(s['scenes'])}\n\nԹարգմանություն՝\n{s['hy']}\n\n«{c['quote']}» — {c['author']}\n«{c['quote_hy']}»\n\n"
            "Լսի՛ր, հետևի՛ր ընդգծված բառերին, ապա կարդա՛ բարձրաձայն։\nՊահի՛ր և ուղարկի՛ր ընկերոջդ, ով սիրում է գրքեր։\n\n"
            "Կարդացե՞լ ես այս գիրքը։ Գրի՛ր մեկնաբանություններում։\n\n" + TAIL)


def carousel_caption(s):
    words = "\n".join(f"{w['en']} {w['ipa']} — {w['hy']}" for w in s["words"])
    ask = (f"{s['mystery']['question']} Գրի՛ր քո պատասխանը մեկնաբանություններում, հետո թերթի՛ր լուծումը տեսնելու համար։"
           if s.get("mystery") else "Կարդացե՞լ ես այս գիրքը։ Գրի՛ր մեկնաբանություններում։")
    return (f"Դասական գրականություն՝ պարզ անգլերենով · {s['title_hy']}\nClassics made easy · {s['title']} ({s['author']}, {s['year']}) · {s['level']}\n\n"
            f"Թերթի՛ր և կարդա՛ անգլերեն, հայերենը՝ օգնության համար։\n\nՆոր բառեր՝\n{words}\n\n«{s['quote']}» — {s['author']}\n\n{ask}\n\n" + TAIL)


def alt_texts(s):
    n = len(s["scenes"]); shown = n - 1 if s.get("mystery") else n
    alts = [f"Cover of \"{s['title']}\" by {s['author']}, a classic story retold in simple English (A2) for learners."]
    alts += [f"Illustration {i + 1}: {s['scenes'][i]}" for i in range(shown)]
    if s.get("mystery"): alts += [f"Question for the reader: {s['mystery']['question']}", f"The answer: {s['scenes'][-1]}"]
    alts.append(f"New words: {', '.join(w['en'] for w in s['words'])}. Famous line: {s['quote']}")
    return alts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--render", action="store_true")
    ap.add_argument("--reels-start", default="2026-11-15"); ap.add_argument("--carousels-start", default="2026-11-22"); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    sv = {s["id"]: s for s in json.loads((ROOT / "reels/data/storyvideo.json").read_text(encoding="utf-8"))["stories"]}
    cc = {s["id"]: s for s in json.loads((ROOT / "carousels/data/classic_carousels.json").read_text(encoding="utf-8"))["stories"]}
    new = []
    for k, i in enumerate(REELS):
        day = (dt.date.fromisoformat(a.reels_start) + dt.timedelta(days=k)).isoformat()
        if a.render: subprocess.run(["node", "reels/render_storyvideo.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        rid = f"{day}-classic-{i}"; folder = media / rid; folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / f"storyvideo-{i}.mp4", folder / f"classic-{i}.mp4")
        new.append({"id": rid, "date": day, "time": "17:30", "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS", "kind": "storyvideo",
                    "content_id": i, "title": f"Classic {sv[i]['title']}", "caption": reel_caption(sv[i]), "review_status": "staged", "thumb_offset": 1300,
                    "media": {"video_url": f"{BASE}/{rid}/classic-{i}.mp4"}})
        print("reel", day, i, flush=True)
    for k, i in enumerate(CAROUSELS):
        day = (dt.date.fromisoformat(a.carousels_start) + dt.timedelta(days=k)).isoformat()
        subprocess.run(["node", "carousels/render_classic.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        cid = f"{day}-classic-carousel-{i}"; folder = media / cid
        shutil.rmtree(folder, ignore_errors=True); shutil.copytree(OUT / f"classic-{i}", folder)
        slides = sorted(p.name for p in folder.glob("[0-9][0-9].jpg"))
        new.append({"id": cid, "date": day, "time": "14:00", "timezone": "Asia/Yerevan", "type": "CAROUSEL", "format": "CAROUSEL", "kind": "classic",
                    "content_id": i, "title": f"Classic carousel {cc[i]['title']}", "caption": carousel_caption(cc[i]), "review_status": "staged",
                    "media": {"slides": [f"{BASE}/{cid}/{s}" for s in slides], "alt_texts": alt_texts(cc[i])}})
        print("carousel", day, i, len(slides), flush=True)
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=ROOT, check=False)
    q = json.loads(QUEUE.read_text(encoding="utf-8")); ids = {x["id"] for x in new}
    q["items"] = [x for x in q["items"] if x["id"] not in ids] + new
    q["items"].sort(key=lambda x: (x["date"], x["time"], x["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
