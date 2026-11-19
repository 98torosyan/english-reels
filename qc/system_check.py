"""Whole-system check before publishing. Usage: python qc/system_check.py --media-repo ../english-reels-media
Prints FAIL / WARN lines and a summary; exit code 1 if anything FAILs."""
import argparse, json, re, subprocess, sys, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://98torosyan.github.io/english-reels-media/"
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️✅❌✔✖✨]")
FORBIDDEN = re.compile(r"\b(AI|ChatGPT|Claude|Codex|generated)\b")
fails, warns = [], []
def fail(m): fails.append(m)
def warn(m): warns.append(m)

def ffprobe(path):
    ff = ROOT / "node_modules/ffmpeg-static/ffmpeg"
    r = subprocess.run([str(ff), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    info = r.stderr
    dim = re.search(r"Video: .*?(\d{3,4})x(\d{3,4})", info)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    secs = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else 0
    return (int(dim[1]), int(dim[2])) if dim else None, secs, "Audio:" in info

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--media-repo", required=True); a = ap.parse_args()
    media = Path(a.media_repo).resolve()
    q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=4)))
    ids = Counter(i["id"] for i in q)
    for k, n in ids.items():
        if n > 1: fail(f"duplicate id {k}")
    slots = defaultdict(list)
    for i in q:
        iid, st = i["id"], i.get("review_status")
        when = dt.datetime.fromisoformat(f"{i['date']}T{i['time']}:00+04:00")
        if st == "published":
            if not i.get("published_at"): fail(f"{iid}: published without published_at")
            continue
        if st == "staged" and when < now - dt.timedelta(hours=6): fail(f"{iid}: staged but its time passed more than 6 h ago (will never publish)")
        if st in {"draft", "approved"} and when < now + dt.timedelta(days=2) and when > now: warn(f"{iid}: still {st}, due {i['date']} {i['time']}")
        if i["format"] != "STORIES": slots[(i["date"], i["time"], i["format"])].append(iid)
        cap = i.get("caption", "")
        if EMOJI.search(cap): fail(f"{iid}: emoji in caption: {EMOJI.findall(cap)}")
        if FORBIDDEN.search(cap): fail(f"{iid}: forbidden word in caption")
        if len(cap) > 2200: fail(f"{iid}: caption too long ({len(cap)})")
        if cap.count("#") > 30: fail(f"{iid}: too many hashtags")
        if i["format"] != "STORIES" and st in {"staged", "approved"}:
            if "bio" not in cap: warn(f"{iid}: caption has no link line")
            if not cap.strip(): fail(f"{iid}: empty caption")
        if st != "staged": continue
        m = i.get("media") or {}
        urls = [m.get("video_url"), m.get("image_url"), *(m.get("slides") or m.get("children") or [])]
        urls = [u for u in urls if u]
        if not urls: fail(f"{iid}: staged without media"); continue
        for u in urls:
            if isinstance(u, dict): u = u.get("image_url") or u.get("video_url")
            if not u.startswith(BASE): fail(f"{iid}: media outside the media site: {u}"); continue
            f = media / u[len(BASE):]
            if not f.exists():
                # rendered just in time by "Render ahead" (tools/render_ahead.py): fine until 2 days before it is due
                if i.get("render") and when > now + dt.timedelta(days=2): continue
                fail(f"{iid}: media file missing in media repo: {u[len(BASE):]}"); continue
            if f.suffix == ".mp4":
                dim, secs, audio = ffprobe(f)
                if dim not in ((1080, 1920), (1872, 3328), (1080, 1350), (1872, 2340)): fail(f"{iid}: video size {dim}")
                if not audio: fail(f"{iid}: video has no audio")
                if not 3 <= secs <= 90: fail(f"{iid}: video length {secs:.1f}s outside 3–90 s")
                off = i.get("thumb_offset")
                if off and off / 1000 > secs: fail(f"{iid}: cover time beyond video end")
            elif f.suffix.lower() in {".jpg", ".jpeg"}:
                from PIL import Image
                w, h = Image.open(f).size
                want = (1080, 1920) if i["format"] == "STORIES" else (1080, 1350)
                if (w, h) != want: fail(f"{iid}: image {w}x{h}, expected {want}")
            else:
                fail(f"{iid}: unsupported media type {f.suffix}")
        if i["format"] == "CAROUSEL" and not 2 <= len(urls) <= 10: fail(f"{iid}: carousel has {len(urls)} slides")
    for (d, t, fmt), lst in slots.items():
        if len(lst) > 1 and fmt == "REELS": warn(f"{d} {t}: {len(lst)} reels at the same time: {lst}")
    # media repo pushed?
    r = subprocess.run(["git", "status", "--porcelain"], cwd=media, capture_output=True, text=True)
    if r.stdout.strip(): fail(f"media repo has uncommitted files ({len(r.stdout.splitlines())})")
    r = subprocess.run(["git", "log", "--oneline", "@{u}..HEAD"], cwd=media, capture_output=True, text=True)
    if r.stdout.strip(): fail("media repo has unpushed commits")
    # content data
    for d in json.loads((ROOT / "reels/data/dialogues.json").read_text(encoding="utf-8"))["dialogues"]:
        for n, l in enumerate(d["lines"]):
            tj = ROOT / "assets/dialogues" / d["id"] / f"{n}.json"
            if not tj.exists(): warn(f"dialogue {d['id']}/{n}: no voice yet"); continue
            j = json.loads(tj.read_text())
            if j.get("text") != l["en"] or j.get("tag") != d["speakers"][l["s"]]["voice"]: fail(f"dialogue {d['id']}/{n}: voice does not match text/speaker")
            if not l["hy"].rstrip().endswith(("։", "՞", "՜", "»։", "՛")) and not l["hy"].endswith("։"): warn(f"dialogue {d['id']}/{n}: Armenian line has no final punctuation")
    for s in json.loads((ROOT / "reels/data/sounds.json").read_text(encoding="utf-8"))["sounds"]:
        for k, text in (("a", s["a"]["word"] + "."), ("b", s["b"]["word"] + "."), ("s", s["sentence"])):
            tj = ROOT / "assets/sounds" / s["id"] / f"{k}.json"
            if not tj.exists() or json.loads(tj.read_text()).get("text") != text: fail(f"sound {s['id']}/{k}: voice missing or stale")
    for l in json.loads((ROOT / "reels/data/words10.json").read_text(encoding="utf-8"))["lists"]:
        for n, w in enumerate(l["words"]):
            tj = ROOT / "assets/words10" / l["id"] / f"{n}.json"
            if not tj.exists() or json.loads(tj.read_text()).get("text") != w["en"] + ".": fail(f"words10 {l['id']}/{n}: voice missing or stale")
    for st in json.loads((ROOT / "reels/data/phrasal.json").read_text(encoding="utf-8"))["sets"]:
        for n, it in enumerate(st["items"]):
            for k, text in ((f"{n}p", it["en"] + "."), (f"{n}e", it["example"])):
                tj = ROOT / "assets/phrasal" / st["id"] / f"{k}.json"
                if not tj.exists() or json.loads(tj.read_text()).get("text") != text: fail(f"phrasal {st['id']}/{k}: voice missing or stale")
    for st in json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"]:
        tj = ROOT / "assets/reading" / st["id"] / "p.json"
        if not ((ROOT / "assets/reading" / f"{st['id']}.jpg").exists() or (ROOT / "assets/reading" / st["id"] / "1.jpg").exists()):
            fail(f"reading {st['id']}: picture missing")
        if not tj.exists(): fail(f"reading {st['id']}: voice missing"); continue
        j = json.loads(tj.read_text())
        if j.get("text") != st["en"] or j.get("tag") != st["voice"] or len(j.get("words", [])) != len(st["en"].split()): fail(f"reading {st['id']}: voice stale")
    for f in [ROOT / "reels/data/reading.json", ROOT / "reels/data/dialogues.json", ROOT / "reels/data/sounds.json", ROOT / "carousels/data/lists.json", ROOT / "stories/stories.json",
              ROOT / "reels/data/words10.json", ROOT / "reels/data/phrasal.json"]:
        txt = f.read_text(encoding="utf-8")
        if EMOJI.search(txt): fail(f"{f.name}: emoji in content")
    for p in ["publish/ENABLED"]:
        if not (ROOT / p).exists(): warn(f"{p} missing: publishing is paused")
    print("\n".join(["FAIL  " + m for m in fails] + ["WARN  " + m for m in warns]))
    print(f"\n{len(fails)} fail, {len(warns)} warn, {len(q)} queue items checked")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
