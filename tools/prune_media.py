"""Keep the public media site small (GitHub Pages serves at most ~1 GB): remove the media folders of posts that were
published more than --days days ago. Instagram keeps its own copy, and every file stays in the media repo's git history.
Usage: python tools/prune_media.py --media-repo ../english-reels-media [--days 3] [--dry-run]"""
import argparse, datetime as dt, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); today = dt.date.today()
    items = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    freed = 0
    for i in items:
        if i.get("review_status") != "published": continue
        if (today - dt.date.fromisoformat(i["date"])).days <= a.days: continue
        d = media / i["id"]
        if not d.is_dir(): continue
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()); freed += size
        print("remove", i["id"], f"{size / 1e6:.0f} MB")
        if not a.dry_run: shutil.rmtree(d)
    print(f"freed {freed / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
