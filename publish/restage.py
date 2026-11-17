"""Re-render already staged posts of the older series after a design change, replacing their files in the media repo
under the SAME names (same URLs). The queue is never touched, so nothing can be lost or published twice.
Usage: python publish/restage.py --media-repo ../english-reels-media --after "2026-11-14 18:00" [--kinds dialogue story ...]"""
import argparse, json, shutil, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publish"))
import stage_media  # noqa: E402
from rerender import push  # noqa: E402

KINDS = ["dialogue", "story", "mistake", "quiz", "word", "sound", "storyvideo", "rule"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--after", required=True); ap.add_argument("--before", default="9999")
    ap.add_argument("--kinds", nargs="*", default=KINDS); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); after = a.after
    q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))
    todo = [i for i in q["items"] if i.get("kind") in a.kinds and i.get("review_status") == "staged" and not i.get("published_at")
            and after <= f"{i['date']} {i['time']}" < a.before and i.get("format") == "REELS"]
    todo.sort(key=lambda i: (i["date"], i["time"]))
    for n, item in enumerate(todo, 1):
        want = [u.rsplit("/", 1)[1] for u in ([item["media"].get("video_url")] if item["media"].get("video_url") else item["media"].get("slides", []))]
        files = stage_media.render(item)
        names = [(f.stem + ".jpg") if f.suffix == ".png" else f.name for f in files]
        if names != want:
            print(f"SKIP {item['id']}: new files {names} differ from staged {want}"); continue
        target = media / item["id"]
        for f, name in zip(files, names):
            if f.suffix == ".png": Image.open(f).convert("RGB").save(target / name, "JPEG", quality=93, optimize=True)
            else: shutil.copy2(f, target / name)
        poster = files[0].with_suffix(".png")   # the reel's poster frame is also its grid cover
        if item["media"].get("cover_url", "").endswith("/cover.jpg") and poster.exists():
            Image.open(poster).convert("RGB").save(target / "cover.jpg", "JPEG", quality=92)
        print(f"{n}/{len(todo)} restaged {item['id']}", flush=True)
        if n % 4 == 0 or n == len(todo):
            push(media, f"Reels՝ մաքուր դիզայն ({n}/{len(todo)})")


if __name__ == "__main__":
    main()
