"""Render APPROVED queue items and copy their media into the public media repo.

Usage (run by the maintainer, never in CI):
    python publish/stage_media.py --media-repo ../english-reels-media [--ids ID ...]

Only items with review_status == "approved" are staged. Each staged item gets
`media` URLs in queue.json; the scheduled workflow then publishes it on its date.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
OUTPUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
BASE_URL = os.environ.get("MEDIA_BASE_URL", "https://98torosyan.github.io/english-reels-media").rstrip("/")


def music_env(item: dict) -> dict:
    """Rotate background tracks through the reel schedule so neighbouring reels never share music."""
    tracks = sorted((ROOT / "music").glob("*.m4a"))
    reels = sorted((i for i in json.loads(QUEUE.read_text(encoding="utf-8"))["items"] if i.get("format") == "REELS"),
                   key=lambda i: (i["date"], i["time"], i["id"]))
    idx = next((k for k, i in enumerate(reels) if i["id"] == item["id"]), 0)
    order = [tracks[(k * 5) % len(tracks)] for k in range(len(tracks))]  # step 5 mixes the two sets (16 tracks)
    return {**os.environ, "MUSIC_TRACK": str(order[idx % len(order)])}


def render(item: dict) -> list[Path]:
    kind, cid = item["kind"], item["content_id"]
    if kind == "story":
        m = re.fullmatch(r"(.+)-part-(\d)", cid)
        args, name = ["story", m.group(1), m.group(2)], f"story-{cid}"
    elif kind in {"mistake", "quiz", "word"}:
        args, name = [kind, cid], f"{kind}-{cid}"
    elif kind in {"sound", "dialogue", "words10", "phrasal", "review", "reading"}:
        subprocess.run(["node", f"reels/render_{kind}.js", cid], cwd=ROOT, check=True, env=music_env(item))
        return [OUTPUT / f"{kind}-{cid}.mp4"]
    elif kind == "rule":
        subprocess.run(["node", "carousels/render.js", cid], cwd=ROOT, check=True)
        return sorted((OUTPUT / f"carousel-{cid}").glob("*.png"))
    else:
        raise SystemExit(f"Unknown kind {kind}")
    subprocess.run(["node", "reels/generate.js", *args], cwd=ROOT, check=True, env=music_env(item))
    return [OUTPUT / f"{name}.mp4"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--media-repo", required=True)
    ap.add_argument("--ids", nargs="*")
    a = ap.parse_args()
    repo = Path(a.media_repo).resolve()
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    staged = 0
    for item in queue["items"]:
        if item.get("review_status") != "approved" or item.get("published_at"):
            continue
        if a.ids and item["id"] not in a.ids:
            continue
        files = render(item)
        if not files or not all(f.exists() for f in files):
            raise SystemExit(f"Render failed for {item['id']}")
        target = repo / item["id"]
        target.mkdir(parents=True, exist_ok=True)
        urls = []
        for f in files:
            if f.suffix == ".png":  # Instagram accepts JPEG images only
                from PIL import Image
                name = f.stem + ".jpg"
                Image.open(f).convert("RGB").save(target / name, "JPEG", quality=93, optimize=True)
            else:
                name = f.name
                shutil.copy2(f, target / name)
            urls.append(f"{BASE_URL}/{item['id']}/{name}")
        item["media"] = {"video_url": urls[0]} if item["format"] == "REELS" else {"slides": urls}
        item["review_status"] = "staged"
        staged += 1
        print(f"staged {item['id']}: {len(urls)} file(s)")
        QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")  # save as we go
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{staged} item(s) staged. Commit and push both repositories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
