"""Watchdog: list every staged item that should already be on Instagram but is not.
Exit code 1 (and a short Armenian report in watchdog.md) when something is more than 40 minutes late,
so the workflow can open an issue — GitHub then e-mails the owner."""
import datetime as dt, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
GRACE = dt.timedelta(minutes=40)


def late(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for i in json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]:
        if i.get("review_status") != "staged" or i.get("published_at") or not i.get("media"):
            continue
        due = dt.datetime.fromisoformat(f"{i['date']}T{i['time']}").replace(tzinfo=ZoneInfo(i.get("timezone", "Asia/Yerevan")))
        if now - due > GRACE and now - due < dt.timedelta(days=2):
            out.append((due, i))
    return out


def main():
    items = late()
    if not items:
        print("All due posts are published."); return 0
    rows = "\n".join(f"- {d.astimezone(ZoneInfo('Asia/Yerevan')):%Y-%m-%d %H:%M} · {i['title']} (`{i['id']}`)" for d, i in items)
    (ROOT / "watchdog.md").write_text(
        "Այս գրառումները ժամանակին չեն հրապարակվել.\n\n" + rows +
        "\n\nՍտուգե՛ք **Actions → Publish due posts** վերջին գործարկումը (հաճախ պատճառը ժամկետանց token-ն է)։\n", encoding="utf-8")
    print(rows); return 1


if __name__ == "__main__":
    sys.exit(main())
