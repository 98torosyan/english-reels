"""Re-render the reels that are already scheduled but not yet published (after a design/motion upgrade),
replacing their files in the media repo in place: same dates, same URLs, same music, queue untouched.
Usage: python publish/rerender.py --media-repo ../english-reels-media [--kinds words10 reading ...]"""
import argparse, datetime as dt, importlib, json, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publish"))
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
# kind -> (data file, list key, plan module, music offset)
KINDS = {"words10": ("words10.json", "lists", "plan_words10", 0), "phrasal": ("phrasal.json", "sets", "plan_phrasal", 5),
         "review": ("reviews.json", "reviews", "plan_review", 11), "reading": ("reading.json", "stories", "plan_reading", 2)}


def push(media, msg):
    subprocess.run(["git", "add", "-A"], cwd=media, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=media).returncode:
        subprocess.run(["git", "-c", "user.name=98torosyan", "-c", "user.email=98torosyan@gmail.com", "commit", "-qm", msg], cwd=media, check=True)
        for _ in range(4):
            if subprocess.run(["git", "pull", "-q", "--rebase"], cwd=media).returncode == 0 and subprocess.run(["git", "push", "-q"], cwd=media).returncode == 0:
                break


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); ap.add_argument("--kinds", nargs="*", default=list(KINDS)); a = ap.parse_args()
    media = Path(a.media_repo).resolve(); today = dt.date.today().isoformat()
    q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))
    todo = [i for i in q["items"] if i.get("kind") in a.kinds and not i.get("published_at") and i["date"] >= today and i.get("media", {}).get("video_url")]
    for n, i in enumerate(todo, 1):
        data, key, mod, off = KINDS[i["kind"]]
        ids = [x["id"] for x in json.loads((ROOT / "reels/data" / data).read_text(encoding="utf-8"))[key]]
        k = ids.index(i["content_id"])
        env = {**os.environ, "MUSIC_TRACK": importlib.import_module(mod).music(k + off)}
        subprocess.run(["node", f"reels/render_{i['kind']}.js", i["content_id"]], cwd=ROOT, check=True, env=env, stdout=subprocess.DEVNULL)
        name = f"{i['kind']}-{i['content_id']}"; folder = media / i["id"]
        shutil.copy2(OUT / f"{name}.mp4", folder / f"{name}.mp4")
        Image.open(OUT / f"{name}.png").convert("RGB").save(folder / "cover.jpg", "JPEG", quality=92)
        print(f"{n}/{len(todo)} re-rendered {i['id']}", flush=True)
        if n % 4 == 0 or n == len(todo):
            push(media, f"Reels՝ նոր անիմացիաներով ({n}/{len(todo)})")


if __name__ == "__main__":
    main()
