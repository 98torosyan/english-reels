"""Cross-post a published reel to YouTube Shorts and the Facebook Page (official APIs only).

Each target is used only when its secrets are set, and a failure never blocks Instagram:
  YouTube:  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (YouTube Data API v3, OAuth)
  Facebook: FB_PAGE_ID, FB_PAGE_TOKEN                         (Graph API, page video by URL)"""
import json, os, urllib.parse, urllib.request
from pathlib import Path

GRAPH = f"https://graph.facebook.com/{os.environ.get('META_GRAPH_API_VERSION', 'v27.0')}"


def _post(url, data=None, headers=None, body=None):
    req = urllib.request.Request(url, data=body if body is not None else urllib.parse.urlencode(data or {}).encode(), headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


ROOT = Path(__file__).resolve().parents[1]
CHANNEL = "https://www.youtube.com/@english.readingroom"
LESSONS = "https://98torosyan.github.io/english-reading/"
INSTAGRAM = "https://www.instagram.com/english.readingroom/"
BASE_TAGS = ["learn English", "English story", "easy English story", "English reading", "English listening", "British English",
             "English for beginners", "short stories in English", "English with text", "graded reader",
             "Անգլերեն", "անգլերեն սովորել", "անգլերենի դասեր", "English Reading Room"]


def _story(item: dict) -> dict:
    """The reading's own data (title, level, English text, Armenian text) from reels/data/reading.json."""
    rid = (item.get("render") or {}).get("reading") or item.get("content_id")
    try:
        data = json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"]
        return next((s for s in data if s.get("id") == rid), {})
    except Exception:
        return {}


def _question(caption: str) -> str:
    return next((l.strip() for l in caption.split("\n") if l.startswith("Question:")), "")


def youtube_meta(item: dict) -> dict:
    """Title, description, tags and status for one reading Short, written for YouTube search."""
    s, caption = _story(item), item.get("caption", "")
    if not s.get("en"):   # a reel made outside the reading data: take the texts from its caption
        paras = [p.strip() for p in caption.split("\n\n")]
        for k, para in enumerate(paras):
            if para.startswith("Թարգմանություն"):
                s = {**s, "hy": para.split("\n", 1)[-1], "en": paras[k - 1] if k else ""}
                break
    name, level = s.get("title", ""), s.get("level", "A1")
    if not name:
        for line in caption.split("\n")[:5]:
            if "·" in line and not any(w in line for w in ("Daily reading", "Կարդանք", "Story time", "Did you know")):
                name = line.split("·")[0].strip()
                if "(" in line: level = line.rsplit("(", 1)[1].split(")")[0].strip() or level
                break
    name = name or "Daily reading"
    rid = str(item.get("id"))
    who = "Mila and Leo" if "mila-" in rid else "" if "-st-" in rid else "Ani"
    title = f"{name} 📖 Easy English Story ({level}) | Անգլերեն ընթերցանություն"
    if len(title) > 100: title = f"{name} 📖 Easy English Story ({level})"[:100]
    parts = [f"{name} — a short {level} story in easy English with a clear British voice and the Armenian translation.",
             "🎧 Listen, follow the highlighted words, then read it aloud."]
    if s.get("en"): parts += ["", "📖 Story", s["en"].strip()]
    if s.get("hy"): parts += ["", f"🇦🇲 Թարգմանություն — {s.get('title_hy', '')}".rstrip(" —"), s["hy"].strip()]
    q = _question(caption)
    if q: parts += ["", "💬 " + q]
    parts += ["", f"New stories every day{' with ' + who if who else ''}. Subscribe 🔔 {CHANNEL}?sub_confirmation=1",
              f"📚 All lessons with audio: {LESSONS}",
              f"📷 Instagram: {INSTAGRAM}",
              "✉️ Private and group English lessons in Yerevan: englishreadingroom.am@gmail.com",
              "", f"#Shorts #LearnEnglish #EnglishStory #{level}English #Անգլերեն"]
    desc = "\n".join(parts).replace("<", "‹").replace(">", "›")[:4900]
    words = [w for w in name.replace("'", " ").replace("?", "").split() if len(w) > 3]
    tags, total = [], 0
    for t in [name, f"{level} English", f"{level} English story", f"{who or 'short'} English story"] + BASE_TAGS + words:
        if t not in tags and total + len(t) + 3 < 480: tags.append(t); total += len(t) + 3
    snippet = {"title": title, "description": desc, "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en-GB", "tags": tags}
    loc = {}
    if s.get("title_hy"):
        loc["hy"] = {"title": f"{s['title_hy']} 📖 Անգլերեն պատմություն ({level}) | {name}"[:100], "description": desc}
    return {"snippet": snippet, "localizations": loc,
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True, "embeddable": True,
                       "license": "youtube", "publicStatsViewable": True}}


def youtube(item: dict) -> str | None:
    cid, secret, refresh = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and secret and refresh): return None
    token = _post("https://oauth2.googleapis.com/token", {"client_id": cid, "client_secret": secret, "refresh_token": refresh, "grant_type": "refresh_token"})["access_token"]
    with urllib.request.urlopen(item["media"]["video_url"], timeout=300) as r:
        video = r.read()
    meta = youtube_meta(item)
    parts = "snippet,status" + (",localizations" if meta["localizations"] else "")
    if not meta["localizations"]: meta.pop("localizations")
    boundary = "erroomboundary"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n").encode() + video + f"\r\n--{boundary}--\r\n".encode()
    out = _post(f"https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part={parts}", body=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/related; boundary={boundary}"})
    return out.get("id")


def facebook(video_url: str, caption: str) -> str | None:
    page, token = os.environ.get("FB_PAGE_ID", "").strip(), os.environ.get("FB_PAGE_TOKEN", "").strip()
    if not (page and token): return None
    return _post(f"{GRAPH}/{page}/videos", {"file_url": video_url, "description": caption, "access_token": token}).get("id")


def run(item: dict) -> dict:
    """Returns the IDs it got, e.g. {"youtube_id": "...", "facebook_id": "..."}; prints and skips on errors."""
    out = {}
    if item.get("format") != "REELS" or not item.get("media", {}).get("video_url"): return out
    for name, fn in (("youtube_id", lambda i: youtube(i) if i.get("kind") == "reading" else None),
                     ("facebook_id", lambda i: facebook(i["media"]["video_url"], i.get("caption", "")))):
        if item.get(name): continue
        try:
            got = fn(item)
            if got: out[name] = got; print(f"Cross-posted {item['id']} → {name} {got}")
        except Exception as error:  # never block Instagram publishing
            print(f"Cross-post {name} failed for {item['id']}: {error}")
    return out
