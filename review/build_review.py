"""Build a one-page review gallery for the queue (open review/index.html in a browser).

Mom/owner marks each post ✅ or ✏️ and presses Export → review.json.
Then: python review/apply_review.py review.json  (sets review_status to approved/fix).
"""
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent.parent / "outputs" / "english-reels-samples"
q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))

def media(item):
    k, cid = item["kind"], item["content_id"]
    if k == "rule":
        files = sorted((OUT / f"carousel-{cid}").glob("*.png"))
        return "".join(f'<img loading="lazy" src="{f.as_uri()}">' for f in files) or "<p class=miss>Not rendered yet</p>"
    name = f"story-{cid}.mp4" if k == "story" else f"{k}-{cid}.mp4"
    f = OUT / name
    return f'<video controls preload="none" src="{f.as_uri()}"></video>' if f.exists() else "<p class=miss>Not rendered yet</p>"

cards = []
for it in q["items"]:
    cards.append(f'''<article data-id="{it["id"]}" class="{it.get("review_status","draft")}">
<header><b>{it["date"]} · {it["time"]}</b><span>{it["kind"].upper()}</span></header>
<div class="m">{media(it)}</div>
<pre>{html.escape(it["caption"])}</pre>
<div class="b"><button data-v="approved">✅ Հաստատել</button><button data-v="fix">✏️ Ուղղել</button></div>
<textarea placeholder="Ինչ ուղղել…"></textarea></article>''')

page = f'''<!doctype html><html lang="hy"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review · English Reading Room</title><style>
:root{{--v:#6A49E2;--n:#17183A;--l:#A891F7;--g:#E9C46A}}
body{{margin:0;background:#0E0B1D;color:#fff;font:15px/1.5 system-ui,sans-serif}}
h1{{font:700 24px Georgia,serif;margin:20px 16px 4px}} .top{{position:sticky;top:0;background:#0E0B1Dee;padding:10px 16px;display:flex;gap:12px;align-items:center;z-index:2}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:16px}}
article{{background:#17183A;border:1px solid #2A1E4D;border-radius:18px;padding:14px}} article.approved{{border-color:#2E9E6A}} article.fix{{border-color:#E8A317}}
header{{display:flex;justify-content:space-between;color:var(--l)}} .m{{display:flex;gap:6px;overflow-x:auto;margin:10px 0}}
.m video{{width:100%;border-radius:12px}} .m img{{height:320px;border-radius:10px}} .miss{{color:#8B7CC7}}
pre{{white-space:pre-wrap;font:14px/1.5 system-ui;background:#0E0B1D;padding:10px;border-radius:10px}}
.b{{display:flex;gap:8px}} button{{flex:1;padding:10px;border-radius:12px;border:0;font-weight:700;cursor:pointer;background:#2A1E4D;color:#fff}}
article.approved button[data-v=approved]{{background:#2E9E6A}} article.fix button[data-v=fix]{{background:#E8A317;color:#17183A}}
textarea{{width:100%;box-sizing:border-box;margin-top:8px;border-radius:10px;background:#0E0B1D;color:#fff;border:1px solid #2A1E4D;padding:8px;display:none}} article.fix textarea{{display:block}}
#exp{{background:var(--g);color:var(--n);flex:none;padding:10px 18px}} #cnt{{color:var(--l)}}
</style></head><body><h1>English Reading Room · Review</h1>
<div class="top"><span id="cnt"></span><button id="exp">Export review.json</button></div>
<div class="grid">{"".join(cards)}</div>
<script>
const st=JSON.parse(localStorage.getItem('err-review')||'{{}}');
const all=[...document.querySelectorAll('article')];
function paint(){{all.forEach(a=>{{const s=st[a.dataset.id];a.className=s?s.v:'';a.querySelector('textarea').value=s&&s.note||''}});
document.getElementById('cnt').textContent=Object.values(st).filter(s=>s.v==='approved').length+' / '+all.length+' հաստատված';
try{{localStorage.setItem('err-review',JSON.stringify(st))}}catch(e){{}}}}
all.forEach(a=>{{a.querySelectorAll('button').forEach(b=>b.onclick=()=>{{st[a.dataset.id]={{v:b.dataset.v,note:a.querySelector('textarea').value}};paint()}});
a.querySelector('textarea').oninput=e=>{{(st[a.dataset.id]||={{v:'fix'}}).note=e.target.value;try{{localStorage.setItem('err-review',JSON.stringify(st))}}catch(_){{}}}}}});
document.getElementById('exp').onclick=()=>{{const b=new Blob([JSON.stringify(st,null,2)],{{type:'application/json'}});const l=document.createElement('a');l.href=URL.createObjectURL(b);l.download='review.json';l.click()}};
paint();
</script></body></html>'''
(ROOT / "review" / "index.html").write_text(page, encoding="utf-8")
print("review/index.html written")
