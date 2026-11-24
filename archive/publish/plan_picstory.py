"""Picture-story carousels: render every story, copy the slides to the public repo and schedule one a day at 16:30 (Asia/Yerevan).
Usage: python publish/plan_picstory.py --media-repo ../english-reels-media --start 2026-11-13 [--only id ...]"""
import argparse, datetime as dt, json, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE = "https://98torosyan.github.io/english-reels-media"
AT, STORY_AT = "16:30", "16:50"


def caption(st):
    lines = "\n".join(f"{i}. {en}" for i, en in enumerate(st["scenes"], 1))
    words = "\n".join(f"{w['en']} {w['ipa']} — {w['hy']}" for w in st["words"])
    return (f"Անգլերեն պատմություն նկարներով · Picture story\n{st['title']} · {st['title_hy']} ({st['level']})\n\n{lines}\n\n"
            f"Նոր բառեր՝\n{words}\n\nՀարց՝ {st['question']}\nՊատասխանի՛ր անգլերեն մեկնաբանություններում։\n\n"
            "Պահի՛ր, որ վաղը նորից կարդաս, և ուղարկի՛ր ընկերոջդ։\n\n"
            "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։\nԱմբողջական դասերը ձայնով՝ bio-ի հղումով։\n\n"
            "#learnenglish #անգլերեն #անգլերենիդասեր #EnglishStories #Yerevan")


def alt_texts(st):
    """One description per slide, in English: Instagram uses alt text for search and screen readers."""
    words = ", ".join(w["en"] for w in st["words"])
    return ([f"Cover of the picture story \"{st['title']}\", an illustrated English reading lesson ({st['level']}) by Gayane Torosyan."]
            + [f"Illustration {n} of 6: {s}" for n, s in enumerate(st["scenes"], 1)]
            + [f"New words from the story: {words}. Question: {st['question']}"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--start", required=True)
    ap.add_argument("--only", nargs="*"); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); start = dt.date.fromisoformat(a.start)
    stories = json.loads((ROOT / "carousels/data/picture_stories.json").read_text(encoding="utf-8"))["stories"]
    new = []
    for st in stories:
        if a.only and st["id"] not in a.only: continue
        day = (start + dt.timedelta(days=st["number"] - 1)).isoformat()
        subprocess.run(["node", "carousels/render_picstory.js", st["id"]], cwd=ROOT, check=True, env=os.environ)
        iid = f"{day}-picstory-{st['id']}"; folder = media / iid
        if folder.exists(): shutil.rmtree(folder)
        shutil.copytree(OUT / f"picstory-{st['id']}", folder)
        slides = sorted(p.name for p in folder.glob("[0-9][0-9].jpg"))
        new.append({"id": iid, "date": day, "time": AT, "timezone": "Asia/Yerevan", "type": "CAROUSEL", "format": "CAROUSEL", "kind": "picstory",
                    "content_id": st["id"], "title": f"Picture story {st['number']:02d}", "caption": caption(st), "review_status": "staged",
                    "media": {"slides": [f"{BASE}/{iid}/{s}" for s in slides], "alt_texts": alt_texts(st)}})
        # a story the same afternoon sends story viewers to the new carousel
        sid = f"{day}-story-picstory-{st['id']}"; sfolder = media / sid; sfolder.mkdir(exist_ok=True)
        if (folder / "story.jpg").exists():
            shutil.move(str(folder / "story.jpg"), sfolder / "story.jpg")
        new.append({"id": sid, "date": day, "time": STORY_AT, "timezone": "Asia/Yerevan", "type": "STORY", "format": "STORIES",
                    "kind": "story-image", "content_id": f"picstory-{st['id']}", "title": f"Picture story {st['number']:02d} story", "caption": "",
                    "review_status": "staged", "media": {"image_url": f"{BASE}/{sid}/story.jpg"}})
        print("scheduled", day, st["id"], len(slides), "slides + story")
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=ROOT, check=False)
    q = json.loads(QUEUE.read_text(encoding="utf-8")); ids = {i["id"] for i in new}
    q["items"] = [i for i in q["items"] if i["id"] not in ids] + new
    q["items"].sort(key=lambda i: (i["date"], i["time"], i["id"]))
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
