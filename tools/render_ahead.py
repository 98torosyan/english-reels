"""Just-in-time media: for staged posts due within --days days whose files are not in the media repo yet, render them
and put them in place. Posts say how in item["render"]: {"reel": "<feelstory id>"}, {"countries": "<country id>"} or
{"motion": "<story id>"} (a finished story reel kept on the motion-clips branch: only copied, not rendered).
This keeps the public media site small (only the next few days live there) and needs no computer: the daily
"Render ahead" workflow runs it. Usage: python tools/render_ahead.py --media-repo ../english-reels-media [--days 3]"""
import argparse, datetime as dt, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()


def files_for(item):
    m = item["media"]
    return [u.split("english-reels-media/", 1)[1] for u in [m.get("video_url"), m.get("cover_url"), *(m.get("slides") or [])] if u]


def render(item, media):
    spec = item["render"]; folder = media / item["id"]; folder.mkdir(parents=True, exist_ok=True)
    if "reel" in spec:
        i = spec["reel"]
        subprocess.run(["node", "reels/render_feelstory.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        shutil.copy2(OUT / f"feelstory-{i}.mp4", folder / f"feelstory-{i}.mp4")
        if (OUT / f"feelstory-{i}-cover.jpg").exists(): shutil.copy2(OUT / f"feelstory-{i}-cover.jpg", folder / "cover.jpg")
    elif "motion" in spec:
        i = spec["motion"]
        subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "motion-clips"], cwd=ROOT, check=True)
        for name, dest in ((f"finished/motion-{i}.mp4", f"motion-{i}.mp4"), (f"finished/motion-{i}-cover.jpg", "cover.jpg")):
            data = subprocess.run(["git", "show", f"FETCH_HEAD:{name}"], cwd=ROOT, check=True, capture_output=True).stdout
            (folder / dest).write_bytes(data)
    elif "countries" in spec:
        i = spec["countries"]
        subprocess.run(["node", "carousels/render_countries.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        for f in (OUT / f"countries-{i}").iterdir():
            if f.suffix in (".mp4", ".jpg") and "poster" not in f.name: shutil.copy2(f, folder / f.name)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--only", nargs="*", help="render these item ids whatever their date"); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); today = dt.date.today()
    items = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    for it in items:
        if not it.get("render") or it.get("review_status") not in ("staged", "draft"): continue
        if a.only is not None:
            if it["id"] not in a.only: continue
        elif it["review_status"] != "staged" or not 0 <= (dt.date.fromisoformat(it["date"]) - today).days <= a.days: continue
        missing = [f for f in files_for(it) if not (media / f).exists()]
        if not missing: continue
        print("render", it["id"], flush=True); render(it, media)
        still = [f for f in files_for(it) if not (media / f).exists()]
        if still: raise SystemExit(f"{it['id']}: still missing {still}")


if __name__ == "__main__":
    main()
