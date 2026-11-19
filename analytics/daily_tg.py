"""Morning note to the owner's Telegram: followers since yesterday, how yesterday's posts are doing, and which kind of
post earns the most this week (likes and comments, plus views/saves/shares once the token can read insights).
Usage: python analytics/daily_tg.py   (after analytics/insights.py has written today's snapshot)"""
import json, os, sys, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from insights import SNAP, TZ, ROOT, series_of   # noqa: E402

TOKEN, CHAT = os.environ.get("TG_BOT_TOKEN", ""), os.environ.get("TG_CHAT_ID", "")


def when(p): return datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(TZ)


def note():
    snaps = sorted(SNAP.glob("*.json"))
    if not snaps: return None
    now = json.loads(snaps[-1].read_text()); prev = json.loads(snaps[-2].read_text()) if len(snaps) > 1 else None
    queue = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    posts = [p for p in now["posts"] if "error" not in p]
    before = {p["id"]: p for p in (prev or {}).get("posts", [])}
    score = lambda p: (p.get("views") or 0) / 50 + (p.get("shares") or 0) * 3 + (p.get("saved") or 0) * 2 + (p.get("comments_count") or 0) * 2 + (p.get("like_count") or 0)
    out = ["Բարի լույս 🌿 English Reading Room", ""]
    if now.get("followers") is not None:
        d = now["followers"] - prev["followers"] if prev and prev.get("followers") is not None else None
        out.append(f"Հետևորդներ՝ {now['followers']}" + (f" ({'+' if d >= 0 else ''}{d} երեկվանից)" if d is not None else ""))
    day = datetime.now(TZ).date() - timedelta(days=1)
    yday = sorted([p for p in posts if when(p).date() == day], key=when)
    if yday:
        out += ["", "Երեկվա գրառումները"]
        for p in yday:
            gain = p.get("like_count", 0) - before.get(p["id"], {}).get("like_count", 0) if p["id"] in before else None
            views = f", դիտում {p['views']}" if p.get("views") else ""
            out.append(f"• {when(p):%H:%M} {(p.get('title') or '')[:38]} — ❤️ {p.get('like_count', 0)}, 💬 {p.get('comments_count', 0)}{views}")
    week = [p for p in posts if when(p).date() > day - timedelta(days=7)]
    by = defaultdict(list)
    for p in week: by[series_of(p, queue)].append(p)
    if by:
        out += ["", "Այս շաբաթ ամենալավը (միջինը մեկ գրառման)"]
        for name, ps in sorted(by.items(), key=lambda kv: -sum(score(p) for p in kv[1]) / len(kv[1]))[:4]:
            out.append(f"• {name}: ❤️ {round(sum(p.get('like_count', 0) for p in ps) / len(ps))} ({len(ps)} գրառում)")
    if week:
        best = max(week, key=score)
        out += ["", f"Շաբաթվա լավագույնը՝ {(best.get('title') or '')[:40]}", best.get("permalink", "")]
    return "\n".join(out)


def main():
    text = note()
    if not text: return
    print(text)
    if TOKEN and CHAT:
        data = urllib.parse.urlencode({"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data, timeout=30)


if __name__ == "__main__":
    main()
