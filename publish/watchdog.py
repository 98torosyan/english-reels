"""Watchdog: list every staged item that should already be on Instagram but is not, and the other things that
quietly stop the page: a reading missing on YouTube, media missing for a post due soon, a failed workflow run.
Exit code 1 (and a short Armenian report in watchdog.md) when something needs attention, so the workflow can open
an issue (GitHub then e-mails the owner) and send the same text to Telegram."""
import datetime as dt, json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
GRACE = dt.timedelta(minutes=40)
YT_SINCE = dt.datetime(2026, 11, 26, 11, 0, tzinfo=ZoneInfo("Asia/Yerevan"))   # YouTube cross-posting started here
YT_GRACE = dt.timedelta(hours=2)
REPO, MEDIA_REPO, MEDIA_BRANCH = "98torosyan/english-reels", "98torosyan/english-reels-media", "media"
WATCHED = ("Render ahead", "Publish due post", "YouTube backfill")


def queue_items():
    return json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]


def _gh(path):
    """GET from the GitHub API (public repos; the workflow token raises the rate limit)."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "err-watchdog"}
    tok = os.environ.get("GH_TOKEN", "").strip()
    if tok: headers["Authorization"] = f"Bearer {tok}"
    with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/{path}", headers=headers), timeout=60) as r:
        return json.loads(r.read().decode())


def youtube_missing(now=None, items=None):
    """Readings that went out on Instagram more than two hours ago but are not on YouTube."""
    if not os.environ.get("YT_REFRESH_TOKEN", "").strip(): return []   # YouTube not connected: nothing to report
    now = now or dt.datetime.now(dt.timezone.utc); out = []
    for i in items if items is not None else queue_items():
        if i.get("kind") != "reading" or i.get("format") != "REELS" or not i.get("published_at") or i.get("youtube_id"): continue
        try: at = dt.datetime.fromisoformat(i["published_at"])
        except ValueError: continue
        if at.tzinfo is None: at = at.replace(tzinfo=ZoneInfo("Asia/Yerevan"))
        if at >= YT_SINCE and now - at > YT_GRACE: out.append(i)
    return out


def media_files():
    """Every file path on the media site, read from the media repo's tree (not from a local checkout)."""
    tree = _gh(f"repos/{MEDIA_REPO}/git/trees/{MEDIA_BRANCH}?recursive=1")
    return {t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"}, bool(tree.get("truncated"))


def media_missing(now=None, items=None, files=None, hours=48):
    """Staged posts due within `hours` whose media files are not on the media site yet."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if files is None:
        try: files, truncated = media_files()
        except Exception as e:
            print("media check skipped:", type(e).__name__); return []
        if truncated: print("media tree truncated: check skipped"); return []
    out = []
    for i in items if items is not None else queue_items():
        if i.get("review_status") != "staged" or i.get("published_at") or not i.get("media"): continue
        due = dt.datetime.fromisoformat(f"{i['date']}T{i['time']}").replace(tzinfo=ZoneInfo(i.get("timezone", "Asia/Yerevan")))
        if not dt.timedelta(0) <= due - now <= dt.timedelta(hours=hours): continue
        urls = [u for k, u in i["media"].items() if isinstance(u, str)] + list(i["media"].get("slides") or [])
        gone = [u.split("english-reels-media/", 1)[1] for u in urls if "english-reels-media/" in u and u.split("english-reels-media/", 1)[1] not in files]
        if gone: out.append((due, i, gone))
    return out


def failed_runs(now=None, hours=24):
    """Watched workflows whose latest run in the last day failed (a later success clears it)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    try: runs = _gh(f"repos/{REPO}/actions/runs?per_page=60").get("workflow_runs", [])
    except Exception as e:
        print("run check skipped:", type(e).__name__); return []
    latest = {}
    for r in runs:   # newest first
        if r.get("name") in WATCHED and r.get("status") == "completed" and r["name"] not in latest: latest[r["name"]] = r
    out = []
    for name, r in latest.items():
        at = dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if r.get("conclusion") == "failure" and now - at < dt.timedelta(hours=hours): out.append((name, r.get("html_url", "")))
    return out


def telegram(text):
    tok, chat = os.environ.get("TG_BOT_TOKEN", "").strip(), os.environ.get("TG_CHAT_ID", "").strip()
    if not (tok and chat and text.strip()): return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=30)
    except Exception as e:
        print("telegram failed:", type(e).__name__)


def late(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for i in queue_items():
        if i.get("review_status") not in ("staged", "failed") or i.get("published_at") or not i.get("media"):
            continue
        due = dt.datetime.fromisoformat(f"{i['date']}T{i['time']}").replace(tzinfo=ZoneInfo(i.get("timezone", "Asia/Yerevan")))
        if now - due > GRACE and now - due < dt.timedelta(days=2):
            out.append((due, i))
    return out


def token_warning(days=10):
    """Warn well before the Instagram token (or its data access) expires, so posting never stops by surprise."""
    tok = os.environ.get("IG_TOKEN", "").strip()
    if not tok:
        return ""
    ver = os.environ.get("META_GRAPH_API_VERSION", "v27.0")
    url = f"https://graph.facebook.com/{ver}/debug_token?" + urllib.parse.urlencode({"input_token": tok})
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode()).get("data", {})
    except Exception as e:   # some token types cannot call debug_token: fall back to a plain validity check
        print("debug_token unavailable:", type(e).__name__, getattr(e, "code", ""))
        try:
            req = urllib.request.Request(f"https://graph.facebook.com/{ver}/me?fields=id", headers={"Authorization": f"Bearer {tok}"})
            with urllib.request.urlopen(req, timeout=30):
                print("token ok (valid)"); return ""
        except urllib.error.HTTPError as h:
            if h.code in (400, 401, 403):
                return "Instagram token-ը **այլևս չի աշխատում**։ Հրապարակումները կանգնած են, պետք է նոր token։"
            return ""
        except Exception:
            return ""
    if not d.get("is_valid", True):
        return "Instagram token-ը **անվավեր է**։ Հրապարակումները կանգնած են, պետք է նոր token։"
    now = dt.datetime.now(dt.timezone.utc).timestamp(); out = []
    for key, what in (("expires_at", "token-ի ժամկետը"), ("data_access_expires_at", "տվյալների հասանելիության ժամկետը")):
        ts = d.get(key) or 0
        if ts and ts - now < days * 86400:
            out.append(f"Instagram {what} լրանում է {dt.datetime.fromtimestamp(ts, dt.timezone.utc):%Y-%m-%d}-ին։ Թարմացրե՛ք IG_TOKEN-ը մինչ այդ։")
    print("token ok" if not out else "\n".join(out))
    return "\n".join(out)


def runway(min_days=4):
    """Warn early when the plan is about to run dry, so the page never goes quiet."""
    today = dt.datetime.now(ZoneInfo("Asia/Yerevan")).date()
    ready = sorted({i["date"] for i in json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
                    if i.get("review_status") == "staged" and not i.get("published_at") and i.get("format") != "STORIES" and i["date"] >= today.isoformat()})
    left = (dt.date.fromisoformat(ready[-1]) - today).days if ready else -1
    if left < min_days:
        return f"Պատրաստ գրառումները բավական են միայն **{max(left, 0)} օր**ի համար (մինչև {ready[-1] if ready else '—'})։ Ժամանակն է նոր նյութ պատրաստելու։"
    return ""


def main():
    items = late(); warn = token_warning(); dry = runway()
    if dry and dt.datetime.now(ZoneInfo("Asia/Yerevan")).hour < 13: warn = (warn + "\n" + dry).strip()   # once a day is enough
    yt, media, runs = youtube_missing(), media_missing(), failed_runs()
    if not (items or warn or yt or media or runs):
        print("All due posts are published, YouTube is up to date, media and workflows are fine."); return 0
    body = ""
    if items:
        rows = "\n".join(f"- {d.astimezone(ZoneInfo('Asia/Yerevan')):%Y-%m-%d %H:%M} · {i['title']} (`{i['id']}`)" for d, i in items)
        body += ("Այս գրառումները ժամանակին չեն հրապարակվել.\n\n" + rows +
                 "\n\nՍտուգե՛ք **Actions → Publish due posts** վերջին գործարկումը (հաճախ պատճառը ժամկետանց token-ն է)։\n")
        print(rows)
    if yt:
        rows = "\n".join(f"- `{i['id']}` (Instagram՝ {i['published_at']})" for i in yt)
        body += "\nԱյս ընթերցանությունները Instagram-ում կան, բայց YouTube-ում՝ ոչ.\n\n" + rows + "\n\nՍտուգե՛ք **Publish due post** գործարկման log-ը (YouTube token)։\n"
        print(rows)
    if media:
        rows = "\n".join(f"- {d.astimezone(ZoneInfo('Asia/Yerevan')):%Y-%m-%d %H:%M} · `{i['id']}` — {', '.join(g)}" for d, i, g in media)
        body += "\nՄոտակա 48 ժամում հրապարակվող գրառումների ֆայլերը պատրաստ չեն.\n\n" + rows + "\n\nԳործարկե՛ք **Actions → Render ahead**։\n"
        print(rows)
    if runs:
        rows = "\n".join(f"- {n}: {u}" for n, u in runs)
        body += "\nՎերջին 24 ժամում ձախողված գործարկումներ.\n\n" + rows + "\n"
        print(rows)
    if warn:
        body += "\n" + warn + "\n"
    (ROOT / "watchdog.md").write_text(body, encoding="utf-8")
    telegram("English Reading Room · պահակ\n\n" + body.replace("**", "").replace("`", ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
