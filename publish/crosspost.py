"""Cross-post a published reel to YouTube Shorts and the Facebook Page (official APIs only).

Each target is used only when its secrets are set, and a failure never blocks Instagram:
  YouTube:  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (YouTube Data API v3, OAuth)
  Facebook: FB_PAGE_ID, FB_PAGE_TOKEN                         (Graph API, page video by URL)"""
import json, os, urllib.parse, urllib.request

GRAPH = f"https://graph.facebook.com/{os.environ.get('META_GRAPH_API_VERSION', 'v27.0')}"


def _post(url, data=None, headers=None, body=None):
    req = urllib.request.Request(url, data=body if body is not None else urllib.parse.urlencode(data or {}).encode(), headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def youtube(video_url: str, caption: str) -> str | None:
    cid, secret, refresh = (os.environ.get(k, "").strip() for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and secret and refresh): return None
    token = _post("https://oauth2.googleapis.com/token", {"client_id": cid, "client_secret": secret, "refresh_token": refresh, "grant_type": "refresh_token"})["access_token"]
    with urllib.request.urlopen(video_url, timeout=300) as r:
        video = r.read()
    name, level = "", "A1"
    for line in caption.split("\n")[:4]:
        if "·" in line and "Daily reading" not in line and "Կարդանք" not in line:
            name = line.split("·")[0].strip()
            if "(" in line: level = line.rsplit("(", 1)[1].split(")")[0].strip() or level
            break
    name = name or "Daily reading"
    title = f"{name} 📖 Easy English Story ({level}) | Անգլերեն ընթերցանություն"[:100]
    desc = "\n".join(l for l in caption.split("\n") if not l.startswith("#") and "Direct" not in l and "bio" not in l).strip()
    desc += ("\n\nԱնհատական և խմբային դասեր Երևանում՝ englishreadingroom.am@gmail.com"
             "\nԱմբողջական դասերը ձայնով՝ https://98torosyan.github.io/english-reading/"
             "\nInstagram՝ https://www.instagram.com/english.readingroom/\n\n#Shorts #LearnEnglish #EnglishReading #Անգլերեն")
    meta = {"snippet": {"title": title, "description": desc[:4900], "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en-GB",
                        "tags": ["English", "learn English", "easy English story", "English reading", "A1 English", "Անգլերեն", "English Reading Room"]},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    boundary = "erroomboundary"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n").encode() + video + f"\r\n--{boundary}--\r\n".encode()
    out = _post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status", body=body,
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
    for name, fn in (("youtube_id", youtube), ("facebook_id", facebook)):
        if item.get(name): continue
        try:
            got = fn(item["media"]["video_url"], item.get("caption", ""))
            if got: out[name] = got; print(f"Cross-posted {item['id']} → {name} {got}")
        except Exception as error:  # never block Instagram publishing
            print(f"Cross-post {name} failed for {item['id']}: {error}")
    return out
