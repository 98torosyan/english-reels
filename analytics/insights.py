"""Instagram analytics: a daily snapshot of every recent post's numbers, and a weekly report.

Daily:   python analytics/insights.py            -> analytics/snapshots/<date>.json
Weekly:  python analytics/insights.py --report   -> also writes analytics/report.md (the workflow opens it as an issue)
Uses the official Graph API (IG_TOKEN needs the instagram_manage_insights permission)."""
import json, os, sys, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "analytics" / "snapshots"
TZ = ZoneInfo("Asia/Yerevan")
API = f"https://graph.facebook.com/{os.environ.get('META_GRAPH_API_VERSION', 'v27.0')}"
TOKEN, USER = os.environ.get("IG_TOKEN", ""), os.environ.get("IG_USER_ID", "")
METRICS = {"REELS": "views,reach,saved,shares,total_interactions", "FEED": "views,reach,saved,shares,total_interactions"}
SERIES = {"words10": "10 words", "phrasal": "Phrasal verbs", "review": "Weekly review", "dialogue": "Everyday English", "sound": "Sound it out",
          "story": "Story time", "rule": "Carousels", "mistake": "Common mistakes", "quiz": "Quiz", "word": "Word of the day"}


def get(path, **params):
    params["access_token"] = TOKEN
    with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(params)}", timeout=40) as r:
        return json.load(r)


def snapshot():
    acct = get(USER, fields="followers_count,media_count")
    media = get(f"{USER}/media", fields="id,caption,media_product_type,media_type,timestamp,permalink,like_count,comments_count", limit=60)["data"]
    posts, failed = [], 0
    for m in media:
        kind = m.get("media_product_type", "FEED")
        if kind not in METRICS: continue
        row = {k: m.get(k) for k in ("id", "media_product_type", "media_type", "timestamp", "permalink", "like_count", "comments_count")}
        row["title"] = (m.get("caption") or "").split("\n")[0][:80]
        try:
            for d in get(f"{m['id']}/insights", metric=METRICS[kind])["data"]:
                row[d["name"]] = d["values"][0]["value"] if d.get("values") else d.get("total_value", {}).get("value")
        except urllib.error.HTTPError as e:
            failed += 1; row["error"] = e.code
        posts.append(row)
    insights = not (failed == len(posts) and posts)
    if not insights:  # keep going with likes, comments and followers until the token gets instagram_manage_insights
        print("NOTE: post insights are not available yet (the token needs the instagram_manage_insights permission); saving likes, comments and followers only.")
        for p in posts: p.pop("error", None)
    snap = {"date": datetime.now(TZ).date().isoformat(), "followers": acct.get("followers_count"), "media_count": acct.get("media_count"), "insights": insights, "posts": posts}
    SNAP.mkdir(parents=True, exist_ok=True)
    (SNAP / f"{snap['date']}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return snap


def series_of(post, queue):
    for i in queue:
        if i.get("ig_media_id") == post["id"]: return SERIES.get(i.get("kind"), i.get("kind"))
    ts = datetime.fromisoformat(post["timestamp"].replace("+0000", "+00:00"))
    for i in queue:
        if i.get("published_at") and i.get("format") != "STORIES":
            if abs(datetime.fromisoformat(i["published_at"]).astimezone(timezone.utc) - ts) < timedelta(minutes=20):
                return SERIES.get(i.get("kind"), i.get("kind"))
    return "Other"


def report(snap):
    queue = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    week_ago = (datetime.now(TZ) - timedelta(days=7)).date()
    old = SNAP / f"{week_ago.isoformat()}.json"
    gained = snap["followers"] - json.loads(old.read_text())["followers"] if old.exists() and snap.get("followers") is not None else None
    recent = [p for p in snap["posts"] if datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(TZ).date() > week_ago and "error" not in p]
    score = lambda p: (p.get("shares") or 0) * 3 + (p.get("saved") or 0) * 2 + (p.get("comments_count") or 0) * 2 + (p.get("like_count") or 0) + (p.get("reach") or 0) / 100
    by = defaultdict(list); hours = defaultdict(list)
    for p in recent:
        by[series_of(p, queue)].append(p)
        hours[datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(TZ).hour].append(score(p))
    avg = lambda xs, k: round(sum((x.get(k) or 0) for x in xs) / len(xs)) if xs else 0
    lines = [f"# Շաբաթական հաշվետվություն · {snap['date']}", "",
             f"**Հետևորդներ՝** {snap['followers']}" + (f" ({'+' if gained >= 0 else ''}{gained} շաբաթում)" if gained is not None else ""),
             f"**Գրառումներ այս շաբաթ՝** {len(recent)}", "", "## Շարքերը (միջինը մեկ գրառման համար)", "",
             "| Շարք | Գրառում | Դիտում | Հասանելիություն | Պահել | Share | Լայք | Մեկնաբ. |", "|---|---|---|---|---|---|---|---|"]
    for name, ps in sorted(by.items(), key=lambda kv: -sum(score(p) for p in kv[1]) / len(kv[1])):
        lines.append(f"| {name} | {len(ps)} | {avg(ps, 'views')} | {avg(ps, 'reach')} | {avg(ps, 'saved')} | {avg(ps, 'shares')} | {avg(ps, 'like_count')} | {avg(ps, 'comments_count')} |")
    lines += ["", "## Լավագույն 5 գրառումը", ""]
    for p in sorted(recent, key=score, reverse=True)[:5]:
        lines.append(f"- [{p['title'] or p['id']}]({p['permalink']}) · դիտում {p.get('views') or 0}, պահել {p.get('saved') or 0}, share {p.get('shares') or 0}, լայք {p.get('like_count') or 0}")
    if hours:
        best = sorted(hours.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))[:3]
        lines += ["", "## Լավագույն ժամերը", "", ", ".join(f"{h:02d}:00" for h, _ in best)]
    if not snap.get("insights"):
        lines += ["", "_Դիտումները, պահումներն ու share-երը կերևան, երբ token-ը ստանա instagram_manage_insights թույլտվությունը։_"]
    (ROOT / "analytics" / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    if not TOKEN or not USER: raise SystemExit("IG_TOKEN / IG_USER_ID missing.")
    s = snapshot(); print(f"snapshot: {len(s['posts'])} posts, {s['followers']} followers")
    if "--report" in sys.argv: report(s)
