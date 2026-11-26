"""YouTube listening lessons (long 16:9 videos made by reels/render_lesson.js).

    python publish/youtube_lesson.py meta <lesson-id>                 # print title, description, tags (no upload)
    python publish/youtube_lesson.py upload <lesson-id> <video.mp4>   # resumable upload, prints the video id
    python publish/youtube_lesson.py next                             # the next lesson that is ready (scheduled runs)

Upload needs YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN. Chapters come from <video>.json next to the video
(written by the renderer), so the times always match the video."""
import json, os, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from crosspost import CHANNEL, LESSONS as LESSON_SITE, INSTAGRAM, _post  # noqa: E402

NUM = {2: "two", 3: "three", 4: "four", 5: "five"}


def _data():
    reading = {s["id"]: s for s in json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"]}
    lessons = json.loads((ROOT / "reels/data/lessons.json").read_text(encoding="utf-8"))
    return reading, lessons


def lesson_meta(lesson_id: str, chapters: list | None = None) -> dict:
    reading, data = _data()
    lesson = next(l for l in data["lessons"] if l["id"] == lesson_id)
    stories = [reading[i] for i in lesson["stories"]]
    level, n = lesson["level"], len(stories)
    who = "Mila and Leo" if all(i.startswith("mila-") for i in lesson["stories"]) else "Ani"
    title = f"{lesson['title']} 🎧 English Listening Practice ({level}) | {NUM.get(n, n)} easy stories with text"
    if len(title) > 100: title = f"{lesson['title']} 🎧 English Listening Practice ({level})"
    parts = [f"Improve your English listening with {NUM.get(n, n)} short {level} stories about {who}. "
             "Each story has the words to know with the Armenian translation, then a clear British voice reads it while every word lights up.",
             "", "How to use this lesson:", "1. Learn the new words.", "2. Listen and follow the highlighted text.",
             "3. Play it again and read aloud with the voice.", ""]
    if chapters:
        parts += ["⏱ Chapters"] + [f"{t} {name}" for t, name in chapters] + [""]
    for s in stories:
        words = data.get("words", {}).get(s["id"], [])
        parts += [f"📖 {s['title']} · {s['title_hy']}"]
        if words: parts += ["Words: " + ", ".join(f"{en} — {hy}" for en, hy in words)]
        parts += [""]
    parts += [f"🔔 Subscribe for a new story every day: {CHANNEL}?sub_confirmation=1",
              f"📚 All lessons with audio: {LESSON_SITE}", f"📷 Instagram: {INSTAGRAM}",
              "✉️ Private and group English lessons in Yerevan: englishreadingroom.am@gmail.com", "",
              "Լսի՛ր, հետևի՛ր ընդգծված բառերին, ապա կարդա՛ բարձրաձայն։ Ամեն շաբաթ՝ նոր դաս։", "",
              f"#EnglishListening #LearnEnglish #{level}English #EnglishStories #Անգլերեն"]
    desc = "\n".join(parts).replace("<", "‹").replace(">", "›")[:4900]
    tags, total = [], 0
    for t in [f"English listening practice {level}", "English listening", "listening practice", "easy English stories", f"{level} English",
              "learn English", "English stories with text", "British English", "English reading practice", "English for beginners",
              "graded reader", f"{who} stories", lesson["title"], "Անգլերեն", "անգլերեն սովորել", "անգլերենի դասեր", "English Reading Room"] + [s["title"] for s in stories]:
        if t not in tags and total + len(t) + 3 < 480: tags.append(t); total += len(t) + 3
    meta = {"snippet": {"title": title, "description": desc, "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en-GB", "tags": tags},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True, "embeddable": True,
                       "license": "youtube", "publicStatsViewable": True}}
    if lesson.get("title_hy"):
        meta["localizations"] = {"hy": {"title": f"{lesson['title_hy']} 🎧 Անգլերենի ունկնդրում ({level})", "description": desc}}
    return meta


def _token() -> str:
    cid, secret, refresh = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and secret and refresh): raise SystemExit("YouTube secrets are not set.")
    return _post("https://oauth2.googleapis.com/token", {"client_id": cid, "client_secret": secret, "refresh_token": refresh,
                                                          "grant_type": "refresh_token"})["access_token"]


def upload(lesson_id: str, video: Path) -> str:
    """Resumable upload in 16 MB pieces (a 4K lesson is a few hundred MB)."""
    side = video.with_suffix(".json")
    chapters = json.loads(side.read_text())["chapters"] if side.exists() else None
    meta = lesson_meta(lesson_id, chapters)
    parts = "snippet,status" + (",localizations" if "localizations" in meta else "")
    token, size = _token(), video.stat().st_size
    req = urllib.request.Request(f"https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part={parts}",
                                 data=json.dumps(meta).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    with urllib.request.urlopen(req, timeout=120) as r:
        session = r.headers["Location"]
    chunk, sent = 16 * 1024 * 1024, 0
    with open(video, "rb") as f:
        while sent < size:
            f.seek(sent); piece = f.read(chunk)
            put = urllib.request.Request(session, data=piece, method="PUT", headers={
                "Content-Length": str(len(piece)), "Content-Range": f"bytes {sent}-{sent + len(piece) - 1}/{size}"})
            try:
                with urllib.request.urlopen(put, timeout=600) as r:
                    return json.load(r)["id"]          # the last piece answers 200/201 with the video
            except urllib.error.HTTPError as e:
                if e.code != 308: raise
                got = e.headers.get("Range")             # bytes=0-N received so far
                sent = int(got.split("-")[1]) + 1 if got else sent
                print(f"  uploaded {sent * 100 // size}%")
    raise RuntimeError("Upload ended without a video id.")


def next_lesson() -> str:
    """The first lesson not yet on YouTube whose stories have all been published on Instagram (empty if none)."""
    _, data = _data()
    queue = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    out = {i.get("content_id") for i in queue if i.get("kind") == "reading" and i.get("published_at")}
    for lesson in data["lessons"]:
        if not lesson.get("youtube_id") and all(s in out for s in lesson["stories"]): return lesson["id"]
    return ""


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "meta":
        print(json.dumps(lesson_meta(sys.argv[2]), ensure_ascii=False, indent=2))
    elif len(sys.argv) >= 2 and sys.argv[1] == "next":
        print(next_lesson())
    elif len(sys.argv) >= 4 and sys.argv[1] == "upload":
        print(upload(sys.argv[2], Path(sys.argv[3])))
    else:
        print(__doc__)
