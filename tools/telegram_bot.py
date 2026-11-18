"""The page's Telegram helper. The owner sends a story pack (the JSON text) and then six clips; when all six are in,
the pack goes into the repo and the "Make a story reel" workflow is started. Runs every few minutes from GitHub Actions
(no server). Only the owner's chat is served.

  python tools/telegram_bot.py poll            read new messages, store packs and clips, print ids that are complete
  python tools/telegram_bot.py send <text>     message to the owner
  python tools/telegram_bot.py video <file> <caption>   send a finished reel to the owner
Secrets (environment): TG_BOT_TOKEN, TG_CHAT_ID (the owner's chat id; when empty the bot answers /start with it)."""
import json, os, subprocess, sys, urllib.parse, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox"
STATE = INBOX / "state.json"
TOKEN = os.environ.get("TG_BOT_TOKEN", "")
OWNER = os.environ.get("TG_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"

HELP = ("Բարև 👋 Ես English Reading Room-ի օգնականն եմ։\n\n"
        "Ինչպես պատրաստել պատմության ռիլս.\n"
        "1. Ուղարկիր պատմության տեքստը ({ … } մասը)։\n"
        "2. Ուղարկիր 6 տեսարանով նկարը. ես կկտրեմ ու հետ կուղարկեմ 6 առանձին նկար՝ կենդանացնելու համար։\n"
        "3. Ուղարկիր 6 վիդեոն հերթով՝ 1-ից 6 (ավելի լավ է որպես ֆայլ, որ որակը չընկնի)։\n"
        "4. Մոտ 30 րոպեից պատրաստ ռիլսը կգա այստեղ։\n\n"
        "Հրամաններ. /status՝ ինչ է սպասվում, /cancel՝ չեղարկել ընթացիկը, /list՝ պատրաստ պատմությունները, "
        "/publish՝ պատրաստները դնել հերթի մեջ։")


def call(method, **params):
    data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}).encode()
    with urllib.request.urlopen(urllib.request.Request(f"{API}/{method}", data=data), timeout=60) as r:
        out = json.loads(r.read())
    if not out.get("ok"): raise RuntimeError(f"{method}: {out}")
    return out["result"]


def send(text, chat=None):
    call("sendMessage", chat_id=chat or OWNER, text=text, disable_web_page_preview=True)


def send_video(path, caption):
    """Multipart upload (Telegram bots may send files up to 50 MB)."""
    b = uuid.uuid4().hex; body = bytearray()
    for k, v in (("chat_id", OWNER), ("caption", caption), ("supports_streaming", "true")):
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += f"--{b}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{Path(path).name}\"\r\nContent-Type: video/mp4\r\n\r\n".encode()
    body += Path(path).read_bytes() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"{API}/sendVideo", data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=300) as r: json.loads(r.read())


def send_photos(paths, caption):
    """Up to ten pictures as one album, sent as files so they keep full quality."""
    b = uuid.uuid4().hex; body = bytearray()
    media = [{"type": "document", "media": f"attach://f{i}", **({"caption": caption} if i == len(paths) - 1 else {})} for i in range(len(paths))]
    for k, v in (("chat_id", OWNER), ("media", json.dumps(media))):
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for i, pth in enumerate(paths):
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"f{i}\"; filename=\"{Path(pth).name}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode()
        body += Path(pth).read_bytes() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(f"{API}/sendMediaGroup", data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=300) as r: json.loads(r.read())


def cut_sheet(src, title):
    """A 6-scene sheet -> six separate scenes (2x larger, sharpened), sent back in order for animating."""
    import tempfile
    from PIL import Image, ImageFilter
    sys.path.insert(0, str(ROOT / "tools"))
    from upscale_panels import panels
    work = Path(tempfile.mkdtemp())
    ps = list(panels(Path(src)))
    out = []
    for k, p in enumerate(ps, 1):
        big = p.resize((p.width * 2, p.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        f = work / f"{k}.jpg"; big.convert("RGB").save(f, quality=95); out.append(f)
    send_photos(out, f"«{title}»՝ {len(out)} տեսարան ✅ Ամեն մեկը կենդանացրու ու վիդեոները ուղարկիր այստեղ հերթով։")


def download(file_id, dest):
    f = call("getFile", file_id=file_id)
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{f['file_path']}", timeout=120) as r:
        dest.write_bytes(r.read())


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {"offset": 0, "pending": None}


def save(st):
    INBOX.mkdir(exist_ok=True); STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")


def handle(msg, st, done):
    sys.path.insert(0, str(ROOT / "tools"))
    import story_pack
    chat = str(msg["chat"]["id"]); text = msg.get("text") or msg.get("caption") or ""
    if not OWNER:
        send(f"Այս զրույցի chat id-ն է՝ {chat}\nԱյն պահիր GitHub-ում TG_CHAT_ID անունով գաղտնի բանալի։", chat); return
    if chat != OWNER:
        send("Այս բոտը մասնավոր է։", chat); return
    p = st.get("pending")
    if text.startswith("/start") or text.startswith("/help"): send(HELP); return
    if text.startswith("/status"):
        send(f"Սպասում եմ «{p['title']}»-ի վիդեոներին՝ {p['clips']}/6։" if p else "Ոչինչ չի սպասվում։ Ուղարկիր նոր պատմության տեքստը։"); return
    if text.startswith("/cancel"):
        if p: subprocess.run(["rm", "-rf", str(INBOX / p["id"])])
        st["pending"] = None; send("Չեղարկեցի։ Կարող ես նոր պատմություն ուղարկել։"); return
    if text.startswith("/publish"):
        r = subprocess.run([sys.executable, str(ROOT / "publish" / "plan_stories.py")], capture_output=True, text=True)
        planned = [l for l in r.stdout.splitlines() if l.strip()]
        send("Հերթում են ✅\n" + "\n".join(f"• {l}" for l in planned) if planned else "Հրապարակելու պատրաստ պատմություն չկա։"); return
    if text.startswith("/list"):
        reg = ROOT / "reels" / "data" / "stories_ready.json"
        items = json.loads(reg.read_text()) if reg.exists() else []
        mark = {"held": "⏸ սպասում է", "queued": "📅 հերթում"}
        send("Պատրաստ պատմություններ.\n" + "\n".join(f"• {x['title']}՝ {mark.get(x.get('status'), x.get('status'))}" for x in items) +
             "\n\n/publish՝ սպասողներին դնել հերթի մեջ (ամեն երեկո 21:00)" if items else "Դեռ պատրաստ պատմություն չկա։"); return
    doc = msg.get("document") or {}
    pic = (msg.get("photo") or [None])[-1] or (doc if doc.get("mime_type", "").startswith("image") else None)
    if pic:
        if not p: send("Նախ ուղարկիր պատմության տեքստը, հետո 6 տեսարանով նկարը։"); return
        sheet = INBOX / p["id"] / "sheet.png"; download(pic["file_id"], sheet)
        try:
            cut_sheet(sheet, p["title"])
        except Exception as error:
            send(f"Նկարը չկարողացա 6 մասի կտրել ({error})։ Համոզվիր, որ 6 տեսարանները բաժանված են սպիտակ գծերով։")
        return
    vid = msg.get("video") or (msg.get("document") if (msg.get("document") or {}).get("mime_type", "").startswith("video") else None)
    if vid:
        if not p: send("Նախ ուղարկիր պատմության տեքստը, հետո վիդեոները։"); return
        if vid.get("file_size", 0) > 20_000_000: send("Այս վիդեոն 20 ՄԲ-ից մեծ է, Telegram-ը թույլ չի տալիս ինձ բեռնել։ Ուղարկիր ավելի փոքր։"); return
        p["clips"] += 1; download(vid["file_id"], INBOX / p["id"] / f"clip{p['clips']}.mp4")
        if p["clips"] < 6: send(f"Վիդեո {p['clips']}/6 ✅"); return
        story_pack.add(INBOX / p["id"]); done.append(p["id"]); st["pending"] = None
        send(f"6/6 ✅ Բոլորը ստացա։ «{p['title']}»-ը պատրաստում եմ՝ մոտ 30 րոպե։ Պատրաստ լինելուն պես կուղարկեմ այստեղ։"); return
    if "{" in text:
        try:
            pack = story_pack.parse(text)
        except Exception:
            send("Չկարողացա կարդալ տեքստը։ Ուղարկիր պատմության { … } մասը ամբողջությամբ։"); return
        bad = story_pack.problems(pack)
        if bad: send("Տեքստում ուղղելու բաներ կան.\n• " + "\n• ".join(bad)); return
        sid = story_pack.slug(pack.get("id") or pack["title"])
        if p: subprocess.run(["rm", "-rf", str(INBOX / p["id"])])
        (INBOX / sid).mkdir(parents=True, exist_ok=True)
        (INBOX / sid / "story.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        st["pending"] = {"id": sid, "title": pack["title"], "clips": 0}
        send(f"Պատմությունը ստացա՝ «{pack['title']}» ✅\nՀիմա ուղարկիր 6 վիդեոն հերթով (0/6)։"); return
    send("Չհասկացա 🙂 Ուղարկիր պատմության տեքստը կամ վիդեոները։ /help՝ օգնություն։")


def poll():
    st = load(); done = []
    for up in call("getUpdates", offset=st["offset"], timeout=0, allowed_updates=["message"]):
        st["offset"] = up["update_id"] + 1
        if "message" in up:
            try:
                handle(up["message"], st, done)
            except Exception as error:   # one bad message must not block the rest
                print("message failed:", error)
                try: send("Ինչ-որ բան չստացվեց այս հաղորդագրության հետ։ Փորձիր նորից։")
                except Exception: pass
        save(st)
    print(" ".join(done))


def main():
    if not TOKEN: raise SystemExit("TG_BOT_TOKEN is not set")
    cmd = sys.argv[1]
    if cmd == "poll": poll()
    elif cmd == "send": send(sys.argv[2])
    elif cmd == "video": send_video(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
