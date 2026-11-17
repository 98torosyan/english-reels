"""Control panel: one page that shows the whole page's state at a glance (queue + analytics), in Armenian.
Usage: python tools/build_panel.py OUT.html"""
import base64, io, json, subprocess, sys, html
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("Asia/Yerevan")
NAMES = {"feelstory": "Զգացմունքային պատմություն", "opposites": "Մեկ օր՝ հակադիր բառերով", "storyvideo": "Պատմություն / Դասական", "classic": "Դասական կարուսել",
         "picstory": "Պատմություն նկարներով", "words10": "10 բառ", "reading": "Ընթերցանություն", "dialogue": "Երկխոսություն", "phrasal": "Phrasal verbs",
         "mistake": "Սխալներ", "quiz": "Թեստ", "word": "Օրվա բառ", "rule": "Կանոն (կարուսել)", "review": "Շաբաթվա կրկնություն", "story": "Պատմություն մասերով",
         "story-image": "Story", "routine": "Everyday English", "list": "Ցանկ (կարուսել)", "test": "Թեստ (կարուսել)", "sound": "Հնչյուններ"}
WD = ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"]
FMT = {"REELS": "Reel", "CAROUSEL": "Կարուսել", "STORIES": "Story", "IMAGE": "Նկար"}
e = lambda s: html.escape(str(s))


MEDIA = ROOT.parent / "english-reels-media"
BASE = "https://98torosyan.github.io/english-reels-media/"


def thumb(i):
    """A small 3:4 picture of how the post will look on the profile grid (data URI), or None."""
    m = i.get("media") or {}
    src = m.get("cover_url") or (m.get("slides") or [None])[0] or m.get("image_url") or m.get("video_url")
    if not src or not src.startswith(BASE): return None
    f = MEDIA / src[len(BASE):]
    if not f.exists(): return None
    if f.suffix == ".mp4":
        t = (i.get("thumb_offset") or 1500) / 1000
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(f), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True)
        data = r.stdout
    else:
        data = f.read_bytes()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB"); w, h = im.size; th = int(w * 4 / 3)
        if h > th: im = im.crop((0, (h - th) // 2, w, (h - th) // 2 + th))
        im = im.resize((240, 320)); b = io.BytesIO(); im.save(b, "JPEG", quality=78)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return None


def main(out):
    q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
    now = datetime.now(TZ); today = now.date()
    snaps = sorted((ROOT / "analytics/snapshots").glob("*.json"))
    snap = json.loads(snaps[-1].read_text()) if snaps else {}
    week_snap = next((json.loads(p.read_text()) for p in snaps if p.stem == (today - timedelta(days=7)).isoformat()), None)
    followers = snap.get("followers"); gained = followers - week_snap["followers"] if week_snap and followers is not None else None
    feed = [i for i in q if i.get("format") != "STORIES"]
    pub7 = [i for i in feed if i.get("published_at") and date.fromisoformat(i["published_at"][:10]) > today - timedelta(days=7)]
    upcoming = [i for i in q if i.get("review_status") == "staged" and not i.get("published_at") and date.fromisoformat(i["date"]) >= today]
    failed = [i for i in q if i.get("review_status") == "failed"]
    late = [i for i in q if i.get("review_status") == "staged" and not i.get("published_at")
            and datetime.fromisoformat(f"{i['date']}T{i['time']}").replace(tzinfo=TZ) < now - timedelta(minutes=40)
            and datetime.fromisoformat(f"{i['date']}T{i['time']}").replace(tzinfo=TZ) > now - timedelta(days=2)]
    held = Counter(NAMES.get(i.get("kind"), i.get("kind")) for i in q if i.get("review_status") == "draft")
    last_day = max((i["date"] for i in upcoming if i.get("format") != "STORIES"), default="—")
    by_kind = Counter(NAMES.get(i.get("kind"), i.get("kind")) for i in upcoming if i.get("format") != "STORIES")

    nxt = sorted([i for i in upcoming if i.get("format") != "STORIES"], key=lambda i: (i["date"], i["time"]))[:12]
    grid = [(i, u) for i in reversed(nxt) if (u := thumb(i))]
    days = defaultdict(list)
    for i in sorted(q, key=lambda i: (i["date"], i["time"])):
        d = date.fromisoformat(i["date"])
        if today <= d < today + timedelta(days=7) and i.get("review_status") in ("staged", "published", "failed"): days[d].append(i)

    def row(i):
        st = "done" if i.get("published_at") else ("bad" if i.get("review_status") == "failed" else "wait")
        lab = {"done": "Հրապարակված", "bad": "Սխալ", "wait": "Սպասում է"}[st]
        return (f'<li class="it {st}"><span class="t">{e(i["time"])}</span><span class="k">{e(NAMES.get(i.get("kind"), i.get("kind")))}'
                f'<small>{e(FMT.get(i.get("format"), i.get("format")))} · {e((i.get("title") or "")[:48])}</small></span><span class="st">{lab}</span></li>')

    alerts = "".join(f'<li class="al bad">Սխալ՝ {e(i["date"])} {e(i["time"])} · {e(NAMES.get(i.get("kind"), i.get("kind")))} · {e((i.get("last_error") or "")[:90])}</li>' for i in failed)
    alerts += "".join(f'<li class="al warn">Ուշանում է՝ {e(i["date"])} {e(i["time"])} · {e(NAMES.get(i.get("kind"), i.get("kind")))}</li>' for i in late)
    if not alerts: alerts = '<li class="al ok">Ամեն ինչ կարգին է. ուշացած կամ սխալ գրառում չկա։</li>'

    stat = lambda big, small: f'<div class="stat"><b>{big}</b><span>{small}</span></div>'
    page = f"""<title>Reading Room Control</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,500;7..72,700&family=Noto+Sans+Armenian:wght@400;600;700&display=swap">
<style>
/* layout: summary strip, alerts, then a 7-day schedule grid and the series inventory */
:root{{--bg:#F6F0E7;--card:#FFFBF5;--ink:#2B1E14;--muted:#7A6656;--line:#E7DACB;--accent:#B5651D;--ok:#3E7D4F;--warn:#B7791F;--bad:#B23A3A;
--display:Literata,Georgia,serif;--body:"Noto Sans Armenian",system-ui,sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1C1612;--card:#251D17;--ink:#F3E8DC;--muted:#B7A595;--line:#3A2E25;--accent:#E0995A;--ok:#7CC48E;--warn:#E6B45A;--bad:#E57D7D;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#1C1612;--card:#251D17;--ink:#F3E8DC;--muted:#B7A595;--line:#3A2E25;--accent:#E0995A;--ok:#7CC48E;--warn:#E6B45A;--bad:#E57D7D;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font-family:var(--body);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 48px}}
.wrap{{max-width:1180px;margin:0 auto;display:grid;gap:22px}}
h1{{font:700 34px/1.1 var(--display);letter-spacing:-.5px;text-wrap:balance}} h1 em{{color:var(--accent)}}
.sub{{color:var(--muted);margin-top:6px;font-size:14px}}
h2{{font:600 13px var(--body);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:grid;gap:4px}}
.stat b{{font:700 30px var(--display);font-variant-numeric:tabular-nums}} .stat span{{color:var(--muted);font-size:13px}}
ul{{list-style:none;margin:0;padding:0}}
.al{{padding:12px 16px;border-radius:12px;background:var(--card);border:1px solid var(--line);border-left:5px solid var(--ok);margin-bottom:8px;font-size:14px}}
.al.bad{{border-left-color:var(--bad)}} .al.warn{{border-left-color:var(--warn)}}
.days{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.day{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 14px 8px;min-width:0}}
.day h3{{font:700 17px var(--display);margin-bottom:8px}} .day h3 span{{color:var(--muted);font:500 13px var(--body);margin-left:6px}}
.it{{display:grid;grid-template-columns:46px 1fr auto;gap:10px;align-items:start;padding:8px 0;border-top:1px solid var(--line);font-size:14px}}
.it .t{{font-variant-numeric:tabular-nums;font-weight:600}} .it small{{display:block;color:var(--muted);font-size:12px;margin-top:2px;overflow-wrap:anywhere}}
.it .st{{font-size:11px;font-weight:700;padding:3px 8px;border-radius:99px;white-space:nowrap;color:var(--warn);border:1px solid currentColor}}
.it.done .st{{color:var(--ok)}} .it.bad .st{{color:var(--bad)}} .it.done{{opacity:.72}}
.inv{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;min-width:0}}
.bar{{display:grid;grid-template-columns:1fr auto;gap:8px;padding:7px 0;border-top:1px solid var(--line);font-size:14px}} .bar b{{font-variant-numeric:tabular-nums}}
.foot{{color:var(--muted);font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3px;max-width:520px}}
.grid figure{{margin:0;position:relative}} .grid img{{display:block;width:100%;aspect-ratio:3/4;object-fit:cover}}
.grid figcaption{{position:absolute;left:6px;bottom:6px;font-size:11px;font-weight:600;color:#fff;background:#0008;padding:2px 6px;border-radius:6px;font-variant-numeric:tabular-nums}}
</style>
<div class="wrap">
<header><h1>English Reading Room · <em>կառավարման վահանակ</em></h1>
<div class="sub">Թարմացված՝ {now:%Y-%m-%d %H:%M} (Երևան) · @english.readingroom</div></header>
<section class="stats">
{stat(followers if followers is not None else "—", "հետևորդ" + (f" ({'+' if gained >= 0 else ''}{gained} շաբաթում)" if gained is not None else ""))}
{stat(len(pub7), "գրառում վերջին 7 օրում")}
{stat(len([i for i in upcoming if i.get("format") != "STORIES"]), "պատրաստ գրառում հերթում")}
{stat(e(last_day), "պլանավորված է մինչև")}
{stat(sum(held.values()), "պահված (սպասում են քո «այո»-ին)")}
</section>
<section><h2>Վիճակ</h2><ul>{alerts}</ul></section>
<section><h2>Առաջիկա 7 օրը</h2><div class="days">
{"".join(f'<div class="day"><h3>{d:%d.%m}<span>{WD[d.weekday()]}</span></h3><ul>{"".join(row(i) for i in days[d])}</ul></div>' for d in sorted(days))}
</div></section>
<section><h2>Էջի տեսքը՝ հաջորդ 12 գրառումը (վերևում՝ ամենավերջինը)</h2><div class="grid">
{"".join(f'<figure><img src="{u}" alt=""><figcaption>{e(i["date"][5:])} {e(i["time"])}</figcaption></figure>' for i, u in grid)}
</div></section>
<section class="inv">
<div class="box"><h2>Հերթում՝ ըստ շարքի</h2>{"".join(f'<div class="bar"><span>{e(k)}</span><b>{v}</b></div>' for k, v in by_kind.most_common())}</div>
<div class="box"><h2>Պահված՝ չհրապարակել առանց քո ասելու</h2>{"".join(f'<div class="bar"><span>{e(k)}</span><b>{v}</b></div>' for k, v in held.most_common()) or '<div class="bar"><span>Ոչինչ</span><b>0</b></div>'}</div>
</section>
<p class="foot">Դիտումները, պահումներն ու share-երը կավելանան այստեղ, երբ Instagram token-ը ստանա «instagram_manage_insights» թույլտվությունը։</p>
</div>"""
    Path(out).write_text(page, encoding="utf-8"); print("panel →", out)


if __name__ == "__main__":
    main(sys.argv[1])
