"""Just-in-time media: for staged posts due within --days days whose files are not in the media repo yet, render them
and put them in place. Posts say how in item["render"]: {"reel": "<feelstory id>"}, {"countries": "<country id>"} or
{"motion": "<story id>"}, {"storyvideo": "<story id>"} (a finished story reel kept on the motion-clips branch: only copied, not rendered) or
{"story_card": {...}} (a Story video for a reel, tools/story_card.py).
This keeps the public media site small (only the next few days live there) and needs no computer: the daily
"Render ahead" workflow runs it. Usage: python tools/render_ahead.py --media-repo ../english-reels-media [--days 3]"""
import argparse, datetime as dt, json, os, shutil, subprocess
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
    elif "reading" in spec:
        i = spec["reading"]; env = {**os.environ}
        if spec.get("living"):   # living pictures: soft depth movement made from the stills (tools/living_pictures.py)
            live = ROOT / ".render-work" / "live" / i; shutil.rmtree(live, ignore_errors=True)
            subprocess.run(["python", str(ROOT / "tools" / "living_pictures.py"), i, str(live)], cwd=ROOT, check=True); env["LIVE"] = "1"
        if spec.get("music"): env["MUSIC_TRACK"] = str(ROOT / "music" / spec["music"])
        subprocess.run(["node", "reels/render_reading.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, env=env)
        shutil.copy2(OUT / f"reading-{i}.mp4", folder / f"reading-{i}.mp4")
        from PIL import Image
        Image.open(OUT / f"reading-{i}.png").convert("RGB").save(folder / "cover.jpg", "JPEG", quality=92)
    elif "motion" in spec:
        i = spec["motion"]
        subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "motion-clips"], cwd=ROOT, check=True)
        for name, dest in ((f"finished/motion-{i}.mp4", f"motion-{i}.mp4"), (f"finished/motion-{i}-cover.jpg", "cover.jpg")):
            data = subprocess.run(["git", "show", f"FETCH_HEAD:{name}"], cwd=ROOT, check=True, capture_output=True).stdout
            (folder / dest).write_bytes(data)
    elif "story_card" in spec:   # a Story video for a reel (tools/story_card.py); picture "motion:<id>:<n>" = a frame of that clip
        c = dict(spec["story_card"]); work = folder / ".card"; work.mkdir(exist_ok=True)
        if c["picture"].startswith("motion:"):
            _, sid, n = c["picture"].split(":")
            subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "motion-clips"], cwd=ROOT, check=True)
            for name in (f"{sid}/out-{sid}-{n}.mp4", f"{sid}/out-{n}.mp4"):
                r = subprocess.run(["git", "show", f"FETCH_HEAD:{name}"], cwd=ROOT, capture_output=True)
                if r.returncode == 0: (work / "clip.mp4").write_bytes(r.stdout); break
            else: raise SystemExit(f"no clip {sid}/{n} on motion-clips")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(work / "clip.mp4"), "-frames:v", "1", "-q:v", "2", str(work / "pic.jpg")], check=True)
            c["picture"] = str(work / "pic.jpg")
        else: c["picture"] = str(ROOT / c["picture"])
        (work / "spec.json").write_text(json.dumps(c), encoding="utf-8")
        subprocess.run(["python", str(ROOT / "tools" / "story_card.py"), str(work / "spec.json"), str(folder / "story.mp4")], cwd=ROOT, check=True)
        shutil.rmtree(work)
    elif "storyvideo" in spec:   # classics and story-time reels (reels/render_storyvideo.js)
        i = spec["storyvideo"]
        subprocess.run(["node", "reels/render_storyvideo.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        shutil.copy2(OUT / f"storyvideo-{i}.mp4", folder / Path(item["media"]["video_url"]).name)
        if item["media"].get("cover_url") and not (folder / "cover.jpg").exists():
            from PIL import Image
            Image.open(OUT / f"storyvideo-{i}.png").convert("RGB").save(folder / "cover.jpg", "JPEG", quality=92)
    elif "countries" in spec:
        i = spec["countries"]
        subprocess.run(["node", "carousels/render_countries.js", i], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        for f in (OUT / f"countries-{i}").iterdir():
            if f.suffix in (".mp4", ".jpg") and "poster" not in f.name: shutil.copy2(f, folder / f.name)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--only", nargs="*", help="render these item ids whatever their date"); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); today = dt.date.today()
    items = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]; failed = []
    for it in items:
        if not it.get("render") or it.get("review_status") not in ("staged", "draft"): continue
        if a.only is not None:
            if it["id"] not in a.only: continue
        elif it["review_status"] != "staged" or not 0 <= (dt.date.fromisoformat(it["date"]) - today).days <= a.days: continue
        missing = [f for f in files_for(it) if not (media / f).exists()]
        if not missing and a.only is None: continue   # --only renders again even when the files are there (design changes)
        print("render", it["id"], flush=True)
        try:
            render(it, media)
        except Exception as e:   # one broken post must not stop the others
            failed.append(f"{it['id']}: {e}"); continue
        still = [f for f in files_for(it) if not (media / f).exists()]
        if still: failed.append(f"{it['id']}: still missing {still}")
    if failed: raise SystemExit("Not rendered:\n" + "\n".join(failed))


if __name__ == "__main__":
    main()
