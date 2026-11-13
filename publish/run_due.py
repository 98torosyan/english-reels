"""Publish the queue items that are due now (used by the scheduled workflow).

An item is due when review_status == "staged", it has media URLs, it is not yet
published, and its date/time (Asia/Yerevan) is in the past but less than
MAX_LATE_HOURS ago. Publishes up to eight due items per run, oldest first. DRY_RUN=1 sends nothing.
"""
import json, os, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish  # noqa: E402
import crosspost  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
TZ = ZoneInfo("Asia/Yerevan")
MAX_LATE = timedelta(hours=float(os.environ.get("MAX_LATE_HOURS", "6")))


def due_items(queue: dict, now: datetime) -> list[dict]:
    out = []
    for item in queue["items"]:
        if item.get("review_status") != "staged" or item.get("published_at") or not item.get("media"):
            continue
        when = datetime.fromisoformat(f"{item['date']}T{item['time']}").replace(tzinfo=TZ)
        if when <= now < when + MAX_LATE:
            out.append(item)
    return sorted(out, key=lambda i: (i["date"], i["time"]))


def main() -> int:
    dry = os.environ.get("DRY_RUN", "1").strip().lower() not in {"0", "false", "no"}
    now = datetime.now(TZ)
    if os.environ.get("FORCE_NOW"):
        now = datetime.fromisoformat(os.environ["FORCE_NOW"]).replace(tzinfo=TZ)
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = due_items(queue, now)
    if not items:
        print(f"{now:%Y-%m-%d %H:%M} Yerevan: nothing due.")
        return 0
    code = 0
    for item in items[:8]:
        content = {"kind": item["format"], "caption": item.get("caption", ""), **item["media"], **({"thumb_offset": item["thumb_offset"]} if item.get("thumb_offset") else {}),
                   **({"_container": item["container_id"]} if item.get("container_id") else {})}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False)
        print(f"Due: {item['id']} ({item['format']}).")
        publish.LAST_MEDIA_ID = None; publish.LAST_CONTAINER_ID = None
        try:
            rc = publish.run(Path(f.name), dry)
        except publish.PublishError as error:
            print(f"Publishing failed for {item['id']}: {error}"); code = 1
            # Safety 3: at most 3 attempts per post, then it waits for a person (the watchdog e-mails the owner).
            item["attempts"] = item.get("attempts", 0) + 1; item["last_error"] = str(error)[:300]
            if publish.LAST_CONTAINER_ID: item["container_id"] = publish.LAST_CONTAINER_ID
            if item["attempts"] >= 3: item["review_status"] = "failed"
            if not dry: QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            continue
        if rc == 0 and not dry:
            item["published_at"] = now.isoformat(timespec="minutes")
            item["review_status"] = "published"
            if publish.LAST_MEDIA_ID: item["ig_media_id"] = publish.LAST_MEDIA_ID
            item.update(crosspost.run(item))
            QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        code = code or rc
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except publish.PublishError as error:
        print(f"Publishing failed: {error}")
        sys.exit(1)
