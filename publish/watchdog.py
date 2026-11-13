"""Watchdog: list every staged item that should already be on Instagram but is not.
Exit code 1 (and a short Armenian report in watchdog.md) when something is more than 40 minutes late,
so the workflow can open an issue — GitHub then e-mails the owner."""
import datetime as dt, json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
GRACE = dt.timedelta(minutes=40)


def late(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for i in json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]:
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


def main():
    items = late(); warn = token_warning()
    if not items and not warn:
        print("All due posts are published."); return 0
    body = ""
    if items:
        rows = "\n".join(f"- {d.astimezone(ZoneInfo('Asia/Yerevan')):%Y-%m-%d %H:%M} · {i['title']} (`{i['id']}`)" for d, i in items)
        body += ("Այս գրառումները ժամանակին չեն հրապարակվել.\n\n" + rows +
                 "\n\nՍտուգե՛ք **Actions → Publish due posts** վերջին գործարկումը (հաճախ պատճառը ժամկետանց token-ն է)։\n")
        print(rows)
    if warn:
        body += "\n" + warn + "\n"
    (ROOT / "watchdog.md").write_text(body, encoding="utf-8")
    return 1


if __name__ == "__main__":
    sys.exit(main())
